"""組み立て済みの編集データ（assemble_lineup.py の出力）に、インサート・字幕・ラベルを型どおりに配置する。

    python3 auto_insert.py ASSEMBLED.fcpxml PLAN.json OUT.fcpxml [--coverage 0.52]

配置するもの（A19 の型）:
  - 商品紹介イン: 左に掲載用 01、右にぼかした SNS 用写真、中央に商品名（4.6 秒）
  - 台本の「デザイン」「素材」を字幕に分割し、商品区間に順番に配置（Klee 32、下中央）
    字幕の下には商品写真の B-roll（約 5 秒ずつ、拡大でズーム）、右上に Design / Material ラベル
  - 字幕のない時間にも、掲載用の写真で Silhouette ブロックを足して、重なり時間を目標値に近づける
  - 区間の最後に価格ありの中央商品名
  - OP: LOOK 写真の左右 2 枚並べと LOOK 動画のモンタージュ
  - ED: ぼかした LOOK 写真の上に、切り抜き画像と商品名の一覧（4 個＋残り）
字幕のタイミングは音声と合わせていない（台本の順番で区間に割り付け）。音声が届いたら合わせ直す。
"""
import copy
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_lineup import Donor, T, S, norm  # noqa: E402
from build_lineup import Templates, apply_template, set_transform  # noqa: E402
from fcpxml_util import append_anchor  # noqa: E402

LANE = {'photo_bg': 3, 'photo_fg': 4, 'center': 5, 'section': 6, 'subtitle': 7, 'ed_name': 8}


def split_script(text, maxlen=34):
    """台本を字幕の長さに分ける（句点で区切り、長い文は読点で分ける）。"""
    out = []
    for sent in re.split(r'(?<=。)', text.replace(' ', '').replace('　', '')):
        sent = sent.strip().rstrip('。')
        if not sent:
            continue
        if len(sent) <= maxlen:
            out.append(sent)
            continue
        parts, cur = [], ''
        for chunk in re.split(r'(?<=、)', sent):
            if cur and len(cur) + len(chunk) > maxlen:
                parts.append(cur.rstrip('、'))
                cur = chunk
            else:
                cur += chunk
        if cur:
            parts.append(cur.rstrip('、'))
        out.extend(parts)
    return out


