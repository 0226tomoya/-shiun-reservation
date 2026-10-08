"""ユーザーの修正（plan.overrides）を、出来上がった編集データに当てる最後の工程。insert_size_compare.py の後に使う。

    python3 apply_overrides.py IN.fcpxml PLAN.json OUT.fcpxml

plan.overrides（時刻はすべてこの工程に入る編集データの時刻。秒）:
  clear:   [{t0, t1, keep_at: [秒...]}]  区間に頭がある差し込み（lane 3 以上の映像・写真と、lane 4 以上の調整レイヤー）を外す。
           keep_at の時刻に頭がある調整レイヤーは残す（ティーザーなど）
  remove:  [{name, at}]                  名前が name で、頭が at（±0.05 秒）の接続クリップを外す（name は前方一致）
  retime:  [{name, at, t0?, t1?}]        名前・頭で選んだ要素の頭・終わりを変える（文字や書式はそのまま）
  move:    [{at, lanes, t0, t1, swap?}]  at に頭がある lanes の要素（紹介インの写真 2 枚と中央の商品名など）を t0〜t1 に移す
                                        swap: {lane: 素材のパス} でその lane の写真の中身を差し替える（パスは plan.asset_root から）
  videos:  [{t0, t1, src, in, speed?, lane?, adj?}]
           EC・LOOK 動画のインサート。手ブレ補正（A19 と同じ clip>video>adjust-stabilization）、speed<1 は timeMap のスロー。
           adj=true で上に A19 の EC 用調整レイヤー（拡大 1.15）を重ねる
  stills:  [{t0, t1, path, like?, lane?}] 写真のインサート。like（素材のパス）の既存の要素の拡大・位置・フィルタをそのまま使う
  pairs:   [{t0, t1, left, right}]       写真の左右 2 分割（修正 7: 左の画像を上のレイヤーにして、画面の中央でクロップ）
  screens: [{t0, t1, path, w, h, label: [行1, 行2]}]
           公式サイトのスクリーンショット（A19 21:25 の型: 左に置く）と左下の商品名ラベル（product_label_bottom）
  no_stroke: true                       すべてのテロップの縁取り（strokeColor・strokeWidth）と影を外す（修正 30）
  stabilize_all: true                   残っている EC・LOOK 動画（asset-clip）も手ブレ補正つきの clip に包む
  merge_adjust: true                    本編の調整レイヤー（lane 1）を A19 の切り方にまとめる
                                        （中身が同じで続いているものは 1 本に。差し込み・字幕・ラベルの切り替わりでは切る）
"""
import copy
import json
import os
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_lineup import T, S  # noqa: E402
from build_lineup import Templates, apply_template  # noqa: E402
from fcpxml_util import append_anchor  # noqa: E402

FD = Fraction(1001, 60000)
VIDEO_TAGS = ('video', 'asset-clip', 'clip', 'ref-clip', 'mc-clip', 'sync-clip')
RATE = {'1001/60000s': '59.94', '1001/30000s': '29.97', '1000/24000s': '24', '1001/24000s': '23.98', '100/2500s': '25'}


def F(x):
    return Fraction(str(x))


