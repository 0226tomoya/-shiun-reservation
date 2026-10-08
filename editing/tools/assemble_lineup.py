"""粗編集（トークのジャンプカット＋チャプターマーカー）に、ラインナップの型を組み付ける。

    python3 assemble_lineup.py ROUGH.fcpxml PLAN.json OUT.fcpxml

PLAN.json の例は editing/plans/A24_plan.json。やること:
  1. メインカメラの各カットに lane 1 の調整レイヤー（A19 のカラー調整＋区間ごとの構図プリセット）を付ける
  2. OP: 名前カード（0 秒〜）、左上のコレクション名（トーク中）
  3. 各商品区間: 頭にアイキャッチ（スパインに挿入）、中央商品名（紹介イン）、左上の商品名ラベル（カットごと）
  4. BGM（A19 と同じ複合クリップ、-17dB ループ）、ED の最後にエンディング動画
素材（アイキャッチ、BGM、エンディング、カウントダウン）とカラー調整は A19 の編集データからそのままコピーする。
"""
import copy
import json
import os
import sys
import unicodedata
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_lineup import Templates, apply_template, set_param, set_transform  # noqa: E402
from fcpxml_util import append_anchor  # noqa: E402

VARIANTS = {  # 同じ区間の中で約 40 秒ごとに少しずらす（A19 の寄りは x 17 / 24 / 35、中は 9.4 / 4.4）
    'tight': ['17.037 -24.7161', '23.9815 -24.7161', '35 -24.7161'],
    # 中の区間は、中と引きを交互に（A19 の配分: 寄り 56% / 中 21% / 引き 23%）
    'mid': [('9.44444 1.85185', '1.21 1.21'), ('-0.0555556 -2.53704', '1.05 1.05'), ('4.35185 0.925926', '1.21 1.21'), ('-0.0555556 -2.53704', '1.05 1.05')],
}
FRAMING = {  # A19（4K 単カメ・立ち）の構図プリセット
    'op_tight': ('-7.46296 -29.4719', '1.92 1.92'),
    'tight': ('17.037 -24.7161', '1.82 1.82'),
    'mid': ('9.44444 1.85185', '1.21 1.21'),
    'wide': ('-0.0555556 -2.53704', '1.05 1.05'),
}


# A19 の構図プリセットは、A24 の引きの画（鼻 0.49, 0.25・胴の長さ＝画面の高さの 0.20）に当てたときの仕上がりを目標にする
REF = (0.49, 0.25, 0.20)


def adaptive_framing(mcs, subject, preset_of, chapter_of):
    """カットごとに測った人の位置から、プリセットと同じ仕上がり（鼻の位置・胴の大きさ）になる拡大・位置を逆算する。
    同じ構図・同じ素材が続くまとまりは値を揃える（ちらつかせない）。拡大は 1 倍以上、画面の外が見えない範囲に収める。"""
    import statistics
    if len(subject) != len(mcs):
        print('subject: カット数が合わないので構図はプリセットのまま', len(subject), len(mcs))
        return {}

    def geo(r):
        L = r.get('lm')
        if not L or min(L['ls'][2], L['rs'][2], L['lh'][2], L['rh'][2]) < 0.5:
            return None
        torso = (L['lh'][1] + L['rh'][1]) / 2 - (L['ls'][1] + L['rs'][1]) / 2
        return (L['nose'][0], L['nose'][1], torso) if 0.05 < torso < 1.5 else None

    blocks, cur, key0 = [], [], None
    for e, r in zip(mcs, subject):
        key = (chapter_of(e), preset_of(e), r.get('src'))
        if key != key0 and cur:
            blocks.append((key0, cur))
            cur = []
        cur.append((e, r))
        key0 = key
    if cur:
        blocks.append((key0, cur))
    by_src = {}
    for e, r in zip(mcs, subject):
        g_ = geo(r)
        if g_:
            by_src.setdefault(r.get('src'), []).append(g_)
    out = {}
    for (ch, (p, sc), src), members in blocks:
        gs = [g_ for g_ in (geo(r) for _, r in members) if g_] or by_src.get(src) or []
        if not gs:
            continue
        x, y, torso = (statistics.median(v[i] for v in gs) for i in range(3))
        s0 = float(sc.split()[0])
        px0, py0 = (float(v) for v in p.split())
        xt = 0.5 + (REF[0] - 0.5) * s0 + px0 * 10.8 / 1920
        yt = 0.5 + (REF[1] - 0.5) * s0 - py0 * 0.01
        s = max(1.0, REF[2] * s0 / torso)
        px = (xt - 0.5 - (x - 0.5) * s) / (10.8 / 1920)
        py = (0.5 + (y - 0.5) * s - yt) / 0.01
        lim_x, lim_y = (s - 1) / 2 * 1920 / 10.8, (s - 1) / 2 * 100
        px, py = max(-lim_x, min(lim_x, px)), max(-lim_y, min(lim_y, py))
        for e, _ in members:
            out[id(e)] = (f'{px:.4f} {py:.4f}', f'{s:.4f} {s:.4f}')
    return out


