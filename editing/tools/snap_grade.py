"""スナップの色を参考画像（SNS 用高画質 ローファー 02）に寄せる。
背景（明るくて色の薄い画素）の色を参考の背景色に、黒を参考の黒に合わせる（チャンネルごとの直線＋上の肩）。"""
import json, sys, glob, os
import numpy as np
from PIL import Image
REF_BG = np.array([235.0, 228.9, 217.4]); REF_BK = np.array([10.0, 10.0, 9.0])

def measure(a):
    L = a.mean(2); sat = a.max(2) - a.min(2)
    m = (L > 110) & (sat < 22)
    frac = m.mean()
    bg = a[m].mean(0) if frac > 0.25 else None  # 背景が画面の 1/4 以上ある写真だけで測る（服の寄りは服を背景と取り違える）
    bk = np.percentile(a.reshape(-1, 3), 1, axis=0)
    return bg, bk, frac

def params(files):
    out = {}
    for f in files:
        im = Image.open(f).convert('RGB'); im.thumbnail((600, 600))
        bg, bk, fr = measure(np.asarray(im, float))
        out[os.path.basename(f)] = (bg, bk, fr)
    # 背景が写っていない写真は、番号の近い写真の値を使う
    names = sorted(out)
    good = [n for n in names if out[n][0] is not None]
    res = {}
    for n in names:
        bg, bk, fr = out[n]
        if bg is None:
            k = int(n[3:8]); near = min(good, key=lambda g: abs(int(g[3:8]) - k))
            bg = out[near][0]; src = near
        else:
            src = n
        res[n] = {'bg': bg.tolist(), 'bk': bk.tolist(), 'from': src, 'frac': round(float(fr), 3)}
    return res

def grade(a, p):
    bg = np.array(p['bg']); bk = float(min(np.mean(p['bk']), 30))
    # 明るさ（背景の明るさを参考に。上げすぎない）と色の偏り（チャンネルの比）を分けて合わせる
    lum_ref, lum = REF_BG.mean() - REF_BK.mean(), max(bg.mean() - bk, 1)
    gl = float(np.clip(lum_ref / lum, 0.85, 1.35))
    wb = (REF_BG / REF_BG.mean()) / (bg / bg.mean())
    wb = np.clip(wb, 0.9, 1.1)
    x = REF_BK.mean() + (a - bk) * gl * wb
    k = 230.0
    over = np.maximum(x - k, 0)
    x = np.where(x > k, k + 25 * (1 - np.exp(-over / 25)), x)
    return np.clip(x, 0, 255)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'params':
        json.dump(params(sorted(glob.glob(sys.argv[2] + '/*.JPG'))), open(sys.argv[3], 'w'))
