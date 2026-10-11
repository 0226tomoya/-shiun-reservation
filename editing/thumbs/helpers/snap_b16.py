"""text レイヤーの "m":[x,y,w,h,'#色',tol] で元画像の文字の外接矩形を測り、
描いた文字（塗りだけ）の外接矩形が合うよう size・scale_x・x・y を直す（fit.py の代わりの軽い計算）。
"m" の後ろに 'noscale' を足すと size/scale_x は変えず位置だけ。"""
import json, os, sys
import cv2, numpy as np
sys.path.insert(0, '/home/user/-shiun-reservation/editing/thumbs')
import render as R
ORIG = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs'

def target(img, m):
    x, y, w, h, col = m[:5]
    tol = m[5] if len(m) > 5 and not isinstance(m[5], str) else 30
    lab = cv2.cvtColor(img[y:y+h, x:x+w], cv2.COLOR_BGR2LAB).astype(np.float32)
    c = cv2.cvtColor(np.uint8([[R.hex2bgr(col)]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
    mk = (np.linalg.norm(lab - c, axis=2) < tol).astype(np.uint8)
    mk = cv2.morphologyEx(mk, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    ys, xs = np.where(mk)
    if not len(xs): return None
    # 外れ値を少し落とす
    x0, x1 = np.percentile(xs, [0.05, 99.95]); y0, y1 = np.percentile(ys, [0.05, 99.95])
    return [x + x0, y + y0, x + x1 + 1, y + y1 + 1]

def bbox(page, L):
    L2 = {k: v for k, v in L.items() if k not in ('strokes', 'shadow', 'hollow', 'opacity')}
    L2['color'] = '#ff0000'; L2.pop('fill', None); L2['x'] = L2['x'] + 640; L2['y'] = L2['y'] + 360
    if L2.get('runs'):
        L2['runs'] = [{k: v for k, v in r.items() if k not in ('color', 'fill')} for r in L2['runs']]
    im = R.render_layers({'layers': [L2]}, page)
    a = im[:, :, 3] > 128
    ys, xs = np.where(a)
    if not len(xs): return None
    return [xs.min() - 640, ys.min() - 360, xs.max() + 1 - 640, ys.max() + 1 - 360]

def main():
    from playwright.sync_api import sync_playwright
    sp = sys.argv[1]
    spec = json.load(open(sp))
    img = cv2.resize(cv2.imread(os.path.join(ORIG, spec['id'] + '.jpg')), (R.W, R.H))
    R.W, R.H = 2560, 1440
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
        page = b.new_page(viewport={'width': 2560, 'height': 1440})
        for i, L in enumerate(spec['layers']):
            if L.get("type") != "text" or ("m" not in L and "tgt" not in L): continue
            t = L.get('tgt') or target(img, L['m'])
            if t is None: print(i, 'no target'); continue
            t = [float(v) for v in t]
            nos = "noscale" in L.get("m", [])
            for it in range(3):
                r = bbox(page, L)
                if r is None: break
                rw, rh = r[2]-r[0], r[3]-r[1]; tw, th = t[2]-t[0], t[3]-t[1]
                if not nos:
                    fs = th / rh; fx = (tw / rw) / fs
                    L['size'] = round(L['size'] * fs, 1)
                    L['scale_x'] = round(L.get('scale_x', 1) * fx, 3)
                    r = bbox(page, L); rw, rh = r[2]-r[0], r[3]-r[1]
                L['x'] = round(L['x'] + (t[0]+t[2])/2 - (r[0]+r[2])/2, 1)
                L['y'] = round(L['y'] + (t[1]+t[3])/2 - (r[1]+r[3])/2, 1)
            r = bbox(page, L)
            print(i, L.get('text', '')[:12].replace('\n', '/') or 'runs', 'tgt', [int(v) for v in t], 'now', [int(v) for v in r], 'size', L['size'], 'sx', L.get('scale_x'))
        b.close()
    json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
main()
