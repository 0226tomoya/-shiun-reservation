"""動画（か画像）の 1 コマから服の形を切り抜き、測る点（ランドマーク）を推して points.json に書く。確認用の画像も出す。
    python3 measure_points.py IN.mp4|IN.png 種類(TOPS|OUTER|SHIRT|BOTTOMS) OUT_points.json [--at 秒] [--check OUT.png]
推した点は必ず確認用の画像で見て、ずれていたら points.json を手で直す（肩先・脇は服の形で外れやすい）"""
import sys, json, subprocess, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def load(src, at):
    if src.lower().endswith(('.png', '.jpg', '.jpeg')): return Image.open(src).convert('RGB')
    b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(at), '-i', src, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    return Image.open(io.BytesIO(b)).convert('RGB')


def garment_mask(im, ignore=None, thr=38):
    """背景（画の縁の色）との差で服を切り抜く。細い物（ハンガーのフック）は開いて落とし、一番大きい塊だけ残す"""
    a = np.asarray(im).astype(float); H, W = a.shape[:2]
    edge = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3), a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
    bgc = np.median(edge, 0)
    # 背景は明るさがゆっくり変わるので、大きくぼかした画との差も使う
    blur = np.asarray(im.filter(ImageFilter.GaussianBlur(60))).astype(float)
    dist = np.minimum(np.linalg.norm(a - bgc, axis=2), np.linalg.norm(a - blur, axis=2) * 1.6)
    m = dist > thr
    if ignore:
        for x0, y0, x1, y1 in ignore: m[y0:y1, x0:x1] = False
    mi = Image.fromarray((m * 255).astype('uint8'))
    mi = mi.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(9))   # 細い物を落とす
    mi = mi.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))   # 小さい穴を埋める
    m = np.asarray(mi) > 127
    from scipy import ndimage
    lab, n = ndimage.label(m)
    if n == 0: raise SystemExit('服が見つからない')
    big = np.argmax(ndimage.sum(m, lab, range(1, n + 1))) + 1
    m = ndimage.binary_fill_holes(lab == big)
    # 仕上げ: GrabCut（色の差だけだと、色落ちした明るい所や白い服が背景と見分けにくい）。半分の大きさで回して戻す
    import cv2
    k = 0.5; sm = cv2.resize(np.asarray(im), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    ys, xs = np.where(m); pad = 25
    x0, y0, x1, y1 = [int(v * k) for v in (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, W - 1), min(ys.max() + pad, H - 1))]
    gm = np.full(sm.shape[:2], cv2.GC_BGD, np.uint8); gm[y0:y1, x0:x1] = cv2.GC_PR_BGD
    rm = cv2.resize(m.astype(np.uint8), (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    gm[rm] = cv2.GC_PR_FGD
    core = cv2.erode(rm.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0; gm[core] = cv2.GC_FGD
    if ignore:
        for a0, b0, a1, b1 in ignore: gm[int(b0 * k):int(b1 * k), int(a0 * k):int(a1 * k)] = cv2.GC_BGD
    bgm, fgm = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(cv2.cvtColor(sm, cv2.COLOR_RGB2BGR), gm, None, bgm, fgm, 6, cv2.GC_INIT_WITH_MASK)
    g = ((gm == cv2.GC_FGD) | (gm == cv2.GC_PR_FGD)).astype(np.uint8)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR) > 0
    lab, n = ndimage.label(g)
    if n: g = lab == (np.argmax(ndimage.sum(g, lab, range(1, n + 1))) + 1)
    return ndimage.binary_fill_holes(g)


def runs(row):
    xs = np.where(row)[0]
    if len(xs) == 0: return []
    cut = np.where(np.diff(xs) > 3)[0]
    return [(xs[a], xs[b]) for a, b in zip(np.r_[0, cut + 1], np.r_[cut, len(xs) - 1])]


def climb(m, x, y, y_stop, x_lo, x_hi):
    """背景の空き（x, y）から 1 行ずつ上へ、空きの真ん中をたどる。空きが無くなった所（服がつながる所）を返す"""
    while y > y_stop:
        row = ~m[y - 1]
        if not row[x]: break
        l = x
        while l > x_lo and row[l - 1]: l -= 1
        r = x
        while r < x_hi and row[r + 1]: r += 1
        x = (l + r) // 2; y -= 1
    return int(x), int(y)


def bottoms(m):
    ys, xs = np.where(m); y0, y1 = ys.min(), ys.max(); x0, x1 = xs.min(), xs.max()
    cx = (x0 + x1) / 2
    top = y0 + 4
    r = runs(m[top + 12]); wl, wr = r[0][0], r[-1][1]
    # 股: 両脚の間の背景（裾の高さで真ん中にある空き）を上へたどった、いちばん上の点
    yb = y1 - 3
    while yb > y0 and len([q for q in runs(m[yb]) if q[1] - q[0] > 20]) < 2: yb -= 1   # 両脚がそろう高さ（裾の高さが違うことがある）
    yb -= 4
    gaps = [q for q in runs(~m[yb, x0:x1 + 1])]
    gaps = [(a + x0, b + x0) for a, b in gaps if a > 0 and b < x1 - x0]   # 両端の外側は除く
    crotch = None
    if gaps:
        g = min(gaps, key=lambda q: abs((q[0] + q[1]) / 2 - cx)); gx = int((g[0] + g[1]) / 2)
        crotch = climb(m, gx, yb, y0, x0, x1)
    if crotch is None: raise SystemExit('股が見つからない（脚の間が分かれていない）')
    # 左脚の裾
    left = m[:, :crotch[0]]; yl = np.where(left.any(1))[0].max()
    rr = runs(m[yl - 10, :crotch[0]]); hl_out, hl_in = rr[0][0], rr[-1][1]
    right = m[:, crotch[0]:]; yr = np.where(right.any(1))[0].max()
    thigh = runs(m[crotch[1] + 2])[0][0]
    return {'bbox': [int(x0), int(y0), int(x1), int(y1)], 'ウエスト上端': [int(cx), int(y0)], 'ウエストL': [int(wl), int(top)], 'ウエストR': [int(wr), int(top)],
            '股': [int(crotch[0]), int(crotch[1])], '腿L': [int(thigh), int(crotch[1])], '裾': [int(cx), int(yl)],
            '裾L外': [int(hl_out), int(yl)], '裾L内': [int(hl_in), int(yl)], '裾R': [int(crotch[0] + (x1 - crotch[0]) / 2), int(yr)]}


def tops(m):
    """トップス・アウター・シャツの点。順番: 首 → 裾（真ん中の列）→ 胴の幅 → 脇 → 肩先 → 袖口。
    自信の低い点は _要確認 に入れる（袖が胴に付いて下がっていて脇が見えない、など）"""
    ys, xs = np.where(m); y0, y1 = ys.min(), ys.max(); x0, x1 = xs.min(), xs.max()
    H, Wd = y1 - y0, x1 - x0; cx = int((x0 + x1) / 2); unsure = []
    top_y = np.array([np.where(m[:, x])[0].min() if m[:, x].any() else 10 ** 6 for x in range(m.shape[1])])
    # 首
    neck_c = [cx, int(top_y[cx])]
    L = np.arange(x0, cx); R = np.arange(cx, x1)
    nl = int(L[np.argmin(top_y[L])]); nr = int(R[np.argmin(top_y[R])])
    # 裾: 真ん中の列を首から下へたどり、服が切れた所
    yy = int(top_y[cx])
    while yy + 1 < m.shape[0] and m[yy + 1, cx]: yy += 1
    hem_y = yy
    def run_at(y):
        rr = runs(m[y]); seg = [q for q in rr if q[0] <= cx <= q[1]]
        return seg[0] if seg else None
    hb = run_at(max(hem_y - 12, y0)); bl, br = hb
    hem_fused = (br - bl) > Wd * 0.92   # 裾の行に袖まで入っている（袖が胴に付いて下がっている）
    # 脇 1: 袖と胴の間に空きがあれば、下から上へたどる（袖を広げた平置き・半袖）
    arm = armL = armR = None
    for y in range(hem_y - 12, y0 + H // 4, -2):
        rr = [q for q in runs(m[y]) if q[1] - q[0] > 6]
        bi = next((i for i, q in enumerate(rr) if q[0] <= cx <= q[1]), None)
        if bi is not None and 0 < bi < len(rr) - 1:
            a_ = climb(m, (rr[bi - 1][1] + rr[bi][0]) // 2, y, y0, x0, x1)
            b_ = climb(m, (rr[bi][1] + rr[bi + 1][0]) // 2, y, y0, x0, x1)
            if min(abs(a_[0] - cx), abs(b_[0] - cx)) > Wd * 0.15 and max(a_[1], b_[1]) < y0 + H * 0.7:
                armL, armR = a_, b_; arm = (a_[1] + b_[1]) // 2
            break
    # 脇 2: 空きが無ければ、裾から上へ胴の幅を見て、外へ広がり始める高さ（袖付け）
    if arm is None:
        bw = br - bl
        for y in range(hem_y - 12, y0, -1):
            q = run_at(y)
            if q and (q[0] < bl - bw * 0.06 or q[1] > br + bw * 0.06):
                arm = y; break
        if arm is None or arm > y0 + H * 0.7:
            arm = int(y0 + H * 0.3); unsure += ['脇L', '脇R']
        q = run_at(min(arm + 6, y1)) or (bl, br)
        armL, armR = (int(max(q[0], bl if '脇L' in unsure else q[0])), arm), (int(min(q[1], br if '脇R' in unsure else q[1])), arm)
    al, ar = armL[0], armR[0]
    if hem_fused:
        unsure += ['裾L', '裾R']; bl, br = (al, ar) if '脇L' not in unsure else (bl, br)
    # 肩先: 首横から外へ、上の縁が急に下へ曲がる角（上 22% の中だけ）
    def corner(xs_, sign):
        best, bx = -1e9, None; k = max(12, int(Wd * 0.03))
        for x in xs_:
            a_, b_ = x - k * sign, x + k * sign
            if not (x0 <= min(a_, b_) and max(a_, b_) <= x1) or top_y[x] > y0 + H * 0.22: continue
            c = (top_y[b_] - top_y[x]) / k - (top_y[x] - top_y[a_]) / k
            if c > best: best, bx = c, x
        return bx
    sl = corner(range(nl - 4, x0, -1), -1); sr = corner(range(nr + 4, x1), 1)
    if sl is None: sl = al; unsure.append('肩先L')
    if sr is None: sr = ar; unsure.append('肩先R')
    # 袖口: 右下（胴の真ん中より右、上 3 割より下）で肩先から一番遠い所の、袖口の辺の真ん中
    pts = np.stack(np.where(m), 1)
    side = pts[(pts[:, 1] > cx + Wd * 0.2) & (pts[:, 0] > y0 + H * 0.3)]
    if len(side):
        q = side[np.argmax(np.hypot(side[:, 1] - sr, side[:, 0] - top_y[sr]))]
        band = side[np.abs(side[:, 0] - q[0]) <= 6]; cuff = [int(band[:, 1].mean()), int(q[0])]
    else:
        cuff = [int(x1), int(y1)]; unsure.append('袖口R')
    return {'bbox': [int(x0), int(y0), int(x1), int(y1)], '首中心': neck_c, '首横L': [nl, int(top_y[nl])], '首横R': [nr, int(top_y[nr])],
            '肩先L': [int(sl), int(top_y[sl])], '肩先R': [int(sr), int(top_y[sr])], '脇L': [int(armL[0]), int(armL[1])], '脇R': [int(armR[0]), int(armR[1])],
            '裾L': [int(bl), int(hem_y)], '裾R': [int(br), int(hem_y)], '裾': [cx, int(hem_y)], '袖口R': cuff, '_要確認': unsure}


def main():
    src, kind, out = sys.argv[1], sys.argv[2].upper(), sys.argv[3]
    at = float(sys.argv[sys.argv.index('--at') + 1]) if '--at' in sys.argv else 0.5
    ign = json.loads(sys.argv[sys.argv.index('--ignore') + 1]) if '--ignore' in sys.argv else None
    thr = float(sys.argv[sys.argv.index('--thr') + 1]) if '--thr' in sys.argv else 38
    im = load(src, at); m = garment_mask(im, ign, thr)
    P = bottoms(m) if kind == 'BOTTOMS' else tops(m)
    json.dump(P, open(out, 'w'), ensure_ascii=False, indent=1); print(json.dumps(P, ensure_ascii=False))
    if '--check' in sys.argv:
        c = im.convert('RGBA'); ov = Image.new('RGBA', c.size, 0)
        ov.putalpha(Image.fromarray((m * 70).astype('uint8'))); ov2 = Image.new('RGBA', c.size, (0, 140, 255, 0)); ov2.putalpha(Image.fromarray((m * 60).astype('uint8')))
        c.alpha_composite(ov2); d = ImageDraw.Draw(c); f = ImageFont.truetype('/root/.fonts/NotoSansJP-700.ttf', 22)
        for k, p in P.items():
            if k.startswith('_'): continue
            if k == 'bbox': d.rectangle(p, outline=(0, 160, 0), width=2); continue
            c_ = (240, 140, 0) if k in P.get('_要確認', []) else (230, 30, 30)
            x, y = p; d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=c_, width=3); d.text((x + 9, y - 28), k + ('（要確認）' if c_[1] == 140 else ''), font=f, fill=c_, stroke_width=2, stroke_fill='white')
        c.convert('RGB').save(sys.argv[sys.argv.index('--check') + 1])


if __name__ == '__main__':
    main()