def T(s):
    s = (s or '0s').rstrip('s')
    return Fraction(s) if s else Fraction(0)


def S(fr):
    fr = Fraction(fr).limit_denominator(240000)
    return f'{fr.numerator}s' if fr.denominator == 1 else f'{fr.numerator}/{fr.denominator}s'


def norm(s):
    return unicodedata.normalize('NFC', s or '')


class Donor:
    """A19 など、部品を借りてくる編集データ。リソース ID は接頭辞を付けて取り込む。"""

    def __init__(self, path, prefix, doc_resources):
        self.root = ET.parse(path).getroot()
        self.res = {e.get('id'): e for e in self.root.find('resources')}
        self.prefix = prefix
        self.doc_resources = doc_resources
        self.imported = {}

    def rid(self, old):
        return self.prefix + old

    def import_resource(self, rid):
        if rid in self.imported or rid not in self.res:
            return
        self.imported[rid] = True
        el = copy.deepcopy(self.res[rid])
        self._remap(el)
        for x in self.res[rid].iter():
            for k in ('ref', 'format'):
                if x.get(k) and x.get(k) in self.res:
                    self.import_resource(x.get(k))
        self.doc_resources.append(el)

    def _remap(self, el):
        for x in el.iter():
            for k in ('id', 'ref', 'format'):
                if x.get(k) and x.get(k) in self.res:
                    x.set(k, self.rid(x.get(k)))

    def element(self, el):
        """部品要素をコピーして、参照するリソースを取り込む。"""
        e = copy.deepcopy(el)
        for x in el.iter():
            for k in ('ref', 'format'):
                if x.get(k) and x.get(k) in self.res:
                    self.import_resource(x.get(k))
        self._remap(e)
        return e

    def find_resource(self, tag, name):
        return next((e for e in self.res.values() if e.tag == tag and norm(e.get('name')) == norm(name)), None)

    def find_in_project(self, project, pred):
        p = [p for p in self.root.iter('project') if norm(p.get('name')) == norm(project)][0]
        for e in p.iter():
            if pred(e):
                return e
        return None