def main():
    src, plan_path, out = sys.argv[1:4]
    plan = json.load(open(plan_path, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(plan_path))
    ov = plan['overrides']
    tree = ET.parse(src)
    root = tree.getroot()
    resources = root.find('resources')
    res = {e.get('id'): e for e in resources}
    project = [p for p in root.iter('project') if p.get('name') == '本編'][0]
    spine = project.find('sequence/spine')
    stats = {}

    def bump(k, n=1):
        stats[k] = stats.get(k, 0) + n

    # ---- 素材（パス → asset）----
    assets = {}
    for a in resources:
        m = a.find('media-rep')
        if a.tag == 'asset' and m is not None:
            p_ = unicodedata.normalize('NFC', urllib.parse.unquote(m.get('src')))
            if plan['asset_root'] in p_:
                assets[p_.split(plan['asset_root'], 1)[1]] = a
    by_name = {}
    for a in resources:
        if a.tag == 'asset':
            by_name.setdefault(a.get('name'), a)
    like = next(a for a in assets.values())
    src0 = unicodedata.normalize('NFC', urllib.parse.unquote(like.find('media-rep').get('src')))
    prefix = src0[:src0.index(plan['asset_root']) + len(plan['asset_root'])]

    def new_id(p):
        k = 1
        while f'{p}{k}' in res:
            k += 1
        return f'{p}{k}'

    def still_asset(path, w, h):
        path = unicodedata.normalize('NFC', path)
        if path in assets:
            return assets[path]
        fe = next((e for e in resources if e.tag == 'format' and e.get('name') == 'FFVideoFormatRateUndefined'
                   and e.get('width') == str(w) and e.get('height') == str(h)), None)
        if fe is None:
            fe = ET.Element('format', id=new_id('ro_f'), name='FFVideoFormatRateUndefined', width=str(w), height=str(h), colorSpace='1-13-1')
            resources.insert(0, fe)
            res[fe.get('id')] = fe
        a = ET.SubElement(resources, 'asset', id=new_id('ro_'), name=path.rsplit('/', 1)[1].rsplit('.', 1)[0],
                          start='0s', duration='0s', hasVideo='1', format=fe.get('id'), videoSources='1')
        ET.SubElement(a, 'media-rep', kind='original-media',
                      src=urllib.parse.quote(unicodedata.normalize('NFD', prefix + path), safe='/:'))
        res[a.get('id')] = a
        assets[path] = a
        bump('登録した素材')
        return a

    def asset_of(key):
        a = assets.get(unicodedata.normalize('NFC', key))
        return a if a is not None else by_name[key]

    # ---- 時刻 ----
    def spans():
        return [(T(e.get('offset')), T(e.get('duration')), T(e.get('start')), e) for e in spine]

    SP = spans()
    CUTS = sorted({o for o, _, _, _ in SP} | {o + d for o, d, _, _ in SP})

    def snap(t, win=Fraction(3, 10)):
        t = F(t)
        c = min(CUTS, key=lambda c: abs(c - t))
        if abs(c - t) <= win:
            return c
        return round(t / FD) * FD

    def parent_at(t):
        for o, d, st, e in SP:
            if o <= t < o + d:
                return o, st, e
        o, d, st, e = SP[-1]
        return o, st, e

    def children():
        """(親, 子, 絶対の頭) を全部"""
        out = []
        for o, d, st, e in SP:
            for c in list(e):
                if c.get('offset') is None or c.tag in ('chapter-marker', 'marker', 'keyword'):
                    continue
                out.append((e, c, o + T(c.get('offset')) - st))
        return out

    def attach(el, t):
        o, st, e = parent_at(t)
        el.set('offset', S(st + (t - o)))
        append_anchor(e, el)
        return el

    def detach(par, c):
        par.remove(c)

    def is_adj(c):
        return c.tag == 'title' and (c.get('name') or '').startswith('Adjustment Layer')

    def lane(c):
        return int(c.get('lane') or 0)

    def find(name, at):
        at = F(at)
        hit = [(p, c, a) for p, c, a in children() if (c.get('name') or '').startswith(name) and abs(a - at) <= Fraction(1, 20)]
        if not hit:
            raise SystemExit(f'見つからない: {name} @ {at}')
        return hit

    # ---- 型（調整レイヤー・EC のフィルタ）----
    tpl = Templates(os.path.join(base, plan['templates']))
    doc_res = res

    proto_adj = None   # A19 の EC 用調整レイヤー（拡大 1.15・カラー調整）
    proto_filters = []  # A19 の LOOK・EC 動画のフィルタ（基本3D・カラー調整）
    for p, c, a in children():
        if proto_adj is None and is_adj(c) and lane(c) == 4 and c.find('adjust-transform') is not None \
                and c.find('adjust-transform').get('scale') == '1.15 1.15':
            proto_adj = copy.deepcopy(c)
        if not proto_filters and c.tag == 'asset-clip' and c.findall('filter-video') and lane(c) >= 3:
            proto_filters = [copy.deepcopy(f) for f in c.findall('filter-video')]

    # ---- 1) 区間の差し込みを外す ----
    for cl in ov.get('clear', []):
        t0, t1 = F(cl['t0']), F(cl['t1'])
        keep = [F(x) for x in cl.get('keep_at', [])]
        for p, c, a in children():
            if not (t0 <= a < t1):
                continue
            if c.tag in VIDEO_TAGS and lane(c) >= 3 or is_adj(c) and lane(c) >= 4 and not any(abs(a - k) < Fraction(1, 20) for k in keep):
                detach(p, c)
                bump('外した差し込み')

    # ---- 2) 移動・時刻変更・写真の差し替え（外す前に、要素を取っておく）----
    saved = {}
    for i, mv in enumerate(ov.get('move', [])):
        at = F(mv['at'])
        saved[i] = [(p, c, a) for p, c, a in children() if abs(a - at) < Fraction(1, 20) and str(lane(c)) in map(str, mv['lanes'])]
    like_el = {}
    for st_ in ov.get('stills', []):
        k = st_.get('like')
        if k and k not in like_el:
            a_ = asset_of(k)
            like_el[k] = next((copy.deepcopy(c) for p, c, a in children() if c.get('ref') == a_.get('id') and c.tag == 'video'), None)
    for rm in ov.get('remove', []):
        for p, c, a in find(rm['name'], rm['at']):
            detach(p, c)
            bump('外した要素')
    for i, mv in enumerate(ov.get('move', [])):
        t0, t1 = snap(mv['t0']), snap(mv['t1'])
        for p, c, a in saved[i]:
            detach(p, c)
            c.set('duration', S(t1 - t0))
            sw = mv.get('swap', {}).get(str(lane(c)))
            if sw and c.tag == 'video':
                na = asset_of(sw)
                c.set('ref', na.get('id'))
                c.set('name', na.get('name'))
                bump('差し替えた写真')
            attach(c, t0)
            bump('移した要素')
    for rt in ov.get('retime', []):
        for p, c, a in find(rt['name'], rt['at']):
            t0 = snap(rt['t0']) if 't0' in rt else a
            t1 = snap(rt['t1']) if 't1' in rt else a + T(c.get('duration'))
            detach(p, c)
            c.set('duration', S(t1 - t0))
            attach(c, t0)
            bump('時刻を変えた要素')
    # ---- 3) EC・LOOK 動画（手ブレ補正つき。A19 の clip>video>adjust-stabilization）----
    def video_clip(a, t0, t1, src_in, speed, ln):
        fmt = res[a.get('format')]
        A = T(a.get('start'))
        L = T(a.get('duration'))
        fr = Fraction(1) / T(fmt.get('frameDuration'))
        d = t1 - t0
        sp = F(speed)
        s_in = A + F(src_in)
        if s_in + d * sp > A + L:
            raise SystemExit(f'{a.get("name")} の長さが足りない: {float(src_in)} + {float(d * sp)} > {float(L)}')
        cl = ET.Element('clip', lane=str(ln), offset='0s', name=a.get('name'), duration=S(d), format=a.get('format'), tcFormat='NDF')
        ET.SubElement(cl, 'conform-rate', scaleEnabled='0', srcFrameRate=RATE.get(fmt.get('frameDuration'), '29.97'))
        if sp != 1:
            # 時間の写し方（A19 と同じ）: time（クリップの中の時間）= A + (素材の時間 - A) / 速度
            tm = ET.SubElement(cl, 'timeMap')
            ET.SubElement(tm, 'timept', time=S(A), value=S(A), interp='smooth2')
            ET.SubElement(tm, 'timept', time=S(A + L / sp), value=S(A + L), interp='smooth2')
            st = A + round((s_in - A) / sp * fr) / fr
        else:
            st = A + round((s_in - A) * fr) / fr
        cl.set('start', S(st))
        ET.SubElement(cl, 'adjust-volume', amount='-96dB')
        v = ET.SubElement(cl, 'video', ref=a.get('id'), offset=S(A), duration=S(L))
        if A:
            v.set('start', S(A))
        ET.SubElement(v, 'adjust-stabilization', type='automatic')
        for f in proto_filters:
            cl.append(copy.deepcopy(f))
        return cl

    for vd in ov.get('videos', []):
        t0, t1 = snap(vd['t0']), snap(vd['t1'])
        a = asset_of(vd['src'])
        ln = vd.get('lane', 3)
        attach(video_clip(a, t0, t1, vd['in'], vd.get('speed', 1), ln), t0)
        if vd.get('adj', True) and proto_adj is not None:
            j = copy.deepcopy(proto_adj)
            j.set('lane', str(ln + 1))
            j.set('duration', S(t1 - t0))
            attach(j, t0)
        bump('動画のインサート')

    # ---- 4) 写真 ----
    for st_ in ov.get('stills', []):
        t0, t1 = snap(st_['t0']), snap(st_['t1'])
        a = asset_of(st_['path'])
        proto = like_el.get(st_.get('like') or '')
        el = copy.deepcopy(proto) if proto is not None else ET.Element('video', start='3600s')
        for k in ('offset', 'duration', 'lane'):
            el.attrib.pop(k, None)
        el.set('ref', a.get('id'))
        el.set('name', a.get('name'))
        el.set('lane', str(st_.get('lane', 3)))
        el.set('duration', S(t1 - t0))
        if proto is None:
            ET.SubElement(el, 'adjust-transform', position='0 0', scale=str(st_.get('scale', '1 1')))
        attach(el, t0)
        bump('写真のインサート')

    def pair(t0, t1, left, right, ln=3):
        """左の画像を上のレイヤー（ln+1）にして、画面の中央でクロップ（修正 7）"""
        for side, key, l_ in (('R', right, ln), ('L', left, ln + 1)):
            a = asset_of(key)
            fmt = res[a.get('format')]
            w, h = int(fmt.get('width')), int(fmt.get('height'))
            fit = min(Fraction(1920, w), Fraction(1080, h))
            sc = Fraction(960) / (w * fit)  # 半分の幅にちょうど合う拡大
            sc = max(sc, Fraction(1080) / (h * fit))
            pos = Fraction(-444444, 10000) if side == 'L' else Fraction(444444, 10000)
            el = ET.Element('video', ref=a.get('id'), lane=str(l_), name=a.get('name'), start='3600s', duration=S(t1 - t0))
            # はみ出し（中央を越える分）をクロップ。trim-rect は元の画面の高さの %（拡大前）
            over = (w * fit * sc) / 2 - 960 / 2
            if side == 'L' and over > Fraction(1, 2):
                cr = ET.SubElement(el, 'adjust-crop', mode='trim')
                ET.SubElement(cr, 'trim-rect', right=f'{float(over / sc / Fraction(108, 10)):.4f}')
            ET.SubElement(el, 'adjust-transform', position=f'{float(pos):.4f} 0', scale=f'{float(sc):.4f} {float(sc):.4f}')
            attach(el, t0)
        bump('2 分割')

    for pr in ov.get('pairs', []):
        pair(snap(pr['t0']), snap(pr['t1']), pr['left'], pr['right'], pr.get('lane', 3))

    # ---- 5) 公式サイトのスクリーンショット＋左下の商品名ラベル（A19 21:25 の型）----
    for sc_ in ov.get('screens', []):
        t0, t1 = snap(sc_['t0']), snap(sc_['t1'])
        a = still_asset(sc_['path'], sc_['w'], sc_['h'])
        el = ET.Element('video', ref=a.get('id'), lane='3', name=a.get('name'), start='3600s', duration=S(t1 - t0))
        ET.SubElement(el, 'adjust-transform', position='-47.3148 0')
        attach(el, t0)
        fake = ET.Element('title', lane='4', offset='0s', duration=S(t1 - t0))
        tx = ET.SubElement(fake, 'text')
        lines = sc_['label']
        for k, ln_ in enumerate(lines):
            ET.SubElement(tx, 'text-style').text = ln_ + ('\n' if k < len(lines) - 1 else '')
        attach(apply_template(tpl.get('product_label_bottom', 'any'), fake, tpl.res, doc_res, resources, 'product_label_bottom', {}), t0)
        bump('公式サイトの画面')

    # ---- 6) テロップの縁取り・影を外す（修正 30）----
    if ov.get('no_stroke'):
        for e in root.iter('text-style'):
            for k in ('strokeColor', 'strokeWidth', 'shadowColor', 'shadowOffset', 'shadowBlurRadius'):
                if k in e.attrib:
                    del e.attrib[k]
                    bump('外した縁取り・影')

    # ---- 7) 残っている EC・LOOK 動画も手ブレ補正（A19: 手持ちの映像は基本すべて）----
    if ov.get('stabilize_all'):
        for p, c, a in children():
            if c.tag != 'asset-clip' or lane(c) < 2:
                continue
            ar = res.get(c.get('ref'))
            if ar is None or T(ar.get('duration')) == 0 or c.find('timeMap') is not None or ar.get('hasVideo') != '1':
                continue
            if not (ar.get('name', '').startswith('E1_') or ar.get('name', '').startswith('DSCF')):
                continue  # EC・LOOK 動画だけ（アイキャッチの動き素材などは対象外）
            A = T(ar.get('start'))
            cl = ET.Element('clip', lane=c.get('lane'), offset=c.get('offset'), name=c.get('name'), start=c.get('start'),
                            duration=c.get('duration'), format=c.get('format') or ar.get('format'), tcFormat='NDF')
            for k in ('enabled',):
                if c.get(k):
                    cl.set(k, c.get(k))
            fmt = res[ar.get('format')]
            ET.SubElement(cl, 'conform-rate', scaleEnabled='0', srcFrameRate=RATE.get(fmt.get('frameDuration'), '29.97'))
            for x in c:
                if x.tag.startswith('adjust-') and x.tag != 'adjust-volume':
                    cl.append(copy.deepcopy(x))
            ET.SubElement(cl, 'adjust-volume', amount='-96dB')
            v = ET.SubElement(cl, 'video', ref=ar.get('id'), offset=S(A), duration=ar.get('duration'))
            if A:
                v.set('start', S(A))
            ET.SubElement(v, 'adjust-stabilization', type='automatic')
            for x in c:
                if x.tag == 'filter-video':
                    cl.append(copy.deepcopy(x))
            idx = list(p).index(c)
            p.remove(c)
            p.insert(idx, cl)
            bump('手ブレ補正を付けた動画')

    # ---- 8) 本編の調整レイヤー（lane 1）をまとめる ----
    if ov.get('merge_adjust'):
        ch = children()
        edges = set()
        for p, c, a in ch:
            if is_adj(c) or lane(c) < 2:
                continue
            edges.add(a)
            edges.add(a + T(c.get('duration')))

        def sig(c):
            x = copy.deepcopy(c)
            for k in ('offset', 'duration', 'start'):
                x.attrib.pop(k, None)
            return ET.tostring(x)
        l1 = sorted([(a, p, c) for p, c, a in ch if is_adj(c) and lane(c) == 1], key=lambda x: x[0])
        cur = None
        for a, p, c in l1:
            d = T(c.get('duration'))
            if cur is not None:
                ca, cp, cc, cend, cs = cur
                gap_ok = abs(ca + T(cc.get('duration')) - a) < Fraction(1, 100)
                cut_here = any(abs(e - a) < Fraction(1, 50) for e in edges)
                if gap_ok and not cut_here and sig(c) == cs:
                    cc.set('duration', S(a + d - ca))
                    p.remove(c)
                    bump('まとめた調整レイヤー')
                    continue
            cur = (a, p, c, a + d, sig(c))
        stats['調整レイヤー（lane 1）'] = sum(1 for p, c, a in children() if is_adj(c) and lane(c) == 1)

    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))
    print(stats, '->', out)


if __name__ == '__main__':
    main()