def main():
    src, plan_path, out = sys.argv[1:4]
    coverage = float(sys.argv[sys.argv.index('--coverage') + 1]) if '--coverage' in sys.argv else 0.52
    plan = json.load(open(plan_path, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(plan_path))
    tree = ET.parse(src)
    root = tree.getroot()
    resources = root.find('resources')
    doc_res = {e.get('id'): e for e in resources}
    project = [p for p in root.iter('project') if norm(p.get('name')) == norm(plan.get('project', '本編'))][0]
    spine = project.find('sequence/spine')
    tpl = Templates(os.path.join(base, plan['templates']))
    donor = Donor(os.path.join(base, plan['donor']['fcpxml']), 'a19_', resources)
    # 既に取り込み済みのリソースは再度入れない
    for k in list(doc_res):
        if k.startswith('a19_'):
            donor.imported[k[len('a19_'):]] = True

    # ---- 素材の索引（相対パス → asset）----
    def rel(a):
        s = unicodedata.normalize('NFC', urllib.parse.unquote(a.find('media-rep').get('src')))
        return s.split(plan['asset_root'])[-1] if plan['asset_root'] in s else None

    assets = {}
    for a in resources:
        if a.tag == 'asset' and a.find('media-rep') is not None:
            r = rel(a)
            if r:
                assets[r] = a

    def folder(f):
        return [assets[k] for k in sorted(assets) if k.rsplit('/', 1)[0] == f]

    donors = {}

    def donor_assets(spec, key):
        """別の編集データ（A23 など）の素材を、パスの一部一致で探して取り込む。"""
        path = os.path.join(base, spec['fcpxml'])
        if path not in donors:
            donors[path] = Donor(path, 'd%d_' % (len(donors) + 1), resources)
        d = donors[path]
        out = []
        for rid, a in sorted(d.res.items(), key=lambda kv: kv[1].get('name') or ''):
            if a.tag != 'asset' or a.find('media-rep') is None:
                continue
            src = unicodedata.normalize('NFC', urllib.parse.unquote(a.find('media-rep').get('src')))
            if spec[key] in src:
                d.import_resource(rid)
                out.append(next(e for e in resources if e.get('id') == d.rid(rid)))
        return out

    # ---- 型の部品（A19 から）----
    proj19 = plan['donor']['project']
    zoom_f = donor.find_in_project(proj19, lambda e: e.tag == 'filter-video' and norm(e.get('name')) == '拡大')
    tilt_f = donor.find_in_project(proj19, lambda e: e.tag == 'filter-video' and norm(e.get('name')) == '基本3D')
    blur_f = donor.find_in_project(proj19, lambda e: e.tag == 'filter-video' and norm(e.get('name')) == 'ガウス')
    se_src = donor.find_in_project(proj19, lambda e: e.tag == 'asset-clip' and '決定ボタン' in norm(e.get('name')))
    # B-roll（動画）用のカラー調整: A19 で B-roll のクリップに直接当てているもの
    grade_f = donor.find_in_project(proj19, lambda e: e.tag == 'filter-video' and norm(e.get('name')) == 'カラー調整')

    # ---- 時刻 → ホストのカット ----
    hosts = []
    for e in spine:
        if e.tag == 'mc-clip':
            hosts.append((T(e.get('offset')), T(e.get('duration')), e))

    def attach(el, t):
        t = Fraction(t).limit_denominator(60000)
        for off, du, e in hosts:
            if off <= t < off + du:
                el.set('offset', S(T(e.get('start')) + (t - off)))
                append_anchor(e, el)
                return el
        return None

    fmts = {e.get('id'): e for e in resources if e.tag == 'format'}

    def half_scale(asset):
        """縦長の写真を、画面の半分の幅（960px）にぴったり合わせる拡大率（高さ合わせが基準）。"""
        f = fmts.get(asset.get('format'))
        try:
            w, h = float(f.get('width')), float(f.get('height'))
        except (AttributeError, TypeError):
            return '1.33 1.33'
        v = max(1.0, 960 / (1080 * w / h)) if w < h else 1.0
        return f'{v:.4f} {v:.4f}'

    def still(asset, dur, lane, position=None, scale=None, filters=(), crop=False):
        el = ET.Element('video', ref=asset.get('id'), lane=str(lane), name=asset.get('name'), start='3600s', duration=S(dur))
        if scale == 'half':
            scale = half_scale(asset)
        if position or scale:
            set_transform(el, position, scale)
        for f in filters:
            if f is not None:
                el.append(donor.element(f))
        return el

    def clip(asset, dur, lane, start_in=1, filters=()):
        st = T(asset.get('start')) + start_in
        el = ET.Element('asset-clip', ref=asset.get('id'), lane=str(lane), name=asset.get('name'), start=S(st), duration=S(dur))
        if asset.get('format'):
            el.set('format', asset.get('format'))
        for f in filters:
            if f is not None:
                el.append(donor.element(f))
        av = ET.Element('adjust-volume', amount='-96dB')
        el.insert(0, av)
        return el

    def title(role, variant, lines, lane, dur, ctx=None):
        fake = ET.Element('title', lane=str(lane), offset='0s', duration=S(dur))
        t = ET.SubElement(fake, 'text')
        for n, line in enumerate(lines):
            r = ET.SubElement(t, 'text-style')
            r.text = line + ('\n' if n < len(lines) - 1 else '')
        return apply_template(tpl.get(role, variant), fake, tpl.res, doc_res, resources, role, ctx or {})

    # ---- 区間（チャプター）----
    chapters = []
    for e in spine:
        for m in e.findall('chapter-marker'):
            chapters.append((T(e.get('offset')) + T(m.get('start')) - T(e.get('start')), m.get('value')))
    seen, ch = set(), []
    for t, v in sorted(chapters):
        if v not in seen:
            seen.add(v)
            ch.append((t, v))
    total = T(project.find('sequence').get('duration'))
    bounds = ch + [(total, 'END')]
    sections = [{'t0': a[0], 't1': b[0], 'chapter': a[1]} for a, b in zip(bounds, bounds[1:])]
    pp = {p['chapter']: p for p in plan['products']}
    stats = {'subtitle': 0, 'broll': 0, 'section': 0, 'price': 0, 'intro': 0, 'op': 0, 'ed': 0}

    for s in sections:
        pr = pp.get(s['chapter'])
        if not pr or ('photos' not in pr and 'donor_assets' not in pr):
            continue
        t0, t1 = s['t0'], s['t1']
        if 'donor_assets' in pr:
            da = pr['donor_assets']
            photos = donor_assets(da, 'photos')
            ec = donor_assets(da, 'ec') or photos
            videos = donor_assets(da, 'videos') if da.get('videos') else []
        else:
            photos = folder(pr['photos']) + (folder(pr['photos2']) if pr.get('photos2') else [])
            ec = folder(pr['ec'])
            videos = []
        # 1) 商品紹介イン（4.6 秒）: 左 掲載用 01、右 SNS 写真をぼかし
        if ec and photos:
            attach(still(ec[0], Fraction(46, 10), LANE['photo_fg'], '-44.4444 0', 'half'), t0)
            attach(still(photos[min(5, len(photos) - 1)], Fraction(46, 10), LANE['photo_bg'], '44.4444 0', 'half', [blur_f]), t0)
            stats['intro'] += 1
        # 2) 字幕と B-roll
        subs = [('Design', x) for x in split_script(pr.get('design', ''))] + [('Material', x) for x in split_script(pr.get('material', ''))]
        if pr.get('lines'):
            subs = [(a, b) for a, b in pr['lines']]
        w0, w1 = t0 + 8, t1 - 9
        if subs and w1 > w0:
            need = sum(max(4.0, min(10.0, len(x) / 3.6)) for _, x in subs)
            gap = max(0.0, (float(w1 - w0) - need) / (len(subs) + 1))
            t = float(w0) + gap
            pi = 0
            block = None
            for k, (sec, text) in enumerate(subs):
                d = max(4.0, min(10.0, len(text) / 3.6))
                attach(title('subtitle', 'one', [text], LANE['subtitle'], Fraction(d).limit_denominator(1000)), t)
                stats['subtitle'] += 1
                # 字幕の下の B-roll（約 5 秒ずつ）
                n = max(1, round(d / 5))
                for j in range(n):
                    dj = Fraction(d / n).limit_denominator(1000)
                    if videos and pi % 2 == 1:
                        # 置き撮りの EC 動画は基本3D で少し傾ける（A19 の型）
                        attach(clip(videos[(pi // 2) % len(videos)], dj, LANE['photo_bg'], filters=[tilt_f, grade_f]), t + j * d / n)
                    else:
                        # Design / Silhouette は前半の写真（全体）、Material / Detail は後半の写真（寄り）から順に使う
                        half = max(1, len(photos) // 2)
                        pool = photos[:half] if sec in ('Design', 'Silhouette') else (photos[half:] or photos)
                        ph = pool[pi % len(pool)]
                        zoom = '2.7 2.7' if sec in ('Design', 'Silhouette') else '4 4'
                        attach(still(ph, dj, LANE['photo_bg'], f'{(pi % 3 - 1) * 6} {(pi % 2) * 8}', zoom, [zoom_f]), t + j * d / n)
                    pi += 1
                    stats['broll'] += 1
                # セクションラベル: B-roll の上にだけ出す（字幕 1 本ぶんの B-roll ブロックごと。A19 の型）
                lbl = title('section_label', 'any', [sec], LANE['section'], Fraction(d).limit_denominator(1000))
                attach(lbl, t)
                stats['section'] += 1
                block = [sec, t, lbl, t + d]
                block[3] = t + d
                t += d + gap
                # 字幕と字幕の間が 14 秒以上空くときは、掲載用の写真で Silhouette ブロックを入れる
                if gap >= 14 and ec and k < len(subs) - 1:
                    gs = t - gap + 2
                    gl = min(10.0, gap - 4)
                    lbl = title('section_label', 'any', ['Silhouette'], LANE['section'], Fraction(gl).limit_denominator(1000))
                    attach(lbl, gs)
                    stats['section'] += 1
                    for j in range(2):
                        src_list = videos if (videos and j == 1) else ec
                        el = (clip(src_list[(k + j) % len(src_list)], Fraction(gl / 2).limit_denominator(1000), LANE['photo_bg'], filters=[tilt_f, grade_f])
                              if src_list is videos else
                              still(src_list[(k + j) % len(src_list)], Fraction(gl / 2).limit_denominator(1000), LANE['photo_bg'], '0 0', 'half' if False else '1.05 1.05'))
                        attach(el, gs + j * gl / 2)
                        stats['broll'] += 1
                    if block:
                        block[2].set('duration', S(Fraction(block[3] - block[1]).limit_denominator(1000)))
                    block = None
            if block:
                block[2].set('duration', S(Fraction(block[3] - block[1]).limit_denominator(1000)))
        # 3) 字幕のない時間に Silhouette ブロック（掲載用の写真）を足す
        covered = sum(max(4.0, min(10.0, len(x) / 3.6)) for _, x in subs) + 4.6
        target = coverage * float(t1 - t0)
        if ec and covered < target:
            blocks = int((target - covered) // 10)
            span0, span1 = float(t0) + 8, float(t1) - 9
            if not subs and blocks:
                step = (span1 - span0) / blocks
                for b in range(blocks):
                    tb = span0 + b * step + max(0, step - 10) / 2
                    lbl = title('section_label', 'any', ['Silhouette' if b % 2 == 0 else 'Detail'], LANE['section'], Fraction(10))
                    attach(lbl, tb)
                    for j in range(2):
                        src_list = ec if b % 2 == 0 else photos
                        attach(still(src_list[(2 * b + j) % len(src_list)], Fraction(5), LANE['photo_bg'],
                                     '0 0', '1.05 1.05' if b % 2 == 0 else '3.2 3.2', [zoom_f] if b % 2 else []), tb + 5 * j)
                        stats['broll'] += 1
                    stats['section'] += 1
        # 4) 価格ありの中央商品名（区間の最後）
        if pr.get('price') and ec:
            tp = t1 - Fraction(7)
            attach(still(ec[0], Fraction(3), LANE['photo_bg'], '0 0', '1.05 1.05'), tp)
            attach(title('product_center', 'price', [pr['name'], f"Color : {pr['color']} | Size : {pr['sizes']}", pr['price'], ' - tax in'],
                         LANE['center'], Fraction(3)), tp)
            stats['price'] += 1

    # ---- OP: LOOK 写真の 2 枚並べと LOOK 動画 ----
    op = plan.get('op_look')
    if op:
        looks = folder(op['photos'])
        vids = [a for a in folder(op['videos']) if float(T(a.get('duration'))) >= 4]
        t, k, vi = float(op['t0']), 0, 0
        step = max(1, len(looks) // 24)
        while t < float(op['t1']) - 2.8:
            if k % 2 == 0 and looks:
                a = looks[(k // 2 * step) % len(looks)]
                b = looks[(k // 2 * step + 1) % len(looks)]
                attach(still(a, Fraction(28, 10), LANE['photo_bg'], '-44.4444 0', 'half'), t)
                attach(still(b, Fraction(28, 10), LANE['photo_fg'], '44.4444 0', 'half'), t)
                t += 2.8
            elif vids:
                attach(clip(vids[vi % len(vids)], Fraction(24, 10), LANE['photo_bg'], filters=[tilt_f, grade_f]), t)
                vi += 1
                t += 2.4
            k += 1
            stats['op'] += 1

    # ---- ED: 一覧 ----
    ed = next((s for s in sections if s['chapter'] == 'ED'), None)
    cut = [p for p in plan['products'] if p.get('cutout') and p['cutout'] in assets]
    if ed and cut:
        te = ed['t0'] + Fraction(1)
        looks = folder(op['photos']) if op else []
        if looks:
            attach(still(looks[len(looks) // 2], Fraction(64, 10), 2, '0 23.3333', '2.68 2.68', [blur_f]), te)
        attach(title('collection_label_center', 'any', [plan['collection'], plan['release_line']], LANE['center'], Fraction(64, 10)), te)
        pages = [cut[:4], cut[4:]]
        xs = {4: [62.5093, 23.0556, -16.3889, -60.1944], 3: [44.4444, 0, -44.4444], 2: [27.7778, -27.7778], 1: [0]}
        tp = te
        for page in pages:
            if not page:
                continue
            d = Fraction(34, 10) if page is pages[0] else Fraction(30, 10)
            for n, p in enumerate(reversed(page)):
                x = xs[len(page)][n]
                attach(still(assets[p['cutout']], d, LANE['ed_name'] + 2 + n, f'{x} 2', '0.42 0.42'), tp)
                nm = title('ed_product_name', 'any', [p['name'], f"Color : {p['color']} | Size : {p['sizes']}", p.get('price', ''), ' - tax in'],
                           LANE['ed_name'] + 6 + n, d, {'group_size': len(page), 'index': n})
                # 画像の下端に合わせる（A18 と同じ y -24.9。列の x はページの商品数で決める）
                set_transform(nm, f'{x} -24.8971', '0.6 0.6')
                attach(nm, tp)
            tp += d
            stats['ed'] += 1
        if se_src is not None:
            x = donor.element(se_src)
            x.set('lane', '-1')
            attach(x, te)

    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))
    print('placed', stats, '->', out)


if __name__ == '__main__':
    main()
