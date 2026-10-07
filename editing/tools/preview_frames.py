"""編集データの指定時刻の画面を、型の位置計算で描いた静止画プレビューにする（素材は枠で代用）。

    python3 preview_frames.py FLAT.json OUT.png 秒 [秒 ...]

テロップは FCP の値（位置 = 中央原点 px、変形 = 画面の高さの 1%、拡大、縦 140%）から描く。
フォントは近いもの（欧文: Noto Serif、和文: Noto Sans CJK）で代用するので、字幅は目安。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role, text, first_style, pos, tr  # noqa: E402

W, H = 1920, 1080
SERIF = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'
SANS = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def font(path, size):
    try:
        return ImageFont.truetype(path, max(8, int(size)))
    except OSError:
        return ImageFont.load_default()


def draw_title(im, i):
    st = first_style(i)
    (px, py), sc = pos(i), tr(i)[1]
    (tx, ty) = tr(i)[0]
    x = W / 2 + px * sc + tx * 10.8
    y = H / 2 - (py * sc + ty * 10.8)
    stretch = float((i.get('params', {}).get('調整') or '1 1').split()[1])
    size = float(st.get('fontSize') or 30) * sc
    is_jp = st.get('font') in ('Klee', 'Hiragino Mincho ProN')
    f = font(SANS if is_jp else SERIF, size * (0.95 if is_jp else 0.8))
    col = tuple(int(float(c) * 255) for c in (st.get('fontColor') or '1 1 1 1').split()[:3])
    lines = text(i).strip('\n').split('\n')
    al = st.get('alignment') or ('center' if '中央' in str(i.get('params', {}).get('配置', '')) else
                                 'right' if '右' in str(i.get('params', {}).get('配置', '')) else 'left')
    lh = size * 1.25 * stretch
    total = lh * len(lines)
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for k, line in enumerate(lines):
        w = d.textlength(line, font=f)
        lx = {'center': x - w / 2, 'right': x - w}.get(al, x)
        ly = y - total / 2 + k * lh
        # 縦 140% を近似: 1 行ずつ縦に伸ばして貼る
        tmp = Image.new('RGBA', (int(w) + 4, int(size * 1.4) + 4), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((2, 0), line, font=f, fill=col + (255,), stroke_width=1 if is_jp else 0, stroke_fill=(0, 0, 0, 60))
        tmp = tmp.resize((tmp.width, int(tmp.height * stretch)))
        layer.alpha_composite(tmp, (int(lx), int(ly)))
    im.alpha_composite(layer)


def draw_media(im, i, label):
    p, sc = tr(i)
    s = sc or 1
    # 写真は縦長（2:3）を高さ合わせ、動画は全画面として近似
    if i['tag'] == 'video':
        h = H * s
        w = h * 2 / 3 if s < 2 else W * s
    else:
        w, h = W * s, H * s
    cx, cy = W / 2 + p[0] * 10.8, H / 2 - p[1] * 10.8
    blur = any(f['name'] == 'ガウス' for f in i.get('filters', []))
    d = ImageDraw.Draw(im)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    d.rectangle(box, fill=(70, 80, 72, 255) if not blur else (95, 95, 100, 255), outline=(150, 160, 150, 255), width=3)
    d.text((max(box[0], 0) + 12, max(box[1], 0) + 12), label, fill=(210, 220, 210, 255), font=font(SANS, 22))


def render(items, t):
    im = Image.new('RGBA', (W, H), (176, 172, 162, 255))  # 白壁のグレー（A19 の実測）
    d = ImageDraw.Draw(im)
    d.text((W - 360, H - 50), 'メインカメラ（トーク）', fill=(110, 105, 95, 255), font=font(SANS, 26))
    act = [i for i in items if i['t0'] <= t < i['t1'] and i['tag'] != 'mc-clip' and i['lane'] not in (None, '-1')
           and role(i) not in ('adjustment_main', 'adjustment_other') and not str(i['lane']).startswith('in')]
    act.sort(key=lambda i: int(i['lane']) if str(i['lane']).lstrip('-').isdigit() else 0)
    for i in act:
        if i['tag'] == 'title':
            draw_title(im, i)
        else:
            draw_media(im, i, (i['name'] or '')[:30] + ('（ぼかし）' if any(f['name'] == 'ガウス' for f in i.get('filters', [])) else ''))
    for i in items:
        if i['t0'] <= t < i['t1'] and i['lane'] is None and i['tag'] in ('ref-clip', 'asset-clip') and i['name'] != 'BGM':
            d.rectangle((0, 0, W, H), fill=(30, 30, 30, 255))
            d.text((60, 60), f'{i["name"]}（挿入素材）', fill='white', font=font(SANS, 40))
    return im.convert('RGB')


def main():
    items = [i for i in json.load(open(sys.argv[1])) if i['enabled'] != '0' and len(i['path']) <= 1]
    times = [float(x) for x in sys.argv[3:]]
    tiles = []
    for t in times:
        im = render(items, t).resize((960, 540))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 150, 30), fill='black')
        d.text((8, 4), f'{int(t // 60)}:{t % 60:04.1f}', fill='yellow', font=font(SANS, 20))
        tiles.append(im)
    cols = 2
    out = Image.new('RGB', (960 * cols, 540 * ((len(tiles) + cols - 1) // cols)), 'black')
    for k, im in enumerate(tiles):
        out.paste(im, ((k % cols) * 960, (k // cols) * 540))
    out.save(sys.argv[2], quality=85)


if __name__ == '__main__':
    main()
