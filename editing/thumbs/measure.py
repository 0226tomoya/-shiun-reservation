"""元のサムネの中で、指定の色に近い画素の外接矩形を出す（fit を使わずに文字の位置・高さを測る）。

    python3 measure.py ID x y w h '#ffffff' [tol]
出力: その色の画素の外接矩形（x0 y0 x1 y1）と、横方向の切れ目（文字のかたまりの区切り）。
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

vid, x, y, w, h, col = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
tol = float(sys.argv[7]) if len(sys.argv) > 7 else 25
img = cv2.resize(cv2.imread(os.path.join(os.environ['THUMB_ORIG'], vid + '.jpg')), (R.W, R.H))
lab = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2LAB).astype(np.float32)
c = cv2.cvtColor(np.uint8([[R.hex2bgr(col)]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
m = np.linalg.norm(lab - c, axis=2) < tol
ys, xs = np.where(m)
if not len(xs):
    print('その色の画素なし')
    sys.exit()
print('外接矩形', x + xs.min(), y + ys.min(), x + xs.max(), y + ys.max(), '高さ', ys.max() - ys.min() + 1, '画素数', len(xs))
col_has = m.any(axis=0)
runs, start = [], None
for i, v in enumerate(col_has):
    if v and start is None:
        start = i
    if not v and start is not None:
        runs.append((x + start, x + i - 1))
        start = None
if start is not None:
    runs.append((x + start, x + len(col_has) - 1))
print('横のかたまり', runs[:40])
