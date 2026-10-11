"""文字レイヤーを元のサムネの文字に合わせて自動で詰める（位置・大きさ・横の伸び・字間・傾き）。

    python3 fit.py SPEC.json [--layers 1,2]

手順（レイヤーごと）:
 1. 元の文字の形: レイヤーの範囲（box か、重なる erase）の中で、レイヤーの色（縁取りがあれば一番外の色、なければ文字色）に近い画素
 2. 描いた形（不透明な部分）と外接矩形を合わせて大きさ・横の伸び・位置の初期値を出す
 3. 二つの形の重なり（IoU）が最大になるよう x, y, size, scale_x, spacing, rotate を座標ごとに詰める
結果は SPEC.json に上書き（各レイヤーに "fit_iou" を書く）。
"split": true の行は 1 行で合わせた後に 1 文字ずつのレイヤーに分ける（もう一度 fit.py を流すと 1 文字ずつ詰める）。
縁取りの色が背景に紛れるときは、レイヤーに "fit_color": "#文字色" を書くとその色で合わせる。"lock": ["rotate",…] で動かさない値を指定。
"""
import copy
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402


def target_mask(orig, L, box, tol):
    x0, y0, x1, y1 = box
    lab = cv2.cvtColor(orig[y0:y1, x0:x1], cv2.COLOR_BGR2LAB).astype(np.float32)
    cols = []
    if L.get('fit_color'):
        cols.append(L['fit_color'])
    elif L.get('strokes'):
        cols.append(L['strokes'][-1][1])
    else:
        sp = {'layers': [L]}
        cols += [c for c in R.layer_colors(sp)]
        cols = [c if isinstance(c, str) else '#%02x%02x%02x' % (int(c[2]), int(c[1]), int(c[0])) for c in cols]
    m = np.zeros(lab.shape[:2], bool)
    for c in cols:
        b = R.hex2bgr(c) if isinstance(c, str) else c
        if b is None:
            continue
        cl = cv2.cvtColor(np.uint8([[b]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
        m |= np.linalg.norm(lab - cl, axis=2) < tol
    full = np.zeros(orig.shape[:2], bool)
    full[y0:y1, x0:x1] = m
    return full


def main():
    from playwright.sync_api import sync_playwright
    sp = sys.argv[1]
    spec = json.load(open(sp))
    orig = cv2.resize(cv2.imread(os.path.join(os.environ['THUMB_ORIG'], spec['id'] + '.jpg')), (R.W, R.H))
    only = [int(v) for v in sys.argv[sys.argv.index('--layers') + 1].split(',')] if '--layers' in sys.argv else None
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
        page = b.new_page(viewport={'width': R.W, 'height': R.H})

        clipbox = [None]

        def alpha_of(L):
            return R.render_layers({'layers': [L]}, page, clip=clipbox[0])[:, :, 3] > 128

        pending_split = []
        for i, L in enumerate(spec['layers']):
            if L['type'] != 'text' or (only and i not in only) or L.get('fixed'):
                continue
            a = alpha_of(L)
            ys, xs = np.where(a)
            if not len(xs):
                continue
            if L.get('box'):
                bx, by, bw, bh = L['box']
                box = [int(bx), int(by), int(bx + bw), int(by + bh)]
            else:
                # 描いた範囲と重なりが一番大きい erase
                best, box = 0, None
                for e in spec.get('erase', []):
                    x, y, w, h = e['rect'] if isinstance(e, dict) else e
                    ov = max(0, min(xs.max(), x + w) - max(xs.min(), x)) * max(0, min(ys.max(), y + h) - max(ys.min(), y))
                    if ov > best:
                        best, box = ov, [int(x), int(y), int(x + w), int(y + h)]
                if box is None:
                    pad = 30
                    box = [max(0, xs.min() - pad), max(0, ys.min() - pad), min(R.W, xs.max() + pad), min(R.H, ys.max() + pad)]
            box = [max(0, box[0]), max(0, box[1]), min(R.W, box[2]), min(R.H, box[3])]
            T = target_mask(orig, L, box, L.get('tol', 30))
            # 以後は box を少し広げた範囲だけ撮る（はみ出した分は数えない＝ box を正しく取ること）
            m_ = 60
            clipbox[0] = [max(0, box[0] - m_), max(0, box[1] - m_), min(R.W, box[2] + m_), min(R.H, box[3] + m_)]
            if T.sum() < 50:
                print(f'レイヤー {i}: 元の文字の色が見つからない（色か box を確認）')
                continue
            ty, tx = np.where(T)
            tb = [tx.min(), ty.min(), tx.max(), ty.max()]

            def iou(Lc):
                A = alpha_of(Lc)
                inter = (A & T).sum()
                uni = (A | T).sum()
                return inter / uni if uni else 0

            # 初期値: 外接矩形を合わせる（回転していない前提で大きさ→位置）
            if not L.get('no_init'):
                for _ in range(2):
                    a = alpha_of(L)
                    ys, xs = np.where(a)
                    ab = [xs.min(), ys.min(), xs.max(), ys.max()]
                    sh = (tb[3] - tb[1]) / max(1, ab[3] - ab[1])
                    sw = (tb[2] - tb[0]) / max(1, ab[2] - ab[0])
                    L = copy.deepcopy(L)
                    L['size'] = round(L.get('size', 80) * sh, 2)
                    L['scale_x'] = round(L.get('scale_x', 1) * sw / sh, 3)
                    a = alpha_of(L)
                    ys, xs = np.where(a)
                    ab = [xs.min(), ys.min(), xs.max(), ys.max()]
                    L['x'] = round(L['x'] + (tb[0] - ab[0] + tb[2] - ab[2]) / 2, 1)
                    L['y'] = round(L['y'] + (tb[1] - ab[1] + tb[3] - ab[3]) / 2, 1)
            best = iou(L)
            steps = [('x', [6, 2, 0.5]), ('y', [6, 2, 0.5]), ('size', [0.04, 0.012, 0.004]), ('scale_x', [0.04, 0.012, 0.004]),
                     ('spacing', [0.02, 0.006, 0.002]), ('rotate', [1.5, 0.5, 0.15]), ('skew', [3, 1, 0.3])]
            for r in range(3):
                for k, st in steps:
                    if k in L.get('lock', []):
                        continue
                    d = st[r]
                    while True:
                        moved = False
                        for sgn in (1, -1):
                            Lc = copy.deepcopy(L)
                            cur = Lc.get(k, {'size': 80, 'scale_x': 1}.get(k, 0))
                            Lc[k] = round(cur * (1 + sgn * d), 3) if k == 'size' else round(cur + sgn * d, 4)
                            v = iou(Lc)
                            if v > best + 1e-4:
                                best, L, moved = v, Lc, True
                                break
                        if not moved:
                            break
            clipbox[0] = None
            L['fit_iou'] = round(float(best), 3)
            spec['layers'][i] = L
            if L.get('split') and L.get('text') and len(L['text'].replace('\n', '')) > 1:
                pending_split.append(i)
            print(f'レイヤー {i}「{(L.get("text") or "".join(r["text"] for r in L.get("runs", [])))[:12]}」 IoU {best:.3f}')
        # "split": true の行は、1 行で合わせた後に 1 文字ずつのレイヤーに分け、大きさの初期化なし・横の伸び固定で詰め直す
        for i in reversed(pending_split):
            L = spec['layers'][i]
            chars = [c for c in L['text'] if c != '\n']
            L2 = copy.deepcopy(L)
            L2['runs'] = [{'text': c} for c in chars]
            L2.pop('text', None)
            R.render_layers({'layers': [L2]}, page)
            rects = page.evaluate("""() => [...document.querySelectorAll('#L0 > div:last-child span')].map(e => {
                const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })""")
            blk = page.evaluate("() => { const r = document.querySelector('#L0 > div:last-child').getBoundingClientRect(); return [r.left, r.top]; }")
            new = []
            for c, (rx, ry, rw, rh) in zip(chars, rects):
                C = {k: v for k, v in L.items() if k not in ('text', 'split', 'fit_iou', 'box')}
                C.update({'text': c, 'anchor': 'lt', 'x': round(rx, 1), 'y': round(blk[1], 1), 'no_init': True,
                          'lock': sorted(set(L.get('lock', [])) | {'scale_x', 'rotate', 'skew', 'spacing'}), 'spacing': 0})
                new.append(C)
            spec['layers'][i:i + 1] = new
            for j in range(i, i + len(new)):
                C = spec['layers'][j]
                a = alpha_of(C)
                ys, xs = np.where(a)
                if not len(xs):
                    continue
                pad = 12
                C['box'] = [int(xs.min() - pad), int(ys.min() - pad), int(xs.max() - xs.min() + 2 * pad), int(ys.max() - ys.min() + 2 * pad)]
            json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
            print(f'レイヤー {i} を {len(new)} 文字に分けた → もう一度 fit.py を実行して 1 文字ずつ詰める')
        b.close()
    json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
