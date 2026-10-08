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

    # カウントダウン: A19 のもの（仮）を、A24 の素材フォルダのカウントダウンに差し替える（切らずにまるごと使う）
    if isinstance(plan.get('countdown'), dict) and plan['countdown'].get('path'):
        like = next(a for a in assets.values() if a.find('media-rep') is not None)
        nsrc = unicodedata.normalize('NFC', urllib.parse.unquote(like.find('media-rep').get('src')))
        prefix = nsrc[:nsrc.index(plan['asset_root']) + len(plan['asset_root'])]
        for a in resources:
            mr = a.find('media-rep') if a.tag == 'asset' else None
            if mr is not None and a.get('name') == '7' and 'カウントダウン' in unicodedata.normalize('NFC', urllib.parse.unquote(mr.get('src'))):
                mr.set('src', urllib.parse.quote(unicodedata.normalize('NFD', prefix + plan['countdown']['path']), safe='/:'))
                for k in ('sig',):
                    mr.attrib.pop(k, None)
                for b in mr.findall('bookmark'):
                    mr.remove(b)
                a.attrib.pop('uid', None)
                if plan['countdown'].get('duration'):
                    a.set('duration', plan['countdown']['duration'])

    # 粗編集の XML に未登録の静止画（後から共有された素材）を、同じ素材フォルダのパスで登録する
    if plan.get('register_stills'):
        like = next(a for a in assets.values() if a.find('media-rep') is not None)
        src0 = urllib.parse.unquote(like.find('media-rep').get('src'))
        nsrc = unicodedata.normalize('NFC', src0)
        prefix = nsrc[:nsrc.index(plan['asset_root']) + len(plan['asset_root'])]
        ids = {e.get('id') for e in resources}
        n_new = 0
        for st_ in plan['register_stills']:
            r_ = unicodedata.normalize('NFC', st_['path'])
            if r_ in assets:
                continue
            fk = f"{st_['w']}x{st_['h']}"
            fe = next((e for e in resources if e.tag == 'format' and e.get('name') == 'FFVideoFormatRateUndefined'
                       and e.get('width') == str(st_['w']) and e.get('height') == str(st_['h'])), None)
            if fe is None:
                fid = f'rs_f{fk}'
                fe = ET.Element('format', id=fid, name='FFVideoFormatRateUndefined', width=str(st_['w']), height=str(st_['h']), colorSpace='1-13-1')
                resources.insert(0, fe)
                ids.add(fid)
            k_ = 1
            while f'rs_{k_}' in ids:
                k_ += 1
            aid = f'rs_{k_}'
            ids.add(aid)
            name_ = r_.rsplit('/', 1)[1].rsplit('.', 1)[0]
            a_ = ET.SubElement(resources, 'asset', id=aid, name=name_, start='0s', duration='0s', hasVideo='1', format=fe.get('id'), videoSources='1')
            url = urllib.parse.quote(unicodedata.normalize('NFD', prefix + r_), safe='/:')
            ET.SubElement(a_, 'media-rep', kind='original-media', src=url)
            assets[r_] = a_
            n_new += 1
        print('未登録の静止画を登録:', n_new, file=sys.stderr)

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
    # 写真（SNS 用高画質など）に直接当てているカラー調整（A19 の写真の 56% に付いている）
    photo_grade_f = next((f for v in donor.root.iter('video') if v.get('lane') for f in v.findall('filter-video')
                          if norm(f.get('name')) == 'カラー調整'), grade_f)
    ph_n = [0]
    # 写真の扱い（A19: 動かさず＋カラー調整 / そのまま / 縦にゆっくりパン / 拡大 の割合に合わせて順に回す）
    PHOTO_STYLE = ['grade', 'plain', 'grade', 'pan', 'grade', 'plain', 'zoom', 'grade', 'plain', 'grade']

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
            # 「¥ 14,300」と「 - tax in」は同じ行（A19: 金額は大きい文字、- tax in は小さい文字で並べる）
            nxt = lines[n + 1] if n < len(lines) - 1 else None
            r.text = line + ('\n' if nxt is not None and not nxt.startswith(' - ') else '')
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

    # ---- インサート台帳（素材ごとの商品・寄り引き・部位）と動きの判定（使える区間）----
    LEDGER = json.load(open(os.path.join(base, plan['insert_ledger']), encoding='utf-8')) if plan.get('insert_ledger') else {'clips': {}, 'photos': {}}
    MOTION = json.load(open(os.path.join(base, plan['insert_motion']), encoding='utf-8'))['clips'] if plan.get('insert_motion') else {}
    clip_asset = {}
    for k_, a_ in assets.items():
        nm_ = k_.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        if nm_ in LEDGER['clips']:
            clip_asset[nm_] = a_
    clip_used = {}   # 素材名 → 使った区間（同じ素材でも違う場面なら使い回してよい）
    clip_count = {}
    mix = {'video': 0, 'photo': 0}
    # 字幕の言葉 → 映っていてほしい部位
    KW = [(r'襟|衿|首|顔周り|顔まわり', {'collar', 'neck', 'neckline'}), (r'Vネック|ネック', {'neckline', 'neck'}),
          (r'ボタン|前立て', {'button', 'front'}), (r'袖口|袖', {'cuff', 'sleeve'}), (r'肩|サドルショルダー', {'shoulder', 'saddle_shoulder'}),
          (r'裾|着丈|丈|丸いカット|カッティング', {'hem', 'length'}), (r'身幅|脇|シルエット|ストン|ストレート|フレア|脚|バランス', {'silhouette', 'body_width', 'leg', 'straight'}),
          (r'ポケット', {'pocket'}), (r'後ろ|背', {'back'}), (r'ウエスト|タック|センタープレス', {'waist', 'front', 'no_tuck', 'crease'}),
          (r'素材|生地|糸|編み|天竺|鹿の子|合皮|レザー|牛革|ポリ|リネン|ウール|コットン|杢|質感|ドレープ|柔らか|チクチク|光沢', {'texture', 'material', 'drape', 'shine'}),
          (r'ソール|靴裏|厚底|えぐ|コバ', {'sole', 'outsole', 'bottom', 'sole_edge'}), (r'ヒール', {'heel'}), (r'サドル|ステッチ', {'saddle', 'stitch'}),
          (r'履き口|内側|ゴム', {'opening', 'inside', 'waist', 'back'}), (r'バックル|プレート|ゴールド', {'buckle', 'plate'}),
          (r'メッシュ|編み込|イントレチャート|表面も裏面', {'mesh', 'texture'}), (r'垂ら|長め|留め', {'belt_end', 'length'}),
          (r'着こなし|コーデ|スタイリング|合わせ', {'styling'})]

    def want_parts(text):
        import re as _re2
        out = set()
        for pat, parts in KW:
            if text and _re2.search(pat, text):
                out |= parts
        return out

    def find_usable(name, d):
        """素材 name の使える区間から、長さ d を、使った区間と NG の近く（余裕 0.75 秒）を避けて探す。"""
        m = MOTION.get(name)
        if not m:
            return None
        bad = [(a - Fraction(3, 4), b + Fraction(3, 4)) for v in m['ng'].values() for a, b in v]
        bad += [(Fraction(str(a)) - 1, Fraction(str(b)) + 1) for a, b in LEDGER['clips'].get(name, {}).get('manual_ng', [])]
        bad += [(a - 1, b + 1) for a, b in clip_used.get(name, [])]
        for a, b in m['usable']:
            st_ = Fraction(str(a)) + Fraction(1, 2)
            while st_ + d <= Fraction(str(b)) - Fraction(1, 2):
                hit = [y for x, y in bad if x < st_ + d and st_ < y]
                if not hit:
                    return st_
                nxt_ = Fraction(max(hit))
                if nxt_ <= st_:
                    break
                st_ = nxt_
        return None

    # ---- 発話に合わせた字幕（plan の subtitles がある場合）----
    # 字幕ファイルの seg（文字起こしの行番号）から、最初の単語の頭〜最後の単語の終わりを時刻にする
    SUBS, SPEC = [], None
    price_after = {}  # 商品名 → (価格の中央表示の終わり, 区間の終わり)。この間の左上ラベルは価格あり（P13）
    if plan.get('subtitles'):
        SPEC = json.load(open(os.path.join(base, plan['subtitles']), encoding='utf-8'))
        tr = json.load(open(os.path.join(base, plan['transcript']), encoding='utf-8'))

        def seg_t(k, end=False):
            x = tr[k - 1]
            if x.get('words'):
                return Fraction(str(x['words'][-1]['end'] if end else x['words'][0]['start']))
            return Fraction(str(x['end'] if end else x['start']))
        for x in SPEC['subs']:
            st, en = seg_t(x['seg'][0]), seg_t(x['seg'][1], True)
            # 頭は 0.25 秒以内に編集点があればそこへ、終わりは言い終わりの少し後の編集点へ（なければフレームに揃える）
            a = near_cut(st, st - Fraction(1, 4), st + Fraction(1, 4)) or snapf(st)
            b = near_cut(en + Fraction(1, 5), en, en + Fraction(6, 10)) or snapf(en + Fraction(15, 100))
            SUBS.append({'t0': a, 't1': max(b, a + 1), 'text': x['text'], 'label': x.get('label'), 'face': x.get('face', False) or x.get('style') == 'emphasis',
                         'style': x.get('style')})
        SUBS.sort(key=lambda x: x['t0'])
        for k, x in enumerate(SUBS):
            # 読む時間（1 秒 6 文字以内）が足りなければ、言い終わりから最大 1.5 秒まで残す
            need = Fraction(len(x['text'].replace('\n', '')), 6)
            if x['t1'] - x['t0'] < need:
                want = min(x['t0'] + need, x['t1'] + Fraction(3, 2))
                x['t1'] = near_cut(want, want, want + Fraction(1, 2)) or snapf(want)
            if k + 1 < len(SUBS) and x['t1'] > SUBS[k + 1]['t0']:
                x['t1'] = SUBS[k + 1]['t0']
        seg_time = {k: seg_t(int(v)) for k, v in SPEC.get('price_at', {}).items()}

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
        # 紹介インは assemble_lineup が置いた中央商品名（価格なし）と同じ時刻に（A19: 区間の頭 1.4〜2.3 秒はトーク）
        i0, di = t0, end_on_cut(t0, Fraction(str(plan.get('label_delay', 4.6))), Fraction(8, 10))
        for off_, du_, e_ in hosts:
            if not (t0 - 1 <= off_ < t1):
                continue
            for ch in e_:
                if ch.tag == 'title' and ch.get('lane') == '5' and pr['name'] in ''.join(ch.itertext()) and '¥' not in ''.join(ch.itertext()):
                    i0 = off_ + T(ch.get('offset')) - T(e_.get('start'))
                    di = T(ch.get('duration'))
        if ec and photos:
            attach(still(ec[0], di, LANE['photo_fg'], '-44.4444 0', 'half'), i0)
            attach(still(photos[min(5, len(photos) - 1)], di, LANE['photo_bg'], '44.4444 0', 'half', [blur_f]), i0)
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

        ch_key = pr['chapter']
        ec_cands = [n_ for n_, c_ in LEDGER['clips'].items() if (c_['product'] == ch_key or ch_key in c_.get('also', [])) and n_ in clip_asset]
        ph_parts = {}
        for ph_ in photos:
            key_ = f"{ch_key}/{unicodedata.normalize('NFC', ph_.get('name') or '')}"
            ph_parts[ph_.get('id')] = set(LEDGER.get('photos', {}).get(key_, {}).get('parts', []))

        def pick_insert(d, text, label):
            """話の内容（字幕の言葉）と台帳の部位・寄り引きで、EC 動画の使える区間か写真を選ぶ。"""
            want = want_parts(text)
            view_pref = {'Silhouette': {'full', 'mid'}, 'Detail': {'close'}, 'Material': {'close'}, 'Design': {'mid', 'close'}, None: {'full', 'mid'}}.get(label, {'mid'})
            best = None
            for n_ in ec_cands:
                c_ = LEDGER['clips'][n_]
                st_ = find_usable(n_, d)
                if st_ is None:
                    continue
                sc_ = 3 * len(want & set(c_['parts'])) + (2 if c_['view'] in view_pref else 0) - 1.5 * clip_count.get(n_, 0)
                if c_['product'] != ch_key:
                    sc_ -= 1
                tot = mix['video'] + mix['photo']
                if tot and mix['video'] / tot < 0.45:
                    sc_ += 1
                if best is None or sc_ > best[0]:
                    best = (sc_, 'video', n_, st_)
            for ph_ in photos:
                parts_ = ph_parts.get(ph_.get('id'), set())
                sc_ = 3 * len(want & parts_) + (1 if not want and label in ('Design', 'Silhouette', None) else 0) - 1.5 * used.get(ph_.get('id'), 0) - 0.5
                if best is None or sc_ > best[0]:
                    best = (sc_, 'photo', ph_, None)
            return best

        def lay(a, b, sec, forced=(), cues=()):
            """インサートのかたまり [a, b] を敷く。forced（字幕の頭・終わり）では必ず切り替える（A19・A23 は 100%）。
            cues（字幕の時刻・文・ラベル）から、そのカットで話している部位に合う素材を選ぶ。"""
            pts = [a] + sorted({f for f in forced if a < f < b}) + [b]
            segs = [pc for x, y in zip(pts, pts[1:]) for pc in pieces(x, y)]
            for pa, pb in segs:
                d = pb - pa
                mid_ = (pa + pb) / 2
                cue = next((c_ for c_ in cues if c_[0] <= mid_ < c_[1]), None)
                text_, label_ = (cue[2], cue[3]) if cue else ('', sec)
                pick = pick_insert(d, text_, label_)
                if pick is not None and pick[1] == 'video':
                    _, _, n_, st_in = pick
                    clip_used.setdefault(n_, []).append((st_in, st_in + d))
                    clip_count[n_] = clip_count.get(n_, 0) + 1
                    mix['video'] += 1
                    # EC 動画: カラー調整、置き撮り・手持ちの一部は基本3D で少し傾ける（A19 は 31%）。上に寄りの調整レイヤー
                    fx_ = [grade_f] + ([tilt_f] if mix['video'] % 3 == 0 else [])
                    attach(clip(clip_asset[n_], d, LANE['photo_bg'], start_in=st_in, filters=fx_), pa)
                    punch(pa, d, LANE['photo_fg'])
                else:
                    mix['photo'] += 1
                    ph = pick[2] if pick is not None else photos[0]
                    used[ph.get('id')] = used.get(ph.get('id'), 0) + 1
                    sc = '2.68 2.68' if sec in ('Design', 'Silhouette', None) else '3.4 3.4'
                    style = PHOTO_STYLE[ph_n[0] % len(PHOTO_STYLE)]
                    ph_n[0] += 1
                    y = (pi[0] % 3 - 1) * 8
                    fx = {'grade': [photo_grade_f], 'plain': [], 'pan': [photo_grade_f], 'zoom': [photo_grade_f, zoom_f]}[style]
                    el = still(ph, d, LANE['photo_bg'], f'0 {y}', sc, fx)
                    if style == 'pan':
                        # 位置にキーフレームを打って縦にゆっくり動かす（A19: 毎秒 4〜10 単位）
                        tr = el.find('adjust-transform')
                        tr.attrib.pop('position', None)
                        prm = ET.SubElement(tr, 'param', name='position')
                        ka = ET.SubElement(prm, 'keyframeAnimation')
                        span = min(Fraction(30), Fraction(6) * d)
                        st_ = T(el.get('start'))
                        ET.SubElement(ka, 'keyframe', time=S(st_), value=f'0 {float(span / 2):.4f}', curve='linear')
                        ET.SubElement(ka, 'keyframe', time=S(st_ + d), value=f'0 {float(-span / 2):.4f}', curve='linear')
                    attach(el, pa)
                    pi[0] += 1
                stats['broll'] += 1

        def fill_talk(g0, g1):
            """トークだけが続く所に、字幕なしのインサート（約 14 秒）を「トーク約 15 秒 ↔ インサート」の間隔で入れる。
            前後は 8 秒以上トークを見せる（A19 はトークの間が中央値 15.5 秒、インサートのかたまりが中央値 16.4 秒）。"""
            if g1 - g0 < 20 or not ec:
                return
            n = max(1, round((g1 - g0 - 15) / 29))
            while n > 1 and (g1 - g0 - 15 * (n + 1)) / n < 8:
                n -= 1
            L = min(Fraction(16), (g1 - g0 - 15 * (n + 1)) / n) if n > 1 else min(Fraction(16), (g1 - g0) - 10)
            talk = (g1 - g0 - n * L) / (n + 1)
            for k in range(n):
                s_ = g0 + talk * (k + 1) + L * k
                a = near_cut(s_, s_ - 2, s_ + 2) or near_cut(s_, s_ - 4, s_ + 4) or snapf(s_)
                b = near_cut(a + L, a + L - 2, a + L + 2) or near_cut(a + L, a + L - 4, min(g1, a + L + 4)) or snapf(a + L)
                if b - a >= 6:
                    lay(a, b, None)

        if SUBS:
            # ---- 発話どおりの字幕と、説明（ラベル付き）の字幕の下だけのインサート ----
            ins_end = i0 + di
            mine = [x for x in SUBS if t0 <= x['t0'] < t1]
            tp = None
            if pr.get('price') and ec and pr['chapter'] in seg_time:
                ps = seg_time[pr['chapter']]
                tp = near_cut(ps, ps - Fraction(1, 2), ps + 1) or near_cut(ps, ps - 2, ps + 2) or snapf(ps)
            # 字幕（紹介インと価格の中央表示に重なる所は、表示が終わってから出す）
            centers = [(t0, ins_end)] + ([(tp, tp + 3)] if tp is not None else [])
            for x in mine:
                for ca, cb in centers:
                    if x['t0'] < cb and ca < x['t1']:
                        x['t0'] = max(x['t0'], cb) if x['t0'] >= ca else x['t0']
                        x['t1'] = min(x['t1'], ca) if x['t0'] < ca else x['t1']
            mine = [x for x in mine if x['t1'] - x['t0'] >= Fraction(3, 2)]
            # 説明の字幕（インサートが付く）は頭と終わりを編集点に寄せ、インサートの切り替わりと一致させる（A19・A23 は 100%）
            for k, x in enumerate(mine):
                if x['face']:
                    continue
                ca = [c for c in CUTS if x['t0'] - Fraction(12, 10) <= c <= x['t0'] + Fraction(3, 10)]
                if ca:
                    x['t0'] = min(ca, key=lambda c: (c > x['t0'], abs(c - x['t0'])))
                cb = [c for c in CUTS if x['t1'] - Fraction(5, 10) <= c <= x['t1'] + Fraction(15, 10)]
                if cb:
                    x['t1'] = min(cb, key=lambda c: (c < x['t1'], abs(c - x['t1'])))
            for k in range(len(mine) - 1):
                if mine[k]['t1'] > mine[k + 1]['t0']:
                    mine[k]['t1'] = mine[k + 1]['t0']
            mine = [x for x in mine if x['t1'] - x['t0'] >= 1]
            for x in mine:
                if x['style'] == 'emphasis':
                    # 中央の強調（P08）: 決め台詞・ニュース。読む時間を確保（1 秒 6 文字）
                    d_ = max(x['t1'] - x['t0'], Fraction(len(x['text'].replace('\n', '')), 6))
                    attach(title('emphasis', 'any', [x['text']], LANE['center'], d_), x['t0'])
                    stats.setdefault('emphasis', 0)
                    stats['emphasis'] += 1
                    continue
                attach(title('subtitle', 'one', [x['text']], LANE['subtitle'], x['t1'] - x['t0']), x['t0'])
                stats['subtitle'] += 1
            # インサートのかたまり: ラベル付きの字幕が 6 秒以内で続く所
            blocks, cur = [], []
            for x in [x for x in mine if not x['face']]:
                if cur and x['t0'] - cur[-1]['t1'] > 6:
                    blocks.append(cur)
                    cur = []
                cur.append(x)
            if cur:
                blocks.append(cur)
            busy = [(t0, ins_end)] + [(x['t0'], x['t1']) for x in mine if x['face']]  # 気持ちを伝える発言は顔を見せる
            if tp is not None:
                busy.append((tp, tp + 4))
            laid = []
            for bl in blocks:
                a = bl[0]['t0']
                ca = [c for c in CUTS if a - 3 <= c <= a]
                a = max(ca) if ca else (near_cut(a, a - 5, a + 1) or a)  # 字幕の直前の編集点から入る
                a = max(a, ins_end)
                b = bl[-1]['t1']
                cb = [c for c in CUTS if b <= c <= b + 3]
                b = min(cb) if cb else (near_cut(b, b - 1, b + 5) or b)  # 言い終わりの直後の編集点で抜ける
                for bs, be in busy:  # 価格・重要な発言・紹介インに重ねない（その頭の編集点で抜ける）
                    if a < bs < b:
                        b = min(b, bs)
                if b - a < 2:
                    continue
                lay(a, b, bl[0]['label'] if bl[0]['label'] in ('Design', 'Silhouette', 'Material', 'Detail') else 'Detail',
                    forced=[x['t0'] for x in bl] + [x['t1'] for x in bl],
                    cues=[(x['t0'], x['t1'], x['text'], x['label']) for x in bl])
                laid.append((a, b))
                # セクションラベル: 同じ語が続く間は 1 本（最長 30 秒）、かたまりの中だけ
                k = 0
                while k < len(bl):
                    j = k
                    while j + 1 < len(bl) and bl[j + 1]['label'] == bl[k]['label'] and bl[j + 1]['t1'] - bl[k]['t0'] <= 30:
                        j += 1
                    la = max(a, bl[k]['t0']) if k else a
                    lb = min(b, bl[j + 1]['t0'] if j + 1 < len(bl) else b)
                    if lb - la >= 1 and bl[k]['label']:
                        attach(title('section_label', 'any', [bl[k]['label']], LANE['section'], lb - la), la)
                        stats['section'] += 1
                    k = j + 1
                last_sub_end = b
            # トークだけが長く続く所（重要な発言・価格・紹介インを避ける）に字幕なしのインサート
            occ = sorted(laid + busy)
            g0 = ins_end + 6
            for a_, b_ in occ:
                if a_ > g0:
                    fill_talk(g0, min(a_, w1 + 9) - 2)
                g0 = max(g0, b_ + 2)
            if t1 - 4 > g0:
                fill_talk(g0, t1 - 4)
            # 価格: 話した瞬間に出す（全面をぼかした写真＋中央に写真＋価格ありの中央商品名）
            if tp is not None:
                pe = (near_cut(tp + 3, tp + Fraction(25, 10), tp + 4) or near_cut(tp + 3, tp + 2, tp + 6)
                      or min([c for c in CUTS if tp + 3 <= c <= tp + 10], default=None) or snapf(tp + 3))
                pd = pe - tp
                attach(still((photos or ec)[-1], pd, LANE['photo_bg'], '0 0', '2.2 2.2', [blur_f]), tp)
                attach(still(ec[0], pd, LANE['photo_fg'], '0 0', '1.05 1.05'), tp)
                attach(title('product_center', 'price', [pr['name'], f"Color : {pr['color']} | Size : {pr['sizes']}", pr['price'], ' - tax in'],
                             LANE['center'], pd), tp)
                stats['price'] += 1
                price_after[pr['name']] = (tp + pd, t1, pr)
            continue
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

    # ---- 商品区間の外（OP・ED）の字幕 ----
    prod_ranges = [(s_['t0'], s_['t1']) for s_ in sections if pp.get(s_['chapter'])]
    for x in SUBS:
        if not any(a <= x['t0'] < b for a, b in prod_ranges):
            attach(title('subtitle', 'one', [x['text']], LANE['subtitle'], x['t1'] - x['t0']), x['t0'])
            stats['subtitle'] += 1

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
        # OP の字幕の頭・終わりでは必ず切り替える（A19: 字幕の頭で写真が切り替わる）
        op_forced = sorted({x[k_] for x in SUBS for k_ in ('t0', 't1') if t < x['t0'] < t_end})
        while t < t_end - 2:
            d0 = Fraction(28, 10) if k % 2 == 0 else Fraction(24, 10)
            e = near_cut(t + d0, t + d0 - Fraction(8, 10), t + d0 + Fraction(8, 10)) or near_cut(t + d0, t + Fraction(16, 10), t + d0 + 2)
            d = (e - t) if e is not None else snapf(t + d0) - t
            if t_end - (t + d) < 2:
                d = t_end - t  # 最後のカットは OP の終わりまで伸ばす（短い切れ端を作らない）
            # 字幕の境目が次の 1 カット分（＋1 秒）の中にあれば、そこで切り替える
            fpt = [f for f in op_forced if t + 1 <= f <= t + d + 1]
            if fpt:
                d = fpt[0] - t
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

    # ---- ED: 一覧（A19 の型）----
    # 1 ページ目: 服の切り抜きを 4 列（動画の順に左から。2 色の商品は 2 枚を少しずらして重ねる）。商品名は x 62.5 / 23.1 / -16.4 / -60.2、y -35.6、0.6 倍
    # 2 ページ目: ベルト（SNS 用スナップ）を左、靴（EC 掲載サイズのスナップ）を右に 0.55 倍。商品名は x ±27.8、y -35.5
    ed = next((s_ for s_ in sections if s_['chapter'] == 'ED'), None)
    page1 = [p for p in plan['products'] if p.get('ed', {}).get('page') == 1 and all(c in assets for c in p['ed']['cutouts'])]
    page2 = [p for p in plan['products'] if p.get('ed', {}).get('page') == 2]
    if ed and page1:
        te = near_cut(ed['t0'] + 1, ed['t0'] + Fraction(1, 2), ed['t0'] + 3) or near_cut(ed['t0'] + 1, ed['t0'], ed['t0'] + 5) or snapf(ed['t0'] + 1)
        looks = folder(op['photos']) if op else []
        d1 = end_on_cut(te, Fraction(344, 100))
        d2 = end_on_cut(te + d1, Fraction(297, 100)) if page2 else 0
        dl = d1 + d2
        if looks:
            attach(still(looks[len(looks) // 2], dl, 2, '0 23.3333', '2.68 2.68', [blur_f, photo_grade_f]), te)
        attach(title('collection_label_center', 'any', [plan['collection'], plan['release_line']], LANE['center'], dl), te)

        def ed_name(p, d, lane, x, y):
            nm = title('ed_product_name', 'any', [p['name'], f"Color : {p['color']} | Size : {p['sizes']}", p.get('price', ''), ' - tax in'], lane, d)
            set_transform(nm, f'{x} {y}', '0.6 0.6')
            return nm

        name_x = [-60.1944, -16.3889, 23.0556, 62.5093]
        lane = LANE['ed_name']
        for n, p in enumerate(page1[:4]):
            x = name_x[n]
            cs = p['ed']['cutouts']
            scs = p['ed'].get('scales', [0.72] * len(cs))
            if len(cs) >= 2:
                # 2 色: 右（後ろ・小さめ）と左（前・大きめ）。A19 の L/S TEE と同じずらし方（-3.9 / +5.0、縦 +3.8 / -2.1）
                attach(still(assets[cs[0]], d1, lane, f'{x + 5.0:.4f} 1', f'{scs[0] * 0.94:.3f} {scs[0] * 0.94:.3f}'), te)
                lane += 1
                attach(still(assets[cs[1]], d1, lane, f'{x - 3.9:.4f} 6.8', f'{scs[1] * 1.06:.3f} {scs[1] * 1.06:.3f}'), te)
                lane += 1
            else:
                el = still(assets[cs[0]], d1, lane, f'{x - 2:.4f} 3', f'{scs[0]:.3f} {scs[0]:.3f}')
                if p['ed'].get('rotation'):
                    el.find('adjust-transform').set('rotation', str(p['ed']['rotation']))
                attach(el, te)
                lane += 1
            attach(ed_name(p, d1, lane, x, -35.5556), te)
            lane += 1
        stats['ed'] += 1
        if page2:
            t2 = te + d1
            for p in page2:
                x = -27.7778 if p['ed'].get('side') == 'left' else 27.7778
                if p['ed'].get('snap') and p['ed']['snap'] in assets:
                    img = assets[p['ed']['snap']]
                elif p['ed'].get('snap_donor') and p.get('donor_assets'):
                    img = (donor_assets(p['donor_assets'], p['ed']['snap_donor']) or [None])[0]
                else:
                    img = None
                if img is not None:
                    attach(still(img, d2, lane, f'{x} 0.462963', '0.55 0.55'), t2)
                    lane += 1
                attach(ed_name(p, d2, lane, x, -35.4815), t2)
                lane += 1
            stats['ed'] += 1
        tp = te + dl
        # 一覧の後: LOOK 写真＋中央の発売日（A18 の型、3.9 秒）→ 締めのトーク中は左上にコレクション名（A19 の型）
        t_rel = tp
        if SPEC and SPEC.get('release_at'):
            # 発売日は話した瞬間に中央に出す（一覧の後なら）
            rt = seg_t(int(SPEC['release_at']))
            rt = near_cut(rt, rt - Fraction(1, 2), rt + 1) or snapf(rt)
            t_rel = max(t_rel, rt)
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
        for n, line in enumerate(reversed([] if SUBS else plan.get('closing_lines', []))):
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

    labels, ivs = [], []
    for off, du, e in hosts:
        for ch in list(e):
            # 商品名ラベルと OP の左上のコレクション名（どちらもカットごとに付けている）
            if ch.tag == 'title' and ch.get('lane') == '2' and ('| Size :' in ''.join(ch.itertext()) or plan['collection'] in ''.join(ch.itertext())):
                labels.append((abs_time(e, ch), T(ch.get('duration')), e, ch))
            elif ch.tag in ('video', 'asset-clip', 'clip', 'ref-clip') and int(ch.get('lane') or 0) >= 3:
                ivs.append((abs_time(e, ch), abs_time(e, ch) + T(ch.get('duration'))))
    # 区切るのはインサートのかたまり（続いているインサート）の頭だけ
    cuts, end_ = set(), None
    for a, b in sorted(ivs):
        if end_ is None or a > end_:
            cuts.add(a)
        end_ = b if end_ is None else max(end_, b)
    for a_, b_, _ in price_after.values():
        cuts.add(a_)
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
            # 価格を話した後（価格の中央表示が終わってから区間の終わりまで）は、価格ありのラベル（P13。A19・A23 と同じ）
            for nm, (pa_, pb_, pr_) in price_after.items():
                if nm in g['key'] and pa_ <= a < pb_ and '| Size :' in g['key']:
                    x = title('product_label', 'price', [pr_['name'], f"Color : {pr_['color']} | Size : {pr_['sizes']}",
                                                         pr_['price'], ' - tax in'], 2, b - a)
            x.set('duration', S(Fraction(b - a).limit_denominator(60000)))
            n_copy += 1
            k = n_copy  # 書式 ID を複製ごとに一意にする
            for tsd in x.findall('text-style-def'):
                tsd.set('id', f"{tsd.get('id')}_l{k}")
            for ts in x.iter('text-style'):
                if ts.get('ref'):
                    ts.set('ref', f"{ts.get('ref')}_l{k}")
            attach(x, a)
    stats['labels'] = f'{n_before}→{n_copy}'

    # ---- 流用した部品（アイキャッチなどの複合クリップ）の中の文字を A24 のものに ----
    # A19 のアイキャッチの中には A19 のコレクション名と発売日のテロップが入っている（そのままだと別の回の情報が出る）
    import re as _re
    fixed = 0
    for m in resources:
        if m.tag != 'media' or not (m.get('id') or '').startswith(('a19_', 'd1_', 'd2_')):
            continue
        for ts in m.iter('text-style'):
            t_ = ts.text or ''
            if _re.search(r'shiun\s.*Collection', t_):
                ts.text = _re.sub(r'shiun\s.*Collection', plan['collection'], t_)
                fixed += 1
            elif _re.search(r'\w+ \d+(st|nd|rd|th) \w+\.? \d+(am|pm) - Release', t_):
                ts.text = _re.sub(r'\w+ \d+(st|nd|rd|th) \w+\.? \d+(am|pm) - Release', plan['release_line'], t_)
                fixed += 1
        for t_el in m.iter('title'):
            if _re.search(r'shiun\s.*Collection', t_el.get('name') or ''):
                t_el.set('name', _re.sub(r'shiun\s.*Collection', plan['collection'], t_el.get('name')))
    stats['donor_text_fixed'] = fixed

    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))
    print('placed', stats, '->', out)


if __name__ == '__main__':
    main()
