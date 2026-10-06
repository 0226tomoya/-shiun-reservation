"""A19 の色味（基準ルック）に素材を合わせる .cube LUT を作る。

素材ごとに元の色（カメラ・ホワイトバランス・露出）が違うので、固定 LUT ではなく
「素材のサンプルフレーム → 基準ルック」の差分から LUT を毎回生成する。

サブコマンド:
  reference  画像/動画から基準ルックの統計を作る
      python3 look_match.py reference OUT.json INPUT... [--storyboard]
  lut        素材のサンプルから基準ルックに合わせる LUT を作る
      python3 look_match.py lut REF.json OUT.cube INPUT... [--strength 0.8] [--size 33]
  apply      LUT を画像に当ててプレビューを作る（左: 元 / 右: 適用後）
      python3 look_match.py apply LUT.cube IN_IMAGE OUT_IMAGE
  stats      画像/動画の統計を基準と比べて表示する
      python3 look_match.py stats REF.json INPUT...

INPUT は画像（jpg/png/tif）か動画（ffmpeg で均等に 24 コマ抽出）。
--storyboard を付けると YouTube ストーリーボード（320x180 のタイル画像）として分割して読む。

前提: 素材は Rec.709（ガンマ 2.4 相当）で、LOG 素材の場合は先に変換 LUT を当ててから使う。
FCP では、LUT は調整レイヤーに「カスタム LUT」エフェクトとして当てる（README 参照）。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

QS = np.linspace(0, 100, 101)
BANDS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]


# ---------- 色空間 ----------
def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


M = np.array([[0.4124564, 0.3575761, 0.1804375],
              [0.2126729, 0.7151522, 0.0721750],
              [0.0193339, 0.1191920, 0.9503041]])
MI = np.linalg.inv(M)
WP = np.array([0.95047, 1.0, 1.08883])


def rgb_to_lab(rgb):
    xyz = srgb_to_lin(rgb) @ M.T / WP
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_rgb(lab):
    fy = (lab[..., 0] + 16) / 116
    fx = fy + lab[..., 1] / 500
    fz = fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f > 0.206893, f ** 3, (f - 16 / 116) / 7.787) * WP
    return np.clip(lin_to_srgb(xyz @ MI.T), 0, 1)


# ---------- 入力 ----------
def load_frames(paths, storyboard=False, n_video=24):
    frames = []
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        if ext in ('.mp4', '.mov', '.mxf', '.m4v', '.mts'):
            with tempfile.TemporaryDirectory() as td:
                dur = float(subprocess.check_output(
                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).decode().strip())
                for k in range(n_video):
                    t = dur * (k + 0.5) / n_video
                    out = os.path.join(td, f'{k}.png')
                    subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', p, '-frames:v', '1',
                                    '-vf', 'scale=640:-2', out], check=True)
                    frames.append(np.asarray(Image.open(out).convert('RGB'), dtype=np.float32) / 255)
        else:
            im = np.asarray(Image.open(p).convert('RGB'), dtype=np.float32) / 255
            if storyboard:
                for r in range(im.shape[0] // 180):
                    for c in range(im.shape[1] // 320):
                        frames.append(im[r * 180:(r + 1) * 180, c * 320:(c + 1) * 320])
            else:
                if im.shape[1] > 960:
                    pil = Image.fromarray((im * 255).astype(np.uint8)).resize((960, int(im.shape[0] * 960 / im.shape[1])))
                    im = np.asarray(pil, dtype=np.float32) / 255
                frames.append(im)
    return frames


def usable(f):
    """真っ黒・ほぼ単色のグラフィック画面は統計から外す。"""
    lab = rgb_to_lab(f)
    med = np.median(lab[..., 0])
    return 8 < med < 85 and lab[..., 0].std() > 4


def stats(frames):
    fr = [f for f in frames if usable(f)]
    if not fr:
        raise SystemExit('統計に使えるフレームがありません')
    lab = np.concatenate([rgb_to_lab(f).reshape(-1, 3) for f in fr])
    L = lab[:, 0]
    out = {'frames': len(fr), 'L_quantiles': np.percentile(L, QS).tolist(), 'bands': []}
    for lo, hi in BANDS:
        m = (L >= lo) & (L < hi)
        sub = lab[m] if m.sum() > 100 else lab
        out['bands'].append({'L': [lo, hi], 'a_mean': float(sub[:, 1].mean()), 'b_mean': float(sub[:, 2].mean()),
                             'a_std': float(sub[:, 1].std()), 'b_std': float(sub[:, 2].std()), 'share': float(m.mean())})
    out['chroma_mean'] = float(np.hypot(lab[:, 1], lab[:, 2]).mean())
    return out


# ---------- 変換 ----------
def band_interp(stat, key, L):
    centers = np.array([(lo + min(hi, 100)) / 2 for lo, hi in BANDS])
    vals = np.array([b[key] for b in stat['bands']])
    return np.interp(L, centers, vals)


def build_transform(src, ref, strength):
    sq = np.maximum.accumulate(np.array(src['L_quantiles']))
    rq = np.maximum.accumulate(np.array(ref['L_quantiles']))
    # 端点は 0/100 に固定して黒つぶれ・白飛びを防ぐ
    sq = np.concatenate([[0], sq[1:-1], [100]])
    rq = np.concatenate([[0], rq[1:-1], [100]])
    sq = sq + np.arange(len(sq)) * 1e-6
    chroma_gain = np.clip(ref['chroma_mean'] / max(src['chroma_mean'], 1e-3), 0.6, 1.4)

    def f(lab):
        L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
        L2 = np.interp(L, sq, rq)
        # 明るさ帯ごとの色かぶり（a/b の平均）を基準に寄せる
        a2 = (a - band_interp(src, 'a_mean', L)) * chroma_gain + band_interp(ref, 'a_mean', L2)
        b2 = (b - band_interp(src, 'b_mean', L)) * chroma_gain + band_interp(ref, 'b_mean', L2)
        # 黒と白の付近は色を抜いて、締まった黒・濁らない白にする
        fade = np.clip(np.minimum(L2 / 6, (100 - L2) / 6), 0, 1)
        a2, b2 = a2 * fade, b2 * fade
        out = np.stack([L2, a2, b2], -1)
        return lab + (out - lab) * strength

    return f


def write_cube(path, fn, size, title):
    g = np.linspace(0, 1, size)
    b, gg, r = np.meshgrid(g, g, g, indexing='ij')  # .cube は R が最速で変わる
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    out = lab_to_rgb(fn(rgb_to_lab(rgb)))
    with open(path, 'w') as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
        for v in out:
            f.write(f'{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n')


def read_cube(path):
    size, rows = None, []
    for line in open(path):
        t = line.split()
        if not t or t[0].startswith('#'):
            continue
        if t[0] == 'LUT_3D_SIZE':
            size = int(t[1])
        elif len(t) == 3 and t[0][0] in '0123456789.-':
            rows.append([float(x) for x in t])
    return size, np.array(rows).reshape(size, size, size, 3)  # [b][g][r]


def apply_cube(img, size, lut):
    x = img * (size - 1)
    i0 = np.clip(np.floor(x).astype(int), 0, size - 2)
    d = x - i0
    out = np.zeros_like(img)
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (np.where(dr, d[..., 0], 1 - d[..., 0]) * np.where(dg, d[..., 1], 1 - d[..., 1]) *
                     np.where(db, d[..., 2], 1 - d[..., 2]))
                out += w[..., None] * lut[i0[..., 2] + db, i0[..., 1] + dg, i0[..., 0] + dr]
    return np.clip(out, 0, 1)


def summary(s):
    q = s['L_quantiles']
    return (f"L p5/25/50/75/95 = {q[5]:.1f}/{q[25]:.1f}/{q[50]:.1f}/{q[75]:.1f}/{q[95]:.1f}  "
            f"a,b(中間調) = {s['bands'][2]['a_mean']:.2f},{s['bands'][2]['b_mean']:.2f}  "
            f"a,b(ハイライト) = {s['bands'][3]['a_mean']:.2f},{s['bands'][3]['b_mean']:.2f}  彩度 = {s['chroma_mean']:.2f}")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('reference'); p.add_argument('out'); p.add_argument('inputs', nargs='+'); p.add_argument('--storyboard', action='store_true')
    p = sp.add_parser('lut'); p.add_argument('ref'); p.add_argument('out'); p.add_argument('inputs', nargs='+')
    p.add_argument('--strength', type=float, default=0.8); p.add_argument('--size', type=int, default=33); p.add_argument('--storyboard', action='store_true')
    p = sp.add_parser('apply'); p.add_argument('cube'); p.add_argument('inp'); p.add_argument('out')
    p = sp.add_parser('stats'); p.add_argument('ref'); p.add_argument('inputs', nargs='+'); p.add_argument('--storyboard', action='store_true')
    a = ap.parse_args()

    if a.cmd == 'reference':
        s = stats(load_frames(a.inputs, a.storyboard))
        json.dump(s, open(a.out, 'w'), indent=1)
        print(summary(s))
    elif a.cmd == 'lut':
        ref = json.load(open(a.ref))
        src = stats(load_frames(a.inputs, a.storyboard))
        print('素材 :', summary(src)); print('基準 :', summary(ref))
        write_cube(a.out, build_transform(src, ref, a.strength), a.size, os.path.splitext(os.path.basename(a.out))[0])
        print('->', a.out)
    elif a.cmd == 'apply':
        size, lut = read_cube(a.cube)
        img = np.asarray(Image.open(a.inp).convert('RGB'), dtype=np.float32) / 255
        out = apply_cube(img, size, lut)
        both = np.concatenate([img, out], 1)
        Image.fromarray((both * 255).round().astype(np.uint8)).save(a.out, quality=92)
    elif a.cmd == 'stats':
        ref = json.load(open(a.ref))
        print('基準 :', summary(ref))
        print('入力 :', summary(stats(load_frames(a.inputs, a.storyboard))))


if __name__ == '__main__':
    sys.exit(main())
