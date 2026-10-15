"""1 行の字幕を日本語の PP-OCRv3 で読む（文字の範囲は白い画素から決める）"""
import os, numpy as np, cv2, onnxruntime as ort
D = os.path.dirname(os.path.abspath(__file__))
_s = ort.InferenceSession(os.path.join(D, 'model.onnx'))
_d = ['blank'] + [l.rstrip('\n') for l in open(os.path.join(D, 'dict.txt'), encoding='utf-8')] + [' ']


def read_line(gray, thr=200):
    m = gray > thr
    ys, xs = np.where(m)
    if len(xs) < 30:
        return ''
    y0, y1 = max(0, ys.min() - 6), min(gray.shape[0], ys.max() + 7)
    x0, x1 = max(0, xs.min() - 8), min(gray.shape[1], xs.max() + 9)
    crop = gray[y0:y1, x0:x1]
    h, w = crop.shape
    nw = max(16, int(w * 48 / h))
    img = cv2.resize(crop, (nw, 48)).astype(np.float32) / 255.0
    img = np.stack([img] * 3, 0)
    img = (img - 0.5) / 0.5
    out = _s.run(None, {'x': img[None]})[0][0]
    idx = out.argmax(1)
    res, prev = [], -1
    for i in idx:
        if i != prev and i != 0:
            res.append(_d[i] if i < len(_d) else '')
        prev = i
    return ''.join(res).strip()
