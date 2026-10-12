"""Light per-layer aligner (one render per layer per pass; no fit.py).
python3 tune.py ID [--layers 0,1] [--apply] [--fonts 'NotoSansJP:900,DelaGothicOne:400'] [--noscale]
レイヤーに "notune": true → 動かさない（手で直した字）。"fit_color": "#文字色"（"fit_tol": 40）→ その色の画素だけを的にする（白縁・光彩を外す）。
"""
import json, os, sys, copy
import cv2, numpy as np
TH = '/home/user/-shiun-reservation/editing/thumbs'
sys.path.insert(0, TH)
import render as R
ORIG = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs'

args = sys.argv[1:]
vid = args[0]
sp = os.path.join(TH, 'specs', vid + '.json')
spec = json.load(open(sp))
orig = cv2.resize(cv2.imread(os.path.join(ORIG, vid + '.jpg')), (R.W, R.H))
R.erase_mask(spec, orig, np.zeros((R.H, R.W), np.uint8))
Tm = R.erase_mask.raw.astype(np.uint8)
keep = np.zeros((R.H, R.W), np.uint8)
for poly in spec.get('front', []):
    cv2.fillPoly(keep, [np.array(poly, np.int32)], 255)
Tm[keep > 0] = 0
lay = [i for i, L in enumerate(spec['layers']) if L['type'] == 'text']
if '--layers' in args:
    lay = [int(v) for v in args[args.index('--layers') + 1].split(',')]
apply = '--apply' in args
OLDIOU = os.environ.get('OLDIOU') == '1'
noscale = '--noscale' in args
fonts = None
if '--fonts' in args:
    fonts = [f.split(':') for f in args[args.index('--fonts') + 1].split(',')]


HAND = ('klee', 'yusei', 'zenkurenaido', 'yomogi', 'hachimaru', 'caveat', 'gochihand', 'homemadeapple', 'permanentmarker', 'reeniebeanie', 'shadowsintolight', 'nothingyoucoulddo', 'dancingscript', 'kaushan', 'marckscript', 'mrdafoe', 'sacramento', 'satisfy', 'alexbrush', 'allura', 'greatvibes', 'parisienne', 'pinyon', 'cookie', 'badscript', 'mrssaintdelafield')  # 手書き・筆記体


def is_hand(f):
    f = (f or '').lower().replace(' ', '')
    return any(h in f for h in HAND)


def color_mask(hexc, tol):
    c = hexc.lstrip('#')
    bgr = np.uint8([[[int(c[4:6], 16), int(c[2:4], 16), int(c[0:2], 16)]]])
    lab = cv2.cvtColor(orig, cv2.COLOR_BGR2LAB).astype(np.float32)
    cl = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
    return (np.linalg.norm(lab - cl, axis=2) < tol).astype(np.uint8)


def alpha_of(page, L):
    s = {'id': vid, 'layers': [L]}
    a = R.render_layers(s, page)[:, :, 3] > 128
    a[keep > 0] = False
    return a.astype(np.uint8)


def best(a, scales, Tm=Tm):
    ys, xs = np.where(a)
    if not len(xs):
        return None
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    t = a[y0:y1, x0:x1].astype(np.float32)
    pad = int(os.environ.get("PAD", 50))
    X0, Y0 = max(0, x0 - pad), max(0, y0 - pad)
    X1, Y1 = min(R.W, x1 + pad), min(R.H, y1 + pad)
    smax = max(s * sx for s, sx in scales); g = max(0, smax - 1)
    FX0, FY0 = max(0, int(x0 - pad - (x1 - x0) * g)), max(0, int(y0 - pad - (y1 - y0) * g))
    FX1, FY1 = min(R.W, int(x1 + pad + (x1 - x0) * g)), min(R.H, int(y1 + pad + (y1 - y0) * g))
    res = None
    for s, sx in scales:
        tw, th = max(2, int(round(t.shape[1] * s * sx))), max(2, int(round(t.shape[0] * s)))
        tt = (cv2.resize(t, (tw, th), interpolation=cv2.INTER_LINEAR) > 0.5).astype(np.float32)
        # window large enough
        wx0, wy0 = max(0, min(X0, x0 - (tw - t.shape[1]) - pad)), max(0, min(Y0, y0 - (th - t.shape[0]) - pad))
        wx1, wy1 = min(R.W, max(X1, x0 + tw + pad)), min(R.H, max(Y1, y0 + th + pad))
        img = Tm[wy0:wy1, wx0:wx1].astype(np.float32)
        if img.shape[0] < th or img.shape[1] < tw:
            continue
        cc = cv2.matchTemplate(img, tt, cv2.TM_CCORR)
        _, mv, _, ml = cv2.minMaxLoc(cc)
        T = img.sum()
        A = tt.sum()
        # IoU relative to window target (approx; target includes other layers)
        if OLDIOU:  # 旧: 置いた箱の中の元の文字だけで数える（縮めるほど得をする偏りがある）
            tw_ = Tm[wy0 + ml[1]:wy0 + ml[1] + th, wx0 + ml[0]:wx0 + ml[0] + tw].sum()
        else:  # 新: 固定の範囲（元の字の外接＋余白＋最大の拡大分）の元の文字を全部数える
            # 置いた箱が固定範囲からはみ出た分の元の文字も足す
            out = Tm[wy0 + ml[1]:wy0 + ml[1] + th, wx0 + ml[0]:wx0 + ml[0] + tw].sum() - Tm[max(FY0, wy0 + ml[1]):min(FY1, wy0 + ml[1] + th), max(FX0, wx0 + ml[0]):min(FX1, wx0 + ml[0] + tw)].sum()
            tw_ = Tm[FY0:FY1, FX0:FX1].sum() + out
        iou = mv / (A + tw_ - mv + 1e-6)
        if res is None or iou > res[0]:
            res = (iou, s, sx, wx0 + ml[0] - x0, wy0 + ml[1] - y0, (x0, y0, x1, y1))
    return res


