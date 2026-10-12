"""行（1 字ずつに分けた字のまとまり）を、字間を保ったまま動かして合わせる。
tune.py は字ごとに独立して動くので、字の間が空いたり重なったりする。ここでは行全体を 1 つとして
  大きさ s（全字共通）・字間 k（行の向きに沿った字の中心の間隔の倍率）・位置 dx, dy
だけを探す。字どうしの並び・高さのそろいは崩れない。

python3 tune_group.py ID [--layers 3,4,5 | --grp L2] [--apply] [--spacing-only] [--rots -2,0,2]
  --layers / --grp   動かす字（省略時は "grp" ごとに全部の行）
  --spacing-only     大きさは変えず、字間と位置だけ（字間だけ直したいとき）
  --rots             行の傾き（度）も候補にする（各字の rotate にも足す）
  --fine             最後に各字を ±FINE px（既定 2）だけ個別に動かす（字の形は変えない）
レイヤーの "notune": true は動かさない。
環境変数: S0,S1（大きさの範囲 既定 0.92〜1.08）K0,K1（字間 既定 0.85〜1.15）PAD（探す余白 既定 40）EXCL（他のレイヤーを的から外す 既定 1）
"""
import json, os, sys, math
import cv2, numpy as np
TH = '/home/user/-shiun-reservation/editing/thumbs'
sys.path.insert(0, TH)
import render as R
ORIG = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs'

args = sys.argv[1:]
vid = args[0]
sp = os.path.join(TH, 'specs', vid + '.json')
spec = json.load(open(sp))
if any(isinstance(e, dict) and e.get('by') == 'layers' for e in spec.get('erase', [])) and os.environ.get('FORCE') != '1':
    print('erase に "by":"layers" がある: 字が自分の描いた形を追いかけて偽の点になるので動かさない。色の erase に替えてから（FORCE=1 で強制）')
    sys.exit(2)
orig = cv2.resize(cv2.imread(os.path.join(ORIG, vid + '.jpg')), (R.W, R.H))
R.erase_mask(spec, orig, np.zeros((R.H, R.W), np.uint8))
Tm = R.erase_mask.raw.astype(np.uint8)
keep = np.zeros((R.H, R.W), np.uint8)
for poly in spec.get('front', []):
    cv2.fillPoly(keep, [np.array(poly, np.int32)], 255)
Tm[keep > 0] = 0

apply = '--apply' in args
sp_only = '--spacing-only' in args
fine = '--fine' in args
rots = [0.0]
if '--rots' in args:
    rots = [float(v) for v in args[args.index('--rots') + 1].split(',')]
texts = [i for i, L in enumerate(spec['layers']) if L['type'] == 'text']
if '--layers' in args:
    groups = [[int(v) for v in args[args.index('--layers') + 1].split(',')]]
else:
    want = args[args.index('--grp') + 1] if '--grp' in args else None
    g = {}
    for i in texts:
        k = spec['layers'][i].get('grp')
        if k and (want is None or k == want):
            g.setdefault(k, []).append(i)
    groups = [v for v in g.values() if len(v) >= 2]
if not groups:
    print('行（grp）がありません。split.py で分けるか --layers で指定'); sys.exit(1)

S0, S1 = float(os.environ.get('S0', 0.92)), float(os.environ.get('S1', 1.081))
K0, K1 = float(os.environ.get('K0', 0.85)), float(os.environ.get('K1', 1.151))
PAD = int(os.environ.get('PAD', 40))
EXCL = os.environ.get('EXCL', '1') == '1'
FINE = int(os.environ.get('FINE', 2))
scales = [1.0] if sp_only else list(np.arange(S0, S1, 0.02))
ks = list(np.arange(K0, K1, 0.025))


def alpha_of(page, L):
    a = R.render_layers({'id': vid, 'layers': [L]}, page)[:, :, 3] > 128
    a[keep > 0] = False
    return a.astype(np.uint8)


def ink(a):
    ys, xs = np.where(a)
    if not len(xs):
        return None
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    return a[y0:y1, x0:x1].astype(np.float32), np.array([(x0 + x1) / 2, (y0 + y1) / 2])


def compose(chars, C, u, s, k, rot):
    """各字を s 倍し、中心を C から (行方向 u に k*s 倍・直角方向に s 倍) で置き直し、rot 度回す。"""
    v = np.array([-u[1], u[0]])
    th = math.radians(rot)
    Rm = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    pos, ims = [], []
    for t, c in chars:
        d = c - C
        d2 = Rm @ (u * (d @ u) * k * s + v * (d @ v) * s)
        tt = cv2.resize(t, (max(1, int(round(t.shape[1] * s))), max(1, int(round(t.shape[0] * s)))), interpolation=cv2.INTER_LINEAR)
        if rot:
            h, w = tt.shape
            M = cv2.getRotationMatrix2D((w / 2, h / 2), -rot, 1)
            cs, sn = abs(M[0, 0]), abs(M[0, 1])
            nw, nh = int(h * sn + w * cs) + 2, int(h * cs + w * sn) + 2
            M[0, 2] += nw / 2 - w / 2; M[1, 2] += nh / 2 - h / 2
            tt = cv2.warpAffine(tt, M, (nw, nh))
        pos.append(C + d2); ims.append(tt)
    x0 = min(p[0] - im.shape[1] / 2 for p, im in zip(pos, ims)); y0 = min(p[1] - im.shape[0] / 2 for p, im in zip(pos, ims))
    x1 = max(p[0] + im.shape[1] / 2 for p, im in zip(pos, ims)); y1 = max(p[1] + im.shape[0] / 2 for p, im in zip(pos, ims))
    ox, oy = int(math.floor(x0)), int(math.floor(y0))
    canvas = np.zeros((int(math.ceil(y1)) - oy + 1, int(math.ceil(x1)) - ox + 1), np.float32)
    for p, im in zip(pos, ims):
        px, py = int(round(p[0] - im.shape[1] / 2)) - ox, int(round(p[1] - im.shape[0] / 2)) - oy
        h, w = im.shape
        canvas[py:py + h, px:px + w] = np.maximum(canvas[py:py + h, px:px + w], im[:canvas.shape[0] - py, :canvas.shape[1] - px])
    return (canvas > 0.5).astype(np.float32), (ox, oy), pos


