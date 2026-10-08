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


LABEL_RULES = [  # 字幕の語 → セクションラベル（A18/A19/A23 で、素材系の語は 37/37 が Material、丈・身幅系は Silhouette が最多）
    ('Material', r'素材|生地|糸|編み|織|合皮|ウール|コットン|ポリエステル|リネン|レーヨン|牛革|ナイロン|ゲージ'),
    ('Silhouette', r'シルエット|丈|身幅|肩幅|落ち感|ストレート|フレア|脚|ワイド|テーパード|股上|股下'),
    ('Detail', r'ボタン|衿|襟|リブ|ポケット|天巾|天幅|サドル|ステッチ|ソール|コバ|踵|ゴム|バックル|ファスナー|ジップ'),
]


def label_for(text, default):
    for name, pat in LABEL_RULES:
        if re.search(pat, text):
            return name
    return default


def split_script(text, maxlen=40, minlen=14):
    """台本を字幕に分ける（A19 の型: 1 文 = 1 枚、約 33 文字。40 文字を超える文は読点で 2 行にする）。"""
    out = []
    for sent in re.split(r'(?<=。)', text.replace(' ', '').replace('\u3000', '')):
        sent = sent.strip().rstrip('。')
        if not sent:
            continue
        if len(sent) <= maxlen:
            out.append(sent)
            continue
        # 読点で区切り、短すぎる断片は隣とつなぐ
        chunks = [c for c in re.split(r'(?<=、)', sent) if c]
        parts, cur = [], ''
        for c in chunks:
            if cur and len(cur) + len(c) > maxlen and len(cur) >= minlen:
                parts.append(cur)
                cur = c
            else:
                cur += c
        if cur:
            if parts and len(cur) < minlen:
                parts[-1] += cur
            else:
                parts.append(cur)
        for p in parts:
            p = p.rstrip('、')
            if len(p) > maxlen:
                # 2 行にする（真ん中に近い読点で改行）
                cands = [m.end() for m in re.finditer('、', p)]
                if cands:
                    k = min(cands, key=lambda x: abs(x - len(p) / 2))
                    p = p[:k] + '\n' + p[k:]
            out.append(p)
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
    tpl2 = Templates(os.path.join(base, plan['templates_extra'])) if plan.get('templates_extra') else None
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

    # ---- フレームの格子と編集点 ----
    seq_fmt = doc_res[project.find('sequence').get('format')]
    FD = T(seq_fmt.get('frameDuration'))  # 本編は 59.94p（1001/60000 秒）

    def snapf(t):
        """いちばん近いフレームの頭に揃える（A19 はすべての要素がフレームの格子に乗っている）。"""
        return round(Fraction(t) / FD) * FD

    CUTS = sorted({x for off, du, _ in hosts for x in (off, off + du)})

    def near_cut(t, lo, hi):
        """[lo, hi] の中で t にいちばん近いメインの編集点。なければ None。"""
        import bisect
        i = bisect.bisect_left(CUTS, Fraction(lo))
        best = None
        while i < len(CUTS) and CUTS[i] <= hi:
            if best is None or abs(CUTS[i] - Fraction(t)) < abs(best - Fraction(t)):
                best = CUTS[i]
            i += 1
        return best

    def end_on_cut(t, d, tol=Fraction(6, 10)):
        """t から約 d 秒の長さを、終わりが編集点に来るように決める（±tol に編集点がなければフレームに揃えた d）。"""
        t, d = Fraction(t), Fraction(d)
        e = near_cut(t + d, t + d - tol, t + d + tol) or near_cut(t + d, t + d - 2 * tol, t + d + 2 * tol)
        return (e if e is not None else snapf(t + d)) - t

    def attach(el, t):
        # 頭と終わりをフレームの格子に揃える
        t = snapf(t)
        if el.get('duration'):
            end = snapf(t + T(el.get('duration')))
            el.set('duration', S(max(FD, end - t)))
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

    punch_src = donor.find_in_project(proj19, lambda e: e.tag == 'title' and norm(e.get('name')) == 'Adjustment Layer'
                                      and e.get('lane') not in (None, '1') and e.find('adjust-transform') is not None
                                      and e.find('filter-video') is not None)
    punch_n = [0]

    def punch(t, dur, lane):
        """B-roll（動画）の上に調整レイヤーを置いて寄る（A19 は拡大 1.07〜1.55 を 84 か所）。"""
        if punch_src is None:
            return
        x = donor.element(punch_src)
        for ch in list(x):
            if ch.tag in ('marker', 'chapter-marker', 'keyword') or ch.get('lane') is not None:
                x.remove(ch)
        sc = ['1.21 1.21', '1.29 1.29', '1.15 1.15', '1.55 1.55'][punch_n[0] % 4]
        punch_n[0] += 1
        set_transform(x, f'{(punch_n[0] % 3 - 1) * 3} {(punch_n[0] % 2) * 3}', sc)
        x.set('lane', str(lane))
        x.set('duration', S(Fraction(dur).limit_denominator(1000)))
        attach(x, t)

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
        t_main = tpl.get(role, variant)
        if t_main is None and tpl2 is not None:
            # A19 にない型（発売日の中央表示など）は A18 から
            return apply_template(tpl2.get(role, variant), fake, tpl2.res, doc_res, resources, role, ctx or {})
        return apply_template(t_main, fake, tpl.res, doc_res, resources, role, ctx or {})

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
        # 紹介インの長さは 4.6 秒前後で、終わりを編集点に（商品名ラベルの出だしと同じ規則。assemble_lineup.intro_end）
        di = end_on_cut(t0, Fraction(str(plan.get('label_delay', 4.6))), Fraction(8, 10))
        if ec and photos:
            attach(still(ec[0], di, LANE['photo_fg'], '-44.4444 0', 'half'), t0)
            attach(still(photos[min(5, len(photos) - 1)], di, LANE['photo_bg'], '44.4444 0', 'half', [blur_f]), t0)
            stats['intro'] += 1
        # 2) 字幕と B-roll（A19 の組み方）
        # - 字幕 3 本のかたまりごとに、続いた 1 つのインサート（中央値 16 秒）を敷く。トークの間は 15 秒前後空ける
        # - インサートの頭・終わり・中の切り替わりは、メインの編集点に揃える（話の途中で切れない）
        # - 1 カットは 4.8 秒前後（3〜7 秒の範囲で一番近い編集点）
        last_sub_end = None
        subs = [('Design', x) for x in split_script(pr.get('design', ''))] + [('Material', x) for x in split_script(pr.get('material', ''))]
        if pr.get('lines'):
            subs = [(a, b) for a, b in pr['lines']]
        w0, w1 = t0 + 8, t1 - 9
        used = {}
        pi = [0]

        def pieces(a, b):
            """[a, b] を、編集点で 4.8 秒前後のカットに分ける。"""
            out, s0 = [], a
            while b - s0 > Fraction(7):
                c = (near_cut(s0 + Fraction(48, 10), s0 + 3, min(s0 + 7, b - 3))
                     or near_cut(s0 + Fraction(48, 10), s0 + 2, min(s0 + 9, b - Fraction(15, 10))))
                if c is None:
                    c = snapf(s0 + Fraction(48, 10))
                out.append((s0, c))
                s0 = c
            out.append((s0, b))
            return out

        def pick_video(dur):
            for _ in range(len(videos)):
                v = videos[(pi[0] // 2) % len(videos)]
                pi[0] += 1
                if T(v.get('duration')) >= dur + Fraction(1, 2):
                    return v, (1 if T(v.get('duration')) >= dur + 1 else Fraction(1, 4))
            return None, 0

        def lay(a, b, sec):
            """インサートのかたまり [a, b] を敷く。"""
            for pa, pb in pieces(a, b):
                d = pb - pa
                v, st_in = pick_video(d) if (videos and pi[0] % 2 == 1) else (None, 0)
                if v is not None:
                    # 置き撮りの EC 動画は基本3D で少し傾け、上に寄りの調整レイヤー（A19 の型）
                    attach(clip(v, d, LANE['photo_bg'], start_in=st_in, filters=[tilt_f, grade_f]), pa)
                    punch(pa, d, LANE['photo_fg'])
                else:
                    if videos and pi[0] % 2 == 1:
                        pi[0] += 1
                    # Design / Silhouette は前半の写真（全体）、Material / Detail は後半の写真（寄り）を優先し、使用回数の少ないものから
                    half = max(1, len(photos) // 2)
                    pref = photos[:half] if sec in ('Design', 'Silhouette', None) else (photos[half:] or photos)
                    pool = pref + [x for x in photos + ec if x not in pref]
                    ph = min(pool, key=lambda x: (used.get(x.get('id'), 0), pool.index(x)))
                    used[ph.get('id')] = used.get(ph.get('id'), 0) + 1
                    zoom = '2.7 2.7' if sec in ('Design', 'Silhouette', None) else '4 4'
                    attach(still(ph, d, LANE['photo_bg'], f'{(pi[0] % 3 - 1) * 6} {(pi[0] % 2) * 8}', zoom, [zoom_f]), pa)
                    pi[0] += 1
                stats['broll'] += 1

        def fill_talk(g0, g1):
            """トークだけが続く所に、字幕なしのインサート（約 14 秒）を「トーク約 15 秒 ↔ インサート」の間隔で入れる。
            前後は 8 秒以上トークを見せる（A19 はトークの間が中央値 15.5 秒、インサートのかたまりが中央値 16.4 秒）。"""
            if g1 - g0 < 26 or not ec:
                return
            n = max(1, round((g1 - g0 - 15) / 29))
            while n > 1 and (g1 - g0 - 15 * (n + 1)) / n < 8:
                n -= 1
            L = min(Fraction(16), (g1 - g0 - 15 * (n + 1)) / n) if n > 1 else min(Fraction(16), (g1 - g0) - 16)
            talk = (g1 - g0 - n * L) / (n + 1)
            for k in range(n):
                s_ = g0 + talk * (k + 1) + L * k
                a = near_cut(s_, s_ - 2, s_ + 2) or snapf(s_)
                b = near_cut(a + L, a + L - 2, a + L + 2) or snapf(a + L)
                if b - a >= 6:
                    lay(a, b, None)

        if subs and w1 > w0:
            durs = [Fraction(max(4.0, min(10.0, len(x) / 3.6))).limit_denominator(100) for _, x in subs]
            K = 3
            clusters = [list(range(k, min(k + K, len(subs)))) for k in range(0, len(subs), K)]
            need = sum(durs) + Fraction(18, 10) * len(subs)  # 字幕の間（編集点 1 つ分）と、編集点に揃える分
            outer = max(Fraction(3), (w1 - w0 - need) / (len(clusters) + 1))
            t = w0 + outer
            prev_end = w0
            block = None
            for ci, cl in enumerate(clusters):
                a = near_cut(t, t - 2, t + 2) or near_cut(t, t - 5, t + 5) or snapf(t)
                cur = a
                for k in cl:
                    sec, text = subs[k]
                    end = (near_cut(cur + durs[k], cur + durs[k] - Fraction(1, 2), cur + durs[k] + Fraction(25, 10))
                           or near_cut(cur + durs[k], cur + durs[k] - Fraction(15, 10), cur + durs[k] + 4)
                           or snapf(cur + durs[k]))
                    attach(title('subtitle', 'one', [text], LANE['subtitle'], end - cur), cur)
                    stats['subtitle'] += 1
                    last_sub_end = end
                    # セクションラベル: 同じ語が続く間は 1 本（最長 30 秒）。字幕の間（インサートは続く）も通す
                    word = label_for(text, sec)
                    if block and block[0] == word and end - block[1] <= 30 and cur - block[3] <= 3:
                        block[3] = end
                    else:
                        if block:
                            block[2].set('duration', S(block[3] - block[1]))
                        lbl = title('section_label', 'any', [word], LANE['section'], end - cur)
                        attach(lbl, cur)
                        stats['section'] += 1
                        block = [word, cur, lbl, end]
                    if k != cl[-1]:
                        nxt = near_cut(end + 1, end + Fraction(1, 2), end + 3) or near_cut(end + 1, end, end + 5) or end
                        block[3] = nxt if block[0] == word else block[3]
                        cur = nxt
                b = last_sub_end
                lay(a, b, subs[cl[0]][0])
                fill_talk(prev_end, a)
                prev_end = b
                t = b + outer
            if block:
                block[2].set('duration', S(block[3] - block[1]))
            # 価格表示（最後の字幕の後）の後〜区間の終わりのトーク
            fill_talk(prev_end + 6, w1)
        # 3) 字幕のない商品（台本なし）: トークの所々に字幕なしのインサート
        elif ec:
            span = w1 - w0
            nb = max(1, int(span // 32))
            for b_ in range(nb):
                g0 = w0 + span * b_ / nb
                fill_talk(g0, g0 + span / nb)
        # 4) 価格ありの中央商品名（区間の最後）
        if pr.get('price') and ec:
            # 価格は台本どおり素材の説明の直後（最後の字幕の 1 秒後）。A19 も価格に触れた時点で出している
            tp = near_cut(t1 - 7, t1 - 9, t1 - 5) or snapf(t1 - Fraction(7))
            if subs and last_sub_end is not None and last_sub_end + 1 < tp:
                # インサートのかたまりの終わり（編集点）からそのまま続けて出す（間にトークが一瞬見えないように）
                tp = last_sub_end
            pe = near_cut(tp + 3, tp + Fraction(25, 10), tp + 4) or near_cut(tp + 3, tp + 2, tp + 5) or snapf(tp + 3)
            pd = pe - tp
            # 全面をぼかした写真で覆い（左上の商品名ラベルを隠す。A18 の型）、中央に写真
            attach(still((photos or ec)[-1], pd, LANE['photo_bg'], '0 0', '2.2 2.2', [blur_f]), tp)
            attach(still(ec[0], pd, LANE['photo_fg'], '0 0', '1.05 1.05'), tp)
            attach(title('product_center', 'price', [pr['name'], f"Color : {pr['color']} | Size : {pr['sizes']}", pr['price'], ' - tax in'],
                         LANE['center'], pd), tp)
            stats['price'] += 1

    # ---- OP: LOOK 写真の 2 枚並べと LOOK 動画 ----
    op = plan.get('op_look')
    if op:
        looks = folder(op['photos'])
        vids = [a for a in folder(op['videos']) if float(T(a.get('duration'))) >= 4]
        # 頭・切り替わり・終わりはメインの編集点に揃える
        t = near_cut(op['t0'], op['t0'] - 1, op['t0'] + 1) or snapf(op['t0'])
        t_end = near_cut(op['t1'], op['t1'] - 2, op['t1'] + 1) or snapf(op['t1'])
        k, vi = 0, 0
        step = max(1, len(looks) // 24)
        while t < t_end - 2:
            d0 = Fraction(28, 10) if k % 2 == 0 else Fraction(24, 10)
            e = near_cut(t + d0, t + d0 - Fraction(8, 10), t + d0 + Fraction(8, 10)) or near_cut(t + d0, t + Fraction(16, 10), t + d0 + 2)
            d = (e - t) if e is not None else snapf(t + d0) - t
            if t_end - (t + d) < 2:
                d = t_end - t  # 最後のカットは OP の終わりまで伸ばす（短い切れ端を作らない）
            if k % 2 == 0 and looks:
                a = looks[(k // 2 * step) % len(looks)]
                b = looks[(k // 2 * step + 1) % len(looks)]
                attach(still(a, d, LANE['photo_bg'], '-44.4444 0', 'half'), t)
                attach(still(b, d, LANE['photo_fg'], '44.4444 0', 'half'), t)
            elif vids:
                attach(clip(vids[vi % len(vids)], d, LANE['photo_bg'], start_in=0 if T(vids[vi % len(vids)].get('duration')) < d + 1 else 1,
                            filters=[tilt_f, grade_f]), t)
                punch(t, d, LANE['photo_fg'])
                vi += 1
            t += d
            k += 1
            stats['op'] += 1

    # ---- OP: ティーザー（名前カードの後、4.9 秒）。LOOK 写真＋フィルムルックの調整レイヤー 2 枚＋中央のコレクション名 ----
    look_a = donor.find_in_project(proj19, lambda e: e.tag == 'title' and any(norm(f.get('name')) == 'プリズム' for f in e.findall('filter-video')))
    # プロジェクタ＋ビネット＋ノイズの調整レイヤーはアイキャッチの複合クリップの中にある
    look_b = next((e for e in donor.root.iter('title') if any(norm(f.get('name')) == 'プロジェクタ' for f in e.findall('filter-video'))), None)
    if op and look_a is not None and look_b is not None:
        tt = near_cut(Fraction(47, 10), Fraction(4), Fraction(54, 10)) or snapf(Fraction(47, 10))  # 名前カードの終わり（assemble_lineup と同じ規則）
        dt = end_on_cut(tt, Fraction(49, 10), Fraction(8, 10))
        looks = folder(op['photos'])
        if looks:
            attach(still(looks[len(looks) // 3], dt, LANE['photo_bg'], '0 27.963', '2.7 2.7'), tt)
        for ln, src_el in ((LANE['photo_fg'], look_a), (LANE['center'], look_b)):
            x = donor.element(src_el)
            for ch in list(x):
                if ch.tag in ('marker', 'chapter-marker', 'keyword') or ch.get('lane') is not None:
                    x.remove(ch)
            x.set('lane', str(ln))
            x.set('duration', S(dt))
            attach(x, tt)
        attach(title('collection_center', 'any', ['shiun ', plan['collection'].replace('shiun ', '')], LANE['section'], dt), tt)
        stats['op'] += 1

    # ---- ED: 一覧 ----
    ed = next((s for s in sections if s['chapter'] == 'ED'), None)
    cut = [p for p in plan['products'] if p.get('cutout') and p['cutout'] in assets]
    if ed and cut:
        te = near_cut(ed['t0'] + 1, ed['t0'] + Fraction(1, 2), ed['t0'] + 3) or near_cut(ed['t0'] + 1, ed['t0'], ed['t0'] + 5) or snapf(ed['t0'] + 1)
        looks = folder(op['photos']) if op else []
        # 一覧のページの長さ（3.4 秒・3.0 秒前後で、終わりを編集点に）を先に決める
        page_d, tq = [], te
        for d0 in (Fraction(34, 10), Fraction(30, 10)):
            page_d.append(end_on_cut(tq, d0))
            tq += page_d[-1]
        # 色名が長いと 4 列では商品名が横で重なるので、5 商品以上は 3 列（3＋残り）にする
        per = 3 if len(cut) >= 5 or any(len(f"Color : {p['color']} | Size : {p['sizes']}") > 34 for p in cut) else 4
        pages = [cut[:per], cut[per:]]
        dl = sum(page_d[:2 if pages[1] else 1])
        if looks:
            attach(still(looks[len(looks) // 2], dl, 2, '0 23.3333', '2.68 2.68', [blur_f]), te)
        attach(title('collection_label_center', 'any', [plan['collection'], plan['release_line']], LANE['center'], dl), te)
        xs = {4: [62.5093, 23.0556, -16.3889, -60.1944], 3: [44.4444, 0, -44.4444], 2: [27.7778, -27.7778], 1: [0]}
        tp = te
        for page in pages:
            if not page:
                continue
            d = page_d[0] if page is pages[0] else page_d[1]
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
        # 一覧の後: LOOK 写真＋中央の発売日（A18 の型、3.9 秒）→ 締めのトーク中は左上にコレクション名（A19 の型）
        t_rel = tp
        if looks and plan.get('release_date'):
            dr = end_on_cut(t_rel, Fraction(39, 10))
            attach(still(looks[2 * len(looks) // 3 + 1], dr, LANE['photo_bg'], '0 0', '2.2 2.2', [blur_f]), t_rel)
            attach(still(looks[2 * len(looks) // 3], dr, LANE['photo_fg'], '0 0', '1.05 1.05'), t_rel)
            attach(title('release_date_center', 'any', [plan['release_date']], LANE['center'], dr), t_rel)
            t_rel += dr
        # エンディング動画（スパインの最後の挿入）の頭まで
        ending = [e for e in spine if e.tag != 'mc-clip' and e.get('offset') is not None and 'エンディング' in norm(e.get('name'))]
        ed_end = T(ending[-1].get('offset')) if ending else snapf(total - Fraction(85, 10))
        if ed_end - t_rel > 3:
            attach(title('collection_label', 'any', [plan['collection'], plan['release_line']], 2, ed_end - t_rel), t_rel)
        for n, line in enumerate(reversed(plan.get('closing_lines', []))):
            dur = Fraction(max(4, min(10, len(line) // 4)))
            ts = near_cut(ed_end - dur - 1 - n * (dur + 1), ed_end - dur - 3 - n * (dur + 1), ed_end - dur - n * (dur + 1)) or snapf(ed_end - dur - 1 - n * (dur + 1))
            attach(title('subtitle', 'one', [line], LANE['subtitle'], end_on_cut(ts, dur, Fraction(1)), ), ts)
        if se_src is not None:
            x = donor.element(se_src)
            x.set('lane', '-1')
            attach(x, te)

    # ---- 商品名ラベルをつなぐ ----
    # assemble_lineup はカットごとにラベルを付けるので、A19 と同じく「トークが続く間は 1 本、B-roll の頭で区切る」にまとめる
    def abs_time(host, el):
        return T(host.get('offset')) + T(el.get('offset')) - T(host.get('start'))

    labels, cuts = [], set()
    for off, du, e in hosts:
        for ch in list(e):
            if ch.tag == 'title' and ch.get('lane') == '2' and '| Size :' in ''.join(ch.itertext()):
                labels.append((abs_time(e, ch), T(ch.get('duration')), e, ch))
            elif ch.tag in ('video', 'asset-clip', 'clip', 'ref-clip') and int(ch.get('lane') or 0) >= 3:
                cuts.add(abs_time(e, ch))
    labels.sort(key=lambda x: x[0])
    groups = []
    for t0, du, e, ch in labels:
        key = ''.join(ch.itertext())
        if groups and groups[-1]['key'] == key and abs(groups[-1]['t1'] - t0) < Fraction(1, 100):
            groups[-1]['t1'] = t0 + du
        else:
            groups.append({'key': key, 't0': t0, 't1': t0 + du, 'el': copy.deepcopy(ch)})
        e.remove(ch)
    n_before = len(labels)
    n_copy = 0
    for g in groups:
        pts = [g['t0']] + sorted(c for c in cuts if g['t0'] + 2 < c < g['t1'] - 2) + [g['t1']]
        for a, b in zip(pts, pts[1:]):
            x = copy.deepcopy(g['el'])
            x.set('duration', S(Fraction(b - a).limit_denominator(60000)))
            n_copy += 1
            k = n_copy  # 書式 ID を複製ごとに一意にする
            for tsd in x.findall('text-style-def'):
                tsd.set('id', f"{tsd.get('id')}_l{k}")
            for ts in x.iter('text-style'):
                if ts.get('ref'):
                    ts.set('ref', f"{ts.get('ref')}_l{k}")
            attach(x, a)
    stats['labels'] = f'{n_before}→{sum(1 for _ in project.iter("title") if _.get("lane") == "2" and "| Size :" in "".join(_.itertext()))}'

    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))
    print('placed', stats, '->', out)


if __name__ == '__main__':
    main()
