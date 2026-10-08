"""身長別比較（A19・A23 の型）を本編の間に差し込む。auto_insert.py の後に使う。

    python3 insert_size_compare.py IN.fcpxml PLAN.json OUT.fcpxml [--media-vid DIR]

- 各商品の「…の動画がこちらです。どうぞ」の後（直後のアイキャッチ・ギャップの頭）に、1 人 1 ブロックを差し込む。
  本編のカットは変えない（差し込んだ分だけ後ろがずれる）。
- ブロックは過去データ（plan.size_compare.products[].template）の同じ身長の人のブロックを、枠・テロップごとそのままコピー。
  変えるのは 動画（大きいサイズ＝lane 1、小さいサイズ＝lane 2）、サイズ表の数値、商品名・色・価格だけ。
- 素材がまだない人（pending）は、動画を外して枠とテロップだけ置く。
- 区間をまたぐ BGM（lane が負の音）は、差し込んだ分だけ長くして、音量の変化（ED の +8dB など）も同じだけ後ろへずらす。
--models: 姿勢推定のモデルのフォルダ（あれば、動画ごとに構図を合わせる）
--media-vid: サイズ別動画のプロキシのフォルダ（<素材名>/proxy.mp4, motion.json）。素材の長さと使える区間（NG を避ける）に使う。
"""
import copy
import json
import os
import subprocess
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_lineup import Donor  # noqa: E402

FD = Fraction(1001, 30000)  # サイズ別動画（29.97p）の 1 コマ


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fraction(int(a), int(b))
    return Fraction(s)


def S(f):
    f = Fraction(f)
    return f'{f.numerator}/{f.denominator}s' if f.denominator != 1 else f'{f.numerator}s'


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def txt(el):
    t = el.find('text')
    return ''.join(t.itertext()) if t is not None else ''


def set_lines(title, lines):
    """テロップの各行の文字だけ差し替える（ランの区切りと書式・行間はそのまま。行数が同じこと）。
    行がランをまたぐ時は、その行の最初のかけらに新しい文字を入れ、残りのかけらは空にする。"""
    runs = title.find('text').findall('text-style')
    frags = []  # [ラン番号, 行番号, 文字]
    line = 0
    for ri, r in enumerate(runs):
        ps = (r.text or '').split('\n')
        for j, pc in enumerate(ps):
            frags.append([ri, line, pc])
            if j < len(ps) - 1:
                line += 1
    n_lines = max(f[1] for f in frags) + 1
    # 最後の行が空（末尾の改行）なら数えない
    if all(f[2] == '' for f in frags if f[1] == n_lines - 1):
        n_lines -= 1
    if n_lines != len(lines):
        raise ValueError(f'行数が違う: {n_lines} 行 → {lines}')
    done = set()
    for f in frags:
        if f[1] < len(lines):
            if f[1] in done:
                f[2] = ''
            elif f[2] != '' or not any(g[1] == f[1] and g[2] != '' for g in frags):
                f[2] = lines[f[1]]
                done.add(f[1])
    for ri, r in enumerate(runs):
        r.text = '\n'.join(f[2] for f in frags if f[0] == ri)

WIN = {'2': (639, 1219), '1': (1244, 1824)}  # 2サイズ.png の窓（x の範囲）。lane 2 = 左（小さいサイズ）、lane 1 = 右
WIN_TOP, WIN_BOTTOM, GAP_R = 56, 1024, 1232
_pose = [None]


