"""サムネに黄金比のグリッド（0.382 / 0.618）と黄金螺旋（Photoshop の切り抜きの「黄金螺旋」と同じく枠に合わせて伸ばす）を重ねる。
    python3 golden_overlay.py IN.png OUT.png [向き 0-3]
向き: 0 = 目が右下, 1 = 左下, 2 = 右上, 3 = 左上。目（螺旋の収束点）の座標を表示する"""
import sys, math
from PIL import Image, ImageDraw

PHI = (1 + 5 ** .5) / 2


def spiral(W, H, orient=0, n=10):
    """黄金長方形（幅 PHI・高さ 1）を正方形で切っていき、四分円をつないだ点列と目を返す（枠に合わせて伸ばす）"""
    x, y, w, h = 0.0, 0.0, PHI, 1.0
    pts = []
    for i in range(n):
        k = i % 4
        if k == 0:   # 左に正方形
            s = h; cx, cy, a0 = x + s, y + s, 180; x += s; w -= s
        elif k == 1:  # 上に正方形
            s = w; cx, cy, a0 = x, y + s, 270; y += s; h -= s
        elif k == 2:  # 右に正方形
            s = h; cx, cy, a0 = x + w - s, y, 0; w -= s
        else:        # 下に正方形
            s = w; cx, cy, a0 = x + s, y + h - s, 90; h -= s
        for t in range(0, 91, 3):
            a = math.radians(a0 + t); pts.append((cx + s * math.cos(a), cy + s * math.sin(a)))
    eye = (x + w / 2, y + h / 2)
    def f(p):
        u, v = p[0] / PHI, p[1]
        if orient in (1, 3): u = 1 - u
        if orient in (2, 3): v = 1 - v
        return (u * W, v * H)
    return [f(p) for p in pts], f(eye)


if __name__ == '__main__':
    im = Image.open(sys.argv[1]).convert('RGB'); W, H = im.size
    o = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    d = ImageDraw.Draw(im)
    for fx in (1 - 1 / PHI, 1 / PHI):
        d.line((fx * W, 0, fx * W, H), fill=(0, 160, 255), width=1); d.line((0, fx * H, W, fx * H), fill=(0, 160, 255), width=1)
    pts, eye = spiral(W, H, o)
    d.line(pts, fill=(255, 40, 40), width=2)
    d.ellipse((eye[0] - 6, eye[1] - 6, eye[0] + 6, eye[1] + 6), outline=(255, 40, 40), width=2)
    im.save(sys.argv[2]); print('eye', [round(v) for v in eye])