def match(tt, org, T, win):
    """win（固定の範囲）の中で一番重なる位置を探す。IoU の分母の「元の文字」は win 全体で数える
    （置いた箱の中だけで数えると、縮めるほど得をする偏りが出る）。"""
    th, tw = tt.shape
    X0, Y0, X1, Y1 = win
    img = T[Y0:Y1, X0:X1].astype(np.float32)
    if img.shape[0] < th or img.shape[1] < tw:
        return None
    cc = cv2.matchTemplate(img, tt, cv2.TM_CCORR)
    _, mv, _, ml = cv2.minMaxLoc(cc)
    return mv / (tt.sum() + img.sum() - mv + 1e-6), X0 + ml[0] - org[0], Y0 + ml[1] - org[1]


from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args=['--allow-file-access-from-files'])
    page = b.new_page(viewport={'width': R.W, 'height': R.H})
    alph = {j: alpha_of(page, Lj) for j, Lj in enumerate(spec['layers'])} if EXCL else {}
    for grp in groups:
        grp = [i for i in grp if not spec['layers'][i].get('notune')]  # 手で直した字は動かさない
        if len(grp) < 2:
            continue
        T = Tm
        if EXCL:
            oth = np.zeros_like(Tm)
            for j, a_ in alph.items():
                if j not in grp:
                    oth |= a_
            T = (Tm & (1 - cv2.dilate(oth, np.ones((3, 3), np.uint8)))).astype(np.uint8)
        chars = []
        for i in grp:
            r = ink(alph[i] if EXCL else alpha_of(page, spec['layers'][i]))
            if r is None:
                print('empty', i); continue
            chars.append(r)
        if len(chars) < 2:
            continue
        cs = np.array([c for _, c in chars]); C = cs.mean(0)
        # 行の向き（中心の並びの主軸）
        _, _, vt = np.linalg.svd(cs - C)
        u = vt[0] / np.linalg.norm(vt[0])
        if abs(u[0]) >= abs(u[1]) and u[0] < 0 or abs(u[1]) > abs(u[0]) and u[1] < 0:
            u = -u
        base, org0, _ = compose(chars, C, u, 1, 1, 0)
        grow = max(S1, 1) * max(K1, 1) - 1
        mx = int(PAD + base.shape[1] * grow / 2 + 4); my = int(PAD + base.shape[0] * grow / 2 + 4)
        if len(rots) > 1 or rots[0]:
            mx = my = max(mx, my) + int(max(base.shape) * math.sin(math.radians(max(abs(r) for r in rots))) / 2)
        win = (max(0, org0[0] - mx), max(0, org0[1] - my), min(R.W, org0[0] + base.shape[1] + mx), min(R.H, org0[1] + base.shape[0] + my))
        r0 = match(base, org0, T, win)
        best = None
        for rot in rots:
            for s in scales:
                for k in ks:
                    tt, org, pos = compose(chars, C, u, s, k, rot)
                    r = match(tt, org, T, win)
                    if r and (best is None or r[0] > best[0]):
                        best = (r[0], s, k, rot, r[1], r[2], pos)
        txt = ''.join(spec['layers'][i].get('text', '') for i in grp)
        print(f"grp {grp[0]}..{grp[-1]} {txt[:16]} iou {r0[0] if r0 else 0:.3f} -> {best[0]:.3f}  s={best[1]:.2f} k={best[2]:.3f} rot={best[3]} dx={best[4]} dy={best[5]}")
        if apply and best and (r0 is None or best[0] > r0[0] + 0.002):
            _, s, k, rot, dx, dy, pos = best
            for i, ptarget in zip(grp, pos):
                L = spec['layers'][i]
                L['size'] = round(L.get('size', 80) * s, 1)
                if rot:
                    L['rotate'] = round(L.get('rotate', 0) + rot, 2)
                r = ink(alpha_of(page, L))
                if r is None:
                    continue
                want = ptarget + np.array([dx, dy])
                L['x'] = round(L['x'] + float(want[0] - r[1][0]), 1)
                L['y'] = round(L['y'] + float(want[1] - r[1][1]), 1)
            if fine:  # 字の形・大きさはそのままで、各字を ±FINE px だけ
                for i in grp:
                    L = spec['layers'][i]
                    r = ink(alpha_of(page, L))
                    if r is None:
                        continue
                    t, c = r
                    org = (int(round(c[0] - t.shape[1] / 2)), int(round(c[1] - t.shape[0] / 2)))
                    th_, tw_ = t.shape
                    X0, Y0 = max(0, org[0] - FINE), max(0, org[1] - FINE)
                    img = T[Y0:min(R.H, org[1] + th_ + FINE), X0:min(R.W, org[0] + tw_ + FINE)].astype(np.float32)
                    if img.shape[0] < th_ or img.shape[1] < tw_:
                        continue
                    _, _, _, ml = cv2.minMaxLoc(cv2.matchTemplate(img, t, cv2.TM_CCORR))
                    L['x'] = round(L['x'] + X0 + ml[0] - org[0], 1); L['y'] = round(L['y'] + Y0 + ml[1] - org[1], 1)
            for i in grp:
                alph[i] = alpha_of(page, spec['layers'][i])
            print('   applied')
    b.close()
if apply:
    json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