def body_box(clip_dir, t0, dur, models):
    """in 点から dur 秒の中の 6 コマ（確認用プロキシ 960x540）で、人の切り抜き（セグメンテーション）から
    頭のてっぺん（髪を含む）・つま先・体の中心、姿勢から首から上の範囲を測る（0〜1）。
    頭頂は一番高いコマ、つま先は一番低いコマ（回っても枠に収まる範囲）。"""
    import subprocess
    import tempfile
    import numpy as np
    from PIL import Image
    import mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    if _pose[0] is None:
        _pose[0] = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=mpt.BaseOptions(model_asset_path=os.path.join(models, 'pose_landmarker_full.task')), num_poses=1,
            output_segmentation_masks=True))
    tops, feet, cxs, heads = [], [], [], []
    with tempfile.TemporaryDirectory() as td:
        for q in (0.03, 0.2, 0.4, 0.6, 0.8, 0.97):
            fp = os.path.join(td, 'f.png')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{float(t0) + float(dur) * q:.3f}', '-i', os.path.join(clip_dir, 'proxy.mp4'),
                            '-frames:v', '1', fp])
            if not os.path.exists(fp):
                continue
            im = np.asarray(Image.open(fp).convert('RGB'))
            h, w = im.shape[:2]
            r = _pose[0].detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=im))
            if not r.pose_landmarks or not r.segmentation_masks:
                continue
            m = r.segmentation_masks[0].numpy_view() > 0.5
            if m.ndim == 3:
                m = m[..., 0]
            L = r.pose_landmarks[0]
            # 人の列だけ見る（床の影や別の物を拾わないように、体の中心 ±25% 幅）
            cxp = int((L[11].x + L[12].x + L[23].x + L[24].x) / 4 * w)
            band = m[:, max(0, cxp - w // 4):min(w, cxp + w // 4)]
            rows = np.where(band.sum(axis=1) >= 2)[0]
            if len(rows) < 10:
                continue
            tops.append(rows[0] / h)
            feet.append(rows[-1] / h)
            cols = np.where(band.sum(axis=0) >= 2)[0]
            cxs.append((max(0, cxp - w // 4) + (cols[0] + cols[-1]) / 2) / w)
            nose_y, sh_y = L[0].y, (L[11].y + L[12].y) / 2
            sw = abs(L[11].x - L[12].x)
            hx = L[0].x
            heads.append((rows[0] / h, nose_y + 0.8 * (sh_y - nose_y), hx - max(0.6 * sw, 0.035), hx + max(0.6 * sw, 0.035)))
    if not tops:
        return None
    head = (min(x[0] for x in heads) - 0.01, max(x[1] for x in heads) + 0.005, min(x[2] for x in heads) - 0.01, max(x[3] for x in heads) + 0.01)
    return float(min(tops)), float(max(feet)), float(np.median(cxs)), head


MARGIN = 15  # 頭のてっぺん・つま先と枠の端の余裕（px）


def fit_scale(box, H=1080):
    top, foot = box[0], box[1]
    want = (WIN_BOTTOM - MARGIN) - (WIN_TOP + MARGIN)
    return max(0.9, min(1.8, want / ((foot - top) * H)))


def fit(lane, box, sc=None, W=1920, H=1080):
    """窓の上下の端に頭のてっぺん〜つま先が合う（上下 MARGIN px の余裕）拡大と位置、体の中心が窓の中心（FCP の単位）。
    sc を渡すとその拡大で（同じ人の 2 サイズは同じ拡大にしないと比べられない）。"""
    top, foot, cx = box[0], box[1], box[2]
    x0, x1 = WIN[lane]
    sc = sc or fit_scale(box, H)
    while True:
        y = (H / 2 + (top - 0.5) * H * sc - (WIN_TOP + MARGIN)) / (H / 100)
        x = ((x0 + x1) / 2 - W / 2 - (cx - 0.5) * W * sc) / (H / 100)
        Y0, X0 = H / 2 - y * H / 100, W / 2 + x * H / 100
        ok = Y0 - H * sc / 2 <= WIN_TOP and Y0 + H * sc / 2 >= WIN_BOTTOM and X0 - W * sc / 2 <= x0 and X0 + W * sc / 2 >= x1
        if ok or sc >= 1.8:
            break
        sc += 0.01
    right = 0.0
    if lane == '2':
        right = max(0.0, (X0 + W * sc / 2 - GAP_R) / sc / (H / 100))
    return round(sc, 3), round(x, 4), round(y, 4), round(right, 4)


def main():
    src, plan_path, out = sys.argv[1:4]
    opt = dict(zip(sys.argv[4::2], sys.argv[5::2]))
    vid_dir = opt.get('--media-vid')
    plan = json.load(open(plan_path, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(plan_path))
    sc = plan['size_compare']
    tree = ET.parse(src)
    root = tree.getroot()
    resources = root.find('resources')
    ids = {e.get('id') for e in resources}
    project = [p for p in root.iter('project') if p.get('name') == '本編'][0]
    seq = project.find('sequence')
    spine = seq.find('spine')
    products = {p['chapter']: p for p in plan['products']}

    # ---- 過去データのブロック（同じ身長の人）----
    donors = {}

    def donor_for(path):
        if path not in donors:
            pre = 'a19_' if 'A19' in path else 'a23_'
            d = Donor(os.path.join(base, path), pre, resources)
            for k in ids:
                if k.startswith(pre):
                    d.imported[k[len(pre):]] = True
            donors[path] = d
        return donors[path]

    def find_blocks(d, product):
        found = {}
        for t in d.root.iter('title'):
            if t.get('name') != 'Adjustment Layer':
                continue
            ts = [c for c in t if c.tag == 'title']
            if not any(product in txt(c) for c in ts):
                continue
            h = next((txt(c).strip() for c in ts if txt(c).strip().endswith('kg')), None)
            if h and h not in found:
                found[h] = t
        return found

    # ---- サイズ別動画の素材登録（粗編集の XML に未登録）----
    like = next(a for a in resources if a.tag == 'asset' and a.get('name') == sc['like_asset'])
    like_src = nfc(urllib.parse.unquote(like.find('media-rep').get('src')))
    prefix = like_src[:like_src.index(plan['asset_root']) + len(plan['asset_root'])]
    new_assets = {}

    def probe(name):
        p = os.path.join(vid_dir, name, 'proxy.mp4')
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True)
        return Fraction(round(float(r.stdout.strip()) / float(FD))) * FD

    def asset_for(who, size, name):
        if name in new_assets:
            return new_assets[name]
        a = next((x for x in resources if x.tag == 'asset' and x.get('name') == name), None)
        if a is None:
            k = 1
            while f'sc_{k}' in ids:
                k += 1
            aid = f'sc_{k}'
            ids.add(aid)
            a = copy.deepcopy(like)
            a.set('id', aid)
            a.set('name', name)
            a.attrib.pop('uid', None)
            a.set('start', '0s')
            a.set('duration', S(probe(name)))
            mr = a.find('media-rep')
            for b in mr.findall('bookmark'):
                mr.remove(b)
            mr.attrib.pop('sig', None)
            rel = f"{sc['video_root']}{sc['folders'][who]}/{size}/{name}.MP4"
            mr.set('src', urllib.parse.quote(unicodedata.normalize('NFD', prefix + rel), safe='/:'))
            resources.append(a)
        new_assets[name] = a
        return a

    used = {}  # 素材名 → [(頭, 終わり)]（同じ動画を別の商品で使い回す時は別の場面に）

    def in_point(name, dur, ch=None):
        """使える区間（NG を避ける）の中で、頭から 1 秒以降に dur 秒とれる一番早い位置。使用済みの場面とは重ねない。
        plan の in_points（目視で指定）があればそれを使う。manual_ng（目視の NG）も避ける。"""
        fixed_ = sc.get('in_points', {}).get(f'{ch}/{name}')
        if fixed_ is not None:
            st = Fraction(round(Fraction(str(fixed_)) / FD)) * FD
        else:
            busy_ = used.get(name, []) + [(Fraction(str(a)), Fraction(str(b))) for a, b in sc.get('manual_ng', {}).get(name, [])]
            st = _in_point(name, dur, busy_)
        used.setdefault(name, []).append((st, st + dur))
        return st

    def _in_point(name, dur, busy):
        total = T(new_assets[name].get('duration'))
        cands = [(Fraction(1), total - dur)]
        mp = os.path.join(vid_dir, name, 'motion.json') if vid_dir else None
        if mp and os.path.exists(mp):
            m = json.load(open(mp))
            cands = [(Fraction(str(a)), Fraction(str(b)) - dur) for a, b in m.get('usable', [])]
            soft = [(Fraction(str(a)), Fraction(str(b))) for a, b in m.get('check', {}).get('clothes', [])]
            for a, b in cands:
                a = max(a, Fraction(1))
                moved_ = True
                while moved_:
                    moved_ = False
                    for u0, u1 in list(busy) + soft:
                        if a < u1 and a + dur > u0:
                            a = u1 + Fraction(1, 2)
                            moved_ = True
                if a <= b:
                    return Fraction(round(a / FD)) * FD
        for a, b in cands:
            a = max(a, Fraction(1))
            # 使用済みの場面の後ろへずらす
            moved_ = True
            while moved_:
                moved_ = False
                for u0, u1 in busy:
                    if a < u1 and a + dur > u0:
                        a = u1 + Fraction(1, 2)
                        moved_ = True
            if a <= b:
                return Fraction(round(a / FD)) * FD
        # とれない時は、一番長い使える区間の頭（足りない分は素材の頭寄りに）
        return Fraction(round(max(Fraction(0), min(Fraction(1), total - dur)) / FD)) * FD

    # ---- 差し込み位置: 「…動画…こちら」の発言の後の、最初のアイキャッチ・ギャップの頭 ----
    tr = json.load(open(os.path.join(base, os.path.basename(plan['transcript'])), encoding='utf-8'))
    segs = tr['segments'] if isinstance(tr, dict) else tr
    subs = json.load(open(os.path.join(base, os.path.basename(plan['subtitles'])), encoding='utf-8'))
    items = list(spine)
    starts = []
    cur = Fraction(0)
    for e in items:
        starts.append(cur)
        cur += T(e.get('duration'))

    def find_point(seg_i):
        win = [k for k in range(max(0, seg_i - 3), min(len(segs), seg_i + 2)) if '動画' in segs[k]['text']]
        t0 = Fraction(str(segs[win[-1] if win else seg_i]['start']))
        for e, st in zip(items, starts):
            if st >= t0 - Fraction(1, 2) and e.tag != 'mc-clip' and st - t0 < 8:
                return e, st
        # なければ発言の終わりの後の最初の編集点
        t1 = Fraction(str(segs[seg_i]['end']))
        return next((e, st) for e, st in zip(items, starts) if st >= t1 - Fraction(3, 10))

    framed = []
    blurred = []
    blocks_at = {}  # 差し込む前の要素 → [ブロック]
    n_ts = [0]
    report = []
    for ch, cfg in sc['products'].items():
        pr = products[ch]
        spec = pr['size_spec']
        d = donor_for(cfg['template']['fcpxml'])
        tpl = find_blocks(d, cfg['template']['product'])
        before, at = find_point(int(subs['size_compare_at'][ch]))
        out_blocks = []
        for person in sc['people']:
            b0 = tpl.get(person['height'])
            if b0 is None:
                raise SystemExit(f"型のブロックがない: {cfg['template']['product']} {person['height']}")
            x = d.element(b0)
            dur = T(x.get('duration'))
            tstart = T(x.get('start'))
            for c in list(x):
                if c.tag in ('mc-clip', 'marker', 'chapter-marker') or (c.tag != 'title' and c.get('lane') is None and c.tag not in ('adjust-transform',)):
                    if c.tag in ('mc-clip', 'marker', 'chapter-marker'):
                        x.remove(c)
            # 動画（lane 1 = 大きいサイズ、lane 2 = 小さいサイズ）
            boxes = {}
            for c in [c for c in x if c.tag == 'asset-clip' and c.get('lane') in ('1', '2')]:
                if person.get('pending'):
                    x.remove(c)
                    continue
                size = person['sizes'][0 if c.get('lane') == '1' else 1]
                name = sc['clips'][person['who']][size][cfg['wear']]
                a = asset_for(person['who'], size, name)
                c.set('ref', a.get('id'))
                c.set('name', name)
                c.set('format', a.get('format'))
                c.set('start', S(in_point(name, dur, ch)))
                c.set('duration', x.get('duration'))
                for k in list(c):
                    if k.tag == 'keyword':
                        c.remove(k)
                    # A19 の青柳さんの顔のセンサー（ぼかし）は A19 の映像の頭の位置に合わせた値なので外す（A24 は blur_face で付け直す）
                    if k.tag == 'filter-video' and k.get('name') == 'センサー':
                        c.remove(k)
                cr = c.find('conform-rate')
                if cr is not None:
                    cr.set('srcFrameRate', '29.97')
                if vid_dir and opt.get('--models'):
                    bx = body_box(os.path.join(vid_dir, name), T(c.get('start')), dur, opt['--models'])
                    if bx:
                        boxes[c.get('lane')] = (c, name, bx)
            # 構図: A24 の素材は人の位置が A19 と違うので、姿勢から逆算して窓に収める（頭の上に余白、足まで入れる）。
            # 同じ人の 2 サイズは同じ拡大に（窮屈な方に合わせる）
            if boxes:
                common = min(fit_scale(b[2]) for b in boxes.values())
                # 窓を覆うために拡大が上がることがあるので、大きい方でもう一度そろえる
                common = max(fit(lane_, b[2], common)[0] for lane_, b in boxes.items())
                for lane_, (c, name, bx) in boxes.items():
                    if True:
                        sc_, x_, y_, r_ = fit(lane_, bx, common)
                        tr_ = c.find('adjust-transform')
                        if tr_ is None:
                            tr_ = ET.SubElement(c, 'adjust-transform')
                        tr_.set('position', f'{x_} {y_}')
                        tr_.set('scale', f'{sc_} {sc_}')
                        tt_ = c.find('adjust-crop/trim-rect')
                        if tt_ is not None:
                            if c.get('lane') == '2':
                                tt_.set('right', f'{r_}')
                            else:
                                # 右の窓（〜1824px）の右端まで映像が届くように、切り取りを必要なだけに
                                X0_ = 960 + x_ * 10.8
                                tt_.set('right', f'{max(0.0, (X0_ + 960 * sc_ - 1850) / sc_ / 10.8):.4f}')
                        framed.append((name, sc_, x_, y_))
                # 顔のブラー（plan の blur_face の人）: 同じ動画を真上に重ね、首から上だけ切り取ってガウス（A23 の青柳さんと同じ 0.5）
                if person['who'] in sc.get('blur_face', []):
                    gid = next((r.get('id') for r in resources if r.tag == 'effect' and 'Gaussian' in (r.get('uid') or '')), None)
                    for c in x:
                        if c.get('lane') is not None and c.get('lane').lstrip('-').isdigit() and int(c.get('lane')) >= 2:
                            c.set('lane', str(int(c.get('lane')) + (1 if c.get('lane') == '2' else 2)))
                    for lane_old, lane_new in (('1', '2'), ('2', '4')):
                        if lane_old not in boxes:
                            continue
                        c, name, bx = boxes[lane_old]
                        hy0, hy1, hx0, hx1 = bx[3]
                        dup = copy.deepcopy(c)
                        dup.set('lane', lane_new)
                        for k in list(dup):
                            if k.tag in ('adjust-crop', 'adjust-volume', 'filter-video', 'marker', 'chapter-marker', 'keyword'):
                                dup.remove(k)
                        crop = ET.Element('adjust-crop', mode='trim')
                        ET.SubElement(crop, 'trim-rect', left=f'{max(0.0, hx0) * 1920 / 10.8:.4f}', right=f'{max(0.0, 1 - hx1) * 1920 / 10.8:.4f}',
                                      top=f'{max(0.0, hy0) * 100:.4f}', bottom=f'{max(0.0, 1 - hy1) * 100:.4f}')
                        kids = list(dup)
                        pos_ = next((n for n, k in enumerate(kids) if k.tag == 'adjust-transform'), 0)
                        dup.insert(pos_, crop)
                        ET.SubElement(dup, 'adjust-volume', amount='-96dB')
                        for k in c.findall('filter-video'):
                            dup.append(copy.deepcopy(k))
                        if gid:
                            g = ET.SubElement(dup, 'filter-video', ref=gid, name='ガウス')
                            ET.SubElement(g, 'param', name='Amount', key='9999/986883370/100/986883376/2/100', value='0.5')
                        idx = list(x).index(c)
                        x.insert(idx + 1, dup)
                    blurred.append(person['who'])
            # テロップ
            for c in [c for c in x if c.tag == 'title']:
                t = txt(c)
                first = t.strip().split('\n')[0].strip()
                lines = [ln for ln in t.split('\n')]
                if first in ('M', 'S', 'XS') and len([ln for ln in lines if ln.strip()]) >= 4:
                    set_lines(c, [first] + [v + 'cm' for v in spec[first]])
                elif first in ('着丈', 'ウエスト', '前身頃', '総丈'):
                    set_lines(c, list(spec['header']))
                elif cfg['template']['product'] in t:
                    runs = c.find('text').findall('text-style')
                    for r in runs:
                        if cfg['template']['product'] in (r.text or ''):
                            r.text = pr['name']
                        elif 'Color :' in (r.text or ''):
                            r.text = f"Color : {pr['color']} | Size : {pr['sizes']}" + ('\n' if (r.text or '').endswith('\n') else '')
                        elif (r.text or '').strip().startswith('¥'):
                            r.text = pr['price']
                    c.set('name', c.get('name').replace(cfg['template']['product'], pr['name']))
            # 書式 ID を複製ごとに一意に
            n_ts[0] += 1
            for tsd in x.iter('text-style-def'):
                tsd.set('id', f"{tsd.get('id')}_sc{n_ts[0]}")
            for ts in x.iter('text-style'):
                if ts.get('ref'):
                    ts.set('ref', f"{ts.get('ref')}_sc{n_ts[0]}")
            out_blocks.append(x)
            report.append((ch, person['who'], float(dur), [(c.get('lane'), c.get('name'), round(float(T(c.get('start'))), 2)) for c in x if c.tag == 'asset-clip']))
        blocks_at[id(before)] = (at, out_blocks)

    # ---- スパインに差し込み、後ろをずらす ----
    shifts = []  # (差し込み位置（元の時刻）, 長さ)
    new_items = []
    for e, st in zip(items, starts):
        if id(e) in blocks_at:
            at, bl = blocks_at[id(e)]
            new_items += bl
            shifts.append((at, sum(T(b.get('duration')) for b in bl)))
        new_items.append(e)
    for e in list(spine):
        spine.remove(e)
    cur = Fraction(0)
    for e in new_items:
        e.set('offset', S(cur))
        spine.append(e)
        cur += T(e.get('duration'))
    seq.set('duration', S(cur))

    def moved(t):
        return t + sum(dd for at, dd in shifts if at <= t)

    # ---- 差し込み位置をまたぐ接続クリップ ----
    n_bgm = n_trim = 0
    for e, st in zip(items, starts):
        for c in list(e):
            if c.get('lane') is None or c.get('offset') is None:
                continue
            a0 = st + T(c.get('offset')) - T(e.get('start'))
            a1 = a0 + T(c.get('duration'))
            inside = [(at, dd) for at, dd in shifts if a0 < at < a1]
            if not inside:
                continue
            add = sum(dd for at, dd in inside)
            if c.get('lane').lstrip('-').isdigit() and int(c.get('lane')) < 0:
                # BGM: 差し込んだ分だけ長く。音量の変化（キーフレーム）も同じだけ後ろへ
                c.set('duration', S(T(c.get('duration')) + add))
                cs = T(c.get('start'))
                for kf in c.iter('keyframe'):
                    kt = T(kf.get('time'))
                    abs_t = a0 + (kt - cs)
                    kf.set('time', S(kt + sum(dd for at, dd in inside if at <= abs_t)))
                # 素材（複合クリップ）が足りなければ、中の最後の曲をつなぎ足す
                m = next((r for r in resources if r.get('id') == c.get('ref')), None)
                if m is not None and m.tag == 'media':
                    ms = m.find('sequence')
                    need = cs + T(c.get('duration'))
                    msp = ms.find('spine')
                    while T(ms.get('duration')) < need and len(msp):
                        last = copy.deepcopy(msp[-1])
                        last.set('offset', S(T(ms.get('duration'))))
                        msp.append(last)
                        ms.set('duration', S(T(ms.get('duration')) + T(last.get('duration'))))
                n_bgm += 1
            else:
                # 映像・テロップ: 差し込み位置で終える
                first_at = min(at for at, dd in inside)
                c.set('duration', S(first_at - a0))
                n_trim += 1

    # ---- 使っていない取り込みリソースを消す（差し替え前の A19・A23 の動画、外した本編の音など）----
    def refs_in(el):
        r = set()
        for x in el.iter():
            for k in ('ref', 'format'):
                if x.get(k):
                    r.add(x.get(k))
        return r

    n_pruned = 0
    while True:
        used_ids = refs_in(project)
        for r in resources:
            if r.get('id') in used_ids:
                used_ids |= refs_in(r)
        # 参照の連鎖（media の中の asset など）を閉じる
        changed = True
        while changed:
            changed = False
            for r in resources:
                if r.get('id') in used_ids:
                    more = refs_in(r) - used_ids
                    if more:
                        used_ids |= more
                        changed = True
        drop = [r for r in resources if r.get('id') not in ids and r.get('id') not in used_ids]
        if not drop:
            break
        for r in drop:
            resources.remove(r)
            n_pruned += 1

    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))
    for r in report:
        print(*r)
    print('構図を合わせた動画:', len(framed), '| 顔のブラー:', len(blurred), 'ブロック')
    print('差し込み:', [(round(float(at), 2), round(float(dd), 2)) for at, dd in shifts], '合計', round(float(sum(dd for _, dd in shifts)), 2), '秒',
          '| BGM 延長', n_bgm, '| 位置で終えた要素', n_trim, '| 登録した動画', len(new_assets), '| 消した未使用リソース', n_pruned, '->', out)


if __name__ == '__main__':
    main()
