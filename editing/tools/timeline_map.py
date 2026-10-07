"""編集データのタイムラインを 1 枚の図にする（区間・B-roll・字幕・ラベル・テロップの配置を確認する用）。

    python3 timeline_map.py FLAT.json OUT.png [タイトル]
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role  # noqa: E402

ROWS = [('チャプター', None), ('メイン（カット）', '#8a8f98'), ('調整レイヤー', '#b9a27a'), ('商品名ラベル', '#5b6b8c'),
        ('B-roll 写真', '#4f8a6b'), ('B-roll 動画', '#2f6f8f'), ('アイキャッチ等', '#a0522d'), ('セクションラベル', '#7a5c99'),
        ('字幕', '#c0504d'), ('中央商品名・価格', '#d08c2e'), ('身長別比較', '#999999')]


def font(size):
    for p in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
              '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    it = [i for i in json.load(open(sys.argv[1])) if i['enabled'] != '0' and len(i['path']) <= 1]
    total = max(i['t1'] for i in it)
    W, left, rh, top = 2400, 190, 34, 60
    H = top + rh * len(ROWS) + 40
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    f, fs = font(18), font(14)
    d.text((10, 14), sys.argv[3] if len(sys.argv) > 3 else os.path.basename(sys.argv[1]), fill='black', font=font(22))
    x = lambda t: left + (W - left - 20) * t / total
    for r, (name, _) in enumerate(ROWS):
        y = top + r * rh
        d.text((10, y + 7), name, fill='black', font=f)
        d.line((left, y + rh, W - 20, y + rh), fill='#eeeeee')
    for m in range(0, int(total) + 1, 60):
        d.line((x(m), top - 6, x(m), H - 30), fill='#f0f0f0')
        d.text((x(m) + 2, H - 28), f'{m // 60}分', fill='#888888', font=fs)

    def bar(row, t0, t1, color):
        y = top + row * rh
        d.rectangle((x(t0), y + 6, max(x(t0) + 1, x(t1)), y + rh - 6), fill=color)

    for i in it:
        r = role(i) if i['tag'] == 'title' else None
        for m in i.get('markers', []):
            if m['tag'] == 'chapter-marker':
                pass
        if i['tag'] == 'mc-clip':
            bar(1, i['t0'], i['t1'], ROWS[1][1])
        elif r == 'adjustment_main':
            bar(2, i['t0'], i['t1'], ROWS[2][1])
        elif r == 'product_label':
            bar(3, i['t0'], i['t1'], ROWS[3][1])
        elif i['tag'] == 'video' and i['lane'] not in (None, '-1'):
            bar(4, i['t0'], i['t1'], ROWS[4][1])
        elif i['tag'] in ('asset-clip', 'clip') and i['lane'] not in (None, '-1'):
            bar(5, i['t0'], i['t1'], ROWS[5][1])
        elif i['tag'] in ('ref-clip', 'asset-clip') and i['lane'] is None:
            bar(6, i['t0'], i['t1'], ROWS[6][1])
        elif r == 'section_label':
            bar(7, i['t0'], i['t1'], ROWS[7][1])
        elif r == 'subtitle':
            bar(8, i['t0'], i['t1'], ROWS[8][1])
        elif r in ('product_center', 'ed_product_name', 'collection_label_center'):
            bar(9, i['t0'], i['t1'], ROWS[9][1])
        elif r and r.startswith('size_'):
            bar(10, i['t0'], i['t1'], ROWS[10][1])
    # チャプター
    seen = set()
    for i in it:
        for m in i.get('markers', []):
            if m['tag'] == 'chapter-marker' and m['value'] not in seen:
                seen.add(m['value'])
                from fractions import Fraction
                t = i['src_t0'] + float(Fraction(m['start'].rstrip('s'))) - 0  # 近似（クリップ先頭基準）
                t = i['t0']
                d.line((x(t), top, x(t), H - 30), fill='#333333', width=2)
                d.text((x(t) + 4, top + 6), m['value'], fill='#333333', font=fs)
    im.save(sys.argv[2])


if __name__ == '__main__':
    main()