def main():
    rough, plan_path, out = sys.argv[1:4]
    plan = json.load(open(plan_path, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(plan_path))
    tree = ET.parse(rough)
    root = tree.getroot()
    resources = root.find('resources')
    doc_res = {e.get('id'): e for e in resources}
    project = [p for p in root.iter('project') if norm(p.get('name')) == norm(plan.get('project', '本編'))][0]
    seq = project.find('sequence')
    spine = seq.find('spine')

    donor = Donor(os.path.join(base, plan['donor']['fcpxml']), 'a19_', resources)
    tpl = Templates(os.path.join(base, plan['templates']))

    # ---- 部品 ----
    grade_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'title' and e.get('lane') == '1'
                                      and e.get('name') == 'Adjustment Layer' and e.find('filter-video') is not None)
    eyecatch_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'ref-clip' and norm(e.get('name')) == 'アイキャッチ')
    ending_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'asset-clip' and norm(e.get('name')) == 'エンディング')
    countdown_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'asset-clip' and e.get('name') == '7')
    bgm_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'ref-clip' and norm(e.get('name')) == 'BGM')

    # ---- チャプターから区間を作る ----
    items = list(spine)
    pos = Fraction(0)
    chapters = []
    for e in items:
        for m in e.findall('chapter-marker'):
            chapters.append((T(e.get('offset')) + T(m.get('start')) - T(e.get('start')), m.get('value')))
    chapters = sorted(set(chapters))
    seen, ch = set(), []
    for t, v in chapters:
        if v not in seen:
            seen.add(v)
            ch.append((t, v))
    chapters = ch
    total = T(seq.get('duration'))
    bounds = [(Fraction(0), 'OP')] + chapters + [(total, 'END')]
    sections = []
    for (t0, name), (t1, _) in zip(bounds, bounds[1:]):
        sections.append({'t0': t0, 't1': t1, 'chapter': name})
    prod_plan = {p['chapter']: p for p in plan['products']}
    k = 0
    for s in sections:
        if s['chapter'] in prod_plan:
            s['product'] = prod_plan[s['chapter']]
            s['framing'] = plan['framing']['products'][k % len(plan['framing']['products'])]
            k += 1
        elif s['chapter'] == 'OP':
            s['framing'] = plan['framing']['op']
        else:
            s['framing'] = plan['framing'].get('ed', 'mid')

    def section_at(t):
        return next(s for s in sections if s['t0'] <= t < s['t1'] or s is sections[-1])

    # ---- フレームの格子と編集点（auto_insert と同じ規則で、紹介インの終わり・名前カードの終わりを決める）----
    FD = T(doc_res[seq.get('format')].get('frameDuration'))
    CUTS = sorted({x for e in items if e.tag == 'mc-clip' for x in (T(e.get('offset')), T(e.get('offset')) + T(e.get('duration')))})

    def snapf(t):
        return round(Fraction(t) / FD) * FD

    def near_cut(t, tol):
        # tol の中になければ 2 倍まで広げて探す（auto_insert.end_on_cut と同じ規則）
        for w in (tol, 2 * tol):
            c = min((x for x in CUTS if abs(x - t) <= w), key=lambda x: abs(x - t), default=None)
            if c is not None:
                return c
        return snapf(t)

    name_end = near_cut(Fraction(47, 10), Fraction(7, 10))

    def intro_start(sec):
        """A19 は区間の頭（アイキャッチの後）1.4〜2.3 秒、左上のコレクション名でトークを見せてから紹介インに入る。"""
        c = [x for x in CUTS if sec['t0'] + Fraction(14, 10) <= x <= sec['t0'] + Fraction(26, 10)]
        return min(c) if c else sec['t0']

    def intro_end(sec):
        return near_cut(intro_start(sec) + Fraction(str(plan.get('label_delay', 4.6))), Fraction(8, 10))

    # ---- テロップ生成のヘルパー ----
    def make_title(role, variant, texts, lane, offset, duration, ctx=None, start=None):
        tp = tpl.get(role, variant)
        fake = ET.Element('title', lane=str(lane), offset=S(offset), duration=S(duration))
        t = ET.SubElement(fake, 'text')
        for n, line in enumerate(texts):
            r = ET.SubElement(t, 'text-style')
            nxt = texts[n + 1] if n < len(texts) - 1 else None
            r.text = line + ('\n' if nxt is not None and not nxt.startswith(' - ') and not line.endswith('\n') else '')
        new = apply_template(tp, fake, tpl.res, doc_res, resources, role, ctx or {})
        if start is not None:
            new.set('start', S(start))
        return new

    # ---- 1. メインカメラの各カット ----
    def preset_for(off, sec):
        p, sc = FRAMING[sec['framing']]
        if sec['framing'] in VARIANTS and 'product' in sec:
            v = VARIANTS[sec['framing']]
            p = v[int((off - sec['t0']) // 40) % len(v)]
            if isinstance(p, tuple):
                p, sc = p
        return p, sc

    mcs = [e for e in items if e.tag == 'mc-clip']
    adaptive = {}
    if plan.get('subject'):
        adaptive = adaptive_framing(mcs, json.load(open(os.path.join(base, plan['subject']))),
                                    lambda e: preset_for(T(e.get('offset')), section_at(T(e.get('offset')))),
                                    lambda e: section_at(T(e.get('offset')))['chapter'])
    # 画角の指定（ユーザーの修正）: OP は参考画像の構図（plan.op_ref: 鼻の x・y、胴の長さ）、
    # framing_overrides の区間は item（商品紹介の画角 = 商品区間の中のプリセット）か full（全身 = 拡大なし）
    def framing_mode(off, du, sec):
        mid_ = float(off + du / 2)
        for o in plan.get('framing_overrides', []):
            if o['t0'] <= mid_ < o['t1']:
                return o['mode']
        if sec['chapter'] == 'OP' and plan.get('op_ref'):
            return 'op'
        return None

    mode_framing = {}
    if plan.get('subject'):
        import statistics as _st
        subj_ = json.load(open(os.path.join(base, plan['subject'])))
        groups_, cur_, key_ = [], [], None
        for e_, r_ in zip(mcs, subj_):
            off_, du_ = T(e_.get('offset')), T(e_.get('duration'))
            m_ = framing_mode(off_, du_, section_at(off_))
            k_ = (m_, r_.get('src'))
            if k_ != key_ and cur_:
                groups_.append((key_, cur_))
                cur_ = []
            cur_.append((e_, r_))
            key_ = k_
        if cur_:
            groups_.append((key_, cur_))
        for (m_, src_), mem_ in groups_:
            if not m_:
                continue
            if m_ == 'full':
                for e_, _ in mem_:
                    mode_framing[(m_, id(e_))] = ('0 0', '1 1')
                continue
            gs_ = []
            for _, r_ in mem_:
                L_ = r_.get('lm')
                if L_ and min(L_['ls'][2], L_['rs'][2], L_['lh'][2], L_['rh'][2]) >= 0.5:
                    tor_ = (L_['lh'][1] + L_['rh'][1]) / 2 - (L_['ls'][1] + L_['rs'][1]) / 2
                    if 0.05 < tor_ < 1.5:
                        gs_.append((L_['nose'][0], L_['nose'][1], tor_))
            if not gs_:
                continue
            x_, y_, tor_ = (_st.median(v[i] for v in gs_) for i in range(3))
            if m_ == 'op':
                xt_, yt_, tt_ = plan['op_ref']
            else:  # item: 商品区間の中の画角（プリセット mid の 1 つ目）を、A24 の引きの画に当てた仕上がり
                p0_, s0_ = FRAMING['mid']
                s0_ = float(s0_.split()[0])
                px0_, py0_ = (float(v) for v in p0_.split())
                xt_ = 0.5 + (REF[0] - 0.5) * s0_ + px0_ * 10.8 / 1920
                yt_ = 0.5 + (REF[1] - 0.5) * s0_ - py0_ * 0.01
                tt_ = REF[2] * s0_
            s_ = max(1.0, tt_ / tor_)
            px_ = (xt_ - 0.5 - (x_ - 0.5) * s_) / (10.8 / 1920)
            py_ = (0.5 + (y_ - 0.5) * s_ - yt_) / 0.01
            lx_, ly_ = (s_ - 1) / 2 * 1920 / 10.8, (s_ - 1) / 2 * 100
            px_, py_ = max(-lx_, min(lx_, px_)), max(-ly_, min(ly_, py_))
            for e_, _ in mem_:
                mode_framing[(m_, id(e_))] = (f'{px_:.4f} {py_:.4f}', f'{s_:.4f} {s_:.4f}')
    log = {'adjustment': 0, 'product_label': 0, 'collection_label': 0}
    for e in items:
        if e.tag != 'mc-clip':
            continue
        off, st, du = T(e.get('offset')), T(e.get('start')), T(e.get('duration'))
        sec = section_at(off)
        g = donor.element(grade_src)
        g.set('lane', '1')
        g.set('offset', S(st))
        g.set('duration', S(du))
        p, sc = adaptive.get(id(e)) or preset_for(off, sec)
        mode = framing_mode(off, du, sec)
        if mode:
            p, sc = mode_framing.get((mode, id(e))) or (p, sc)
        set_transform(g, p, sc)
        append_anchor(e, g)
        log['adjustment'] += 1
        # OP: コレクション名（名前カードの後〜OP の終わり）。商品区間の頭（紹介インの前）にも出す（A19）
        if (sec['chapter'] == 'OP' and off >= name_end) or ('product' in sec and off < intro_start(sec)):
            append_anchor(e, make_title('collection_label', 'any', [plan['collection'], plan['release_line']], 2, st, du))
            log['collection_label'] += 1
        # 商品区間: 紹介インの後は左上に商品名ラベル
        ls = intro_end(sec) if 'product' in sec else None
        if ls is not None and off + du > ls:
            # 紹介インが終わった瞬間から出す（カットの途中からでも。A18/A19 は 0.0 秒後）
            pr = sec['product']
            a0 = max(off, ls)
            append_anchor(e, make_title('product_label', 'plain', [pr['name'], f"Color : {pr['color']} | Size : {pr['sizes']}"], 2,
                                        st + (a0 - off), off + du - a0))
            log['product_label'] += 1

    # ---- 2. OP の名前カード ----
    first = next(e for e in items if e.tag == 'mc-clip')
    append_anchor(first, make_title('name_card', 'any', ['WAMU', '/Fashion YouTuber\n/shiun Director'], 2, T(first.get('start')), name_end))

    # ---- 3. 中央商品名（各商品区間の頭 4.6 秒）----
    for s in sections:
        if 'product' not in s:
            continue
        i0 = intro_start(s)
        host = next(e for e in items if e.tag == 'mc-clip' and T(e.get('offset')) <= i0 < T(e.get('offset')) + T(e.get('duration')))
        pr = s['product']
        append_anchor(host, make_title('product_center', 'plain', [pr['name'], f"Color : {pr['color']} | Size : {pr['sizes']}"], 5,
                               T(host.get('start')) + (i0 - T(host.get('offset'))), intro_end(s) - i0))

    # ---- 5. スパインへの挿入（アイキャッチ・カウントダウン・エンディング）----
    new_items = []
    inserts = []
    first_prod_ = next((s for s in sections if 'product' in s), None)
    for s in sections:
        if ('product' in s or s['chapter'] == 'ED') and eyecatch_src is not None:
            if plan.get('no_eyecatch_after_countdown') and s is first_prod_:
                continue  # カウントダウンの後はそのまま本編（A19 と同じ。修正 20）
            inserts.append((s['t0'], 'eyecatch'))  # 各商品の頭と ED の頭（A19 と同じ）
    if plan.get('countdown') and countdown_src is not None:
        first_prod = next(s for s in sections if 'product' in s)
        inserts.append((first_prod['t0'] - Fraction(1, 1000), 'countdown'))
    inserts.sort()
    ins_i = 0
    for e in items:
        off = T(e.get('offset'))
        while ins_i < len(inserts) and inserts[ins_i][0] <= off:
            kind = inserts[ins_i][1]
            src = eyecatch_src if kind == 'eyecatch' else countdown_src
            x = donor.element(src)
            for ch in list(x):
                if ch.get('lane') is not None:
                    x.remove(ch)
            new_items.append(x)
            ins_i += 1
        new_items.append(e)
    if ending_src is not None:
        x = donor.element(ending_src)
        for ch in list(x):
            if ch.get('lane') is not None:
                x.remove(ch)
        new_items.append(x)
    for e in list(spine):
        spine.remove(e)
    cur = Fraction(0)
    for e in new_items:
        e.set('offset', S(cur))
        spine.append(e)
        cur += T(e.get('duration'))
    seq.set('duration', S(cur))

    # ---- 4. BGM: カウントダウンの間は止め、その後から続きを流す。ED の一覧で +8dB（A19 の型）----
    if bgm_src is not None:
        absol = {}
        acc = Fraction(0)
        for e in new_items:
            absol[id(e)] = acc
            acc += T(e.get('duration'))
        cd = next((e for e in new_items if norm(e.get('name')) == '7'), None)
        cd_t0 = absol[id(cd)] if cd is not None else None
        cd_t1 = cd_t0 + T(cd.get('duration')) if cd is not None else None
        ed_t = next((t for t, v in chapters if v == 'ED'), None)

        def bgm(host, local_off, start, dur, keys=()):
            b = donor.element(bgm_src)
            b.set('lane', '-1')
            b.set('offset', S(local_off))
            b.set('start', S(start))
            b.set('duration', S(dur))
            for kf in list(b):
                if kf.tag == 'adjust-volume':
                    b.remove(kf)
            av = ET.Element('adjust-volume')
            prm = ET.SubElement(av, 'param', name='amount')
            ET.SubElement(prm, 'fadeOut', type='easeIn', duration=S(Fraction(1425, 1000)))
            if keys:
                ka = ET.SubElement(prm, 'keyframeAnimation')
                for t, v in keys:
                    ET.SubElement(ka, 'keyframe', time=S(t), value=v)
            b.insert(0, av)
            append_anchor(host, b)

        first_host = next(e for e in new_items if e.tag == 'mc-clip')
        if cd is None:
            bgm(first_host, T(first_host.get('start')), Fraction(0), cur)
        else:
            bgm(first_host, T(first_host.get('start')), Fraction(0), cd_t0)
            after = new_items[new_items.index(cd) + 1]
            seg_start = cd_t0  # 曲の続きから
            keys = []
            if ed_t is not None:
                # ED（チャプター）は挿入前の時刻なので、挿入分を足して絶対時刻にする
                # ED チャプターは挿入前の時刻なので、ED より前に挿入した要素（カウントダウン・アイキャッチ）の長さを足す
                ed_abs = min((absol[id(e)] + T(m.get('start')) - T(e.get('start')) for e in new_items
                              for m in e.findall('chapter-marker') if m.get('value') == 'ED'), default=ed_t) + 1  # 一覧は ED の 1 秒後
                local = lambda t: seg_start + (t - cd_t1)
                keys = [(local(ed_abs - Fraction(13, 10)), '0dB'), (local(ed_abs), '8dB'), (local(ed_abs + Fraction(128, 10)), '8dB'), (local(ed_abs + Fraction(141, 10)), '0dB')]
            bgm(after, T(after.get('start') or '0s'), seg_start, cur - cd_t1, keys)

    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))
    print(f"sections: {[(s['chapter'], round(float(s['t0']), 1)) for s in sections]}")
    print(f'log: {log}  inserts: {len(inserts)}  duration: {float(cur):.1f}s -> {out}')


if __name__ == '__main__':
    main()