from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args=['--allow-file-access-from-files'])
    page = b.new_page(viewport={'width': R.W, 'height': R.H})
    sc = [(1, 1)] if noscale else [(s, sx) for s in np.arange(float(os.environ.get('S0',0.90)), float(os.environ.get('S1',1.101)), 0.02) for sx in np.arange(float(os.environ.get('X0',0.92)), float(os.environ.get('X1',1.081)), 0.02)]
    EXCL = os.environ.get('EXCL', '1') == '1'
    alph = {}
    if EXCL:
        for j, Lj in enumerate(spec['layers']):
            alph[j] = alpha_of(page, Lj)
    for i in lay:
        L = spec['layers'][i]
        if L.get('notune'):  # 手で直した字: 自動で動かさない
            print(f'L{i} notune'); continue
        T = Tm
        if EXCL:
            oth = np.zeros_like(Tm)
            for j, a_ in alph.items():
                if j != i:
                    oth |= a_
            T = (Tm & (1 - cv2.dilate(oth, np.ones((3, 3), np.uint8)))).astype(np.uint8)
        if L.get('fit_color'):  # 縁・光彩の色を的から外し、文字の色の画素だけで合わせる
            T = (T & color_mask(L['fit_color'], L.get('fit_tol', 40))).astype(np.uint8)
        cands = [(L.get('font'), L.get('weight', 900))]
        if fonts and not is_hand(L.get('font')):  # 手書き書体の層には書体候補を掛けない（太いゴシックが混ざる）
            cands += [(f, int(w)) for f, w in fonts if (f, int(w)) != cands[0]]
        bestr = None
        rots = [None]
        if os.environ.get('ROTS'):
            rots = [float(v) for v in os.environ['ROTS'].split(',')]
        skews = [None]
        if os.environ.get('SKEWS'):
            skews = [float(v) for v in os.environ['SKEWS'].split(',')]
        cands = [(f, w, ro, sk) for f, w in cands for ro in rots for sk in skews]
        for f, w, ro, sk in cands:
            L2 = dict(L, font=f, weight=w)
            if ro is not None: L2['rotate'] = ro
            if sk is not None: L2['skew'] = sk
            r = best(alpha_of(page, L2), sc, T)
            if r is None:
                print(i, 'empty'); continue
            print(f"L{i} {L.get('text', '')[:10] if L.get('text') else ''.join(x['text'] for x in L.get('runs', []))[:10]} {f}:{w}:r{ro}:k{sk} iou={r[0]:.3f} s={r[1]:.2f} sx={r[2]:.2f} dx={r[3]} dy={r[4]}")
            if bestr is None or r[0] > bestr[0][0] + 0.01:
                bestr = (r, f, w, ro, sk)
        if apply and bestr:
            r, f, w, ro, sk = bestr
            L['font'] = f; L['weight'] = w
            if ro is not None: L['rotate'] = ro
            if sk is not None: L['skew'] = sk
            L['size'] = round(L.get('size', 80) * r[1], 1)
            L['scale_x'] = round(L.get('scale_x', 1) * r[2], 3)
            a = alpha_of(page, L)
            r2 = best(a, [(1, 1)], T)
            L['x'] = round(L['x'] + int(r2[3]), 1); L['y'] = round(L['y'] + int(r2[4]), 1)
            if EXCL:
                alph[i] = alpha_of(page, L)
            print(f"   applied {f}:{w} size={L['size']} scale_x={L['scale_x']} x={L['x']} y={L['y']} iou={r2[0]:.3f}")
    b.close()
if apply:
    json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
