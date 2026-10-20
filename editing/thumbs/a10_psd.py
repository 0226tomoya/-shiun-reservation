"""A10 サムネの改善（ややシンプルに、テンションはそのまま）。元の PSD を土台に、文字は打ち直せるまま残す。
    python3 a10_psd.py src.psd OUT.psd [OUT.png]
v1: 後ろの大きな ○×（グループ 1）を消し、デニムの上に小さくはっきりした ○（白）×（赤）を置く／黒い塗りを 50% → 30%／下だけ暗くするグラデーション
v2（ユーザーの指示）: ○× は元のデザインのまま（はっきりさせるとカジュアルになる。デザインで留める）。
    黒い塗りは背景だけに掛かっていて人物は明るくならない（背景が明るいと ○× と人物が沈む）ので元の 50% に戻す。残すのは下のグラデーションだけ
    python3 a10_psd.py src.psd OUT.psd OUT.png --v1   … v1 を作り直すとき"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psd_edit import Editor

src, out = sys.argv[1], sys.argv[2]
W, H = 1280, 720
RED = (226, 36, 36)        # 右上の矢印と同じ赤
V1 = '--v1' in sys.argv
LAY = dict(FILL=77 if V1 else 128,   # 黒い塗りの濃さ（0〜255。元は 128）
           GRAD_FROM=380, GRAD_MAX=150,   # 下のグラデーション: この高さから下へ、最大の濃さ
           O=(300, 285), X=(1030, 290), R=100, STROKE=26)   # ○×の中心・半径・線の太さ
SS = 4  # なめらかに描くための拡大率


def mark(kind):
    """○ か × を、白い縁と影つきで描く（キャンバス大）"""
    big = Image.new('RGBA', (W * SS, H * SS), 0); d = ImageDraw.Draw(big)
    cx, cy = (LAY['O'] if kind == 'o' else LAY['X']); r, t = LAY['R'] * SS, LAY['STROKE'] * SS
    cx, cy = cx * SS, cy * SS
    if kind == 'o':
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 255), width=t)
    else:
        k = r * 0.78
        for sgn in (1, -1):
            d.line((cx - k, cy - k * sgn, cx + k, cy + k * sgn), fill=RED + (255,), width=t)
        for sgn in (1, -1):   # 線の端を丸く
            for ex, ey in ((cx - k, cy - k * sgn), (cx + k, cy + k * sgn)):
                d.ellipse((ex - t / 2, ey - t / 2, ex + t / 2, ey + t / 2), fill=RED + (255,))
    img = big.resize((W, H), Image.LANCZOS)
    # × は白い縁（黒いデニムの上でも形が立つ）
    if kind == 'x':
        a = img.getchannel('A').filter(ImageFilter.MaxFilter(9))
        rim = Image.new('RGBA', (W, H), (255, 255, 255, 0)); rim.putalpha(a)
        rim.alpha_composite(img); img = rim
    # 影
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh.putalpha(img.getchannel('A').point(lambda v: v * 0.45).filter(ImageFilter.GaussianBlur(10)))
    base = Image.new('RGBA', (W, H), 0); base.alpha_composite(sh, (0, 6)); base.alpha_composite(img)
    return base


def gradient():
    yy = np.arange(H)[:, None] * np.ones((1, W))
    a = (np.clip((yy - LAY['GRAD_FROM']) / (H - LAY['GRAD_FROM']), 0, 1) ** 1.4 * LAY['GRAD_MAX']).astype('uint8')
    g = np.zeros((H, W, 4), 'uint8'); g[..., :3] = (18, 13, 10); g[..., 3] = a
    return Image.fromarray(g)


ed = Editor(src)
ed.find('べた塗り 1').opacity = LAY['FILL']          # 黒い塗り
txt = ed.find('グループ 2')
ed.add(gradient(), '下のグラデーション（文字を読みやすく）', before=txt)
if V1:
    ed.find('グループ 1').visible = False             # 後ろの大きな ○×
    ed.add(mark('o'), '○（左のデニム・白）', before=txt)
    ed.add(mark('x'), '×（右のデニム・赤＋白縁）', before=txt)
q = ed.save(out)
print('saved', out)
if len(sys.argv) > 3 and not sys.argv[3].startswith('--'):
    q.composite(force=True).convert('RGB').save(sys.argv[3])
