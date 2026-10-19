"""A25 のサムネ（PSD のレイヤーを書き出した L*.png から組み直す）。python3 a25_rebuild.py レイヤーのフォルダ OUT.png
   レイヤーは psd-tools で書き出す: L1=背景, L11〜L16=6 人, L17=靴"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
d = sys.argv[1]; out = sys.argv[2]
W, H = 1280, 720
F = '/root/.fonts/'
BROWN = (122, 72, 30)
INK = (24, 20, 18)

# 背景: 元の背景の紙色を取って、中央を少し明るくしたクリームの無地（靴の写真のぼけを入れない）
src = Image.open(f'{d}/L1.png').convert('RGB')
c = np.array(src.crop((0, 0, 300, 300))).reshape(-1, 3).mean(0)
yy, xx = np.mgrid[0:H, 0:W]
r = np.sqrt(((xx - W * 0.45) / W) ** 2 + ((yy - H * 0.35) / H) ** 2)
bg = np.clip(c[None, None, :] * (1.06 - 0.12 * r[..., None]), 0, 255).astype('uint8')
im = Image.fromarray(bg).convert('RGBA')

def font(n, s): return ImageFont.truetype(F + n, s)

# 人物: 6 人を横いっぱいに等間隔。足元まで見せる（下端に足）
order = [11, 16, 15, 12, 14, 13]
for i, k in enumerate(order):
    p = Image.open(f'{d}/L{k}.png')
    if k == 16:
        p = p.crop((150, 0, p.width, p.height))  # 左の白い点（キラキラ）を外す
    p = p.crop(p.getbbox())
    p = p.resize((int(p.width * 0.9), int(p.height * 0.9)), Image.LANCZOS)
    cx = int(W * (i + 0.5) / 6)
    y = H - p.height + 2
    # 足元の影
    sh = Image.new('RGBA', (W, H), 0); ImageDraw.Draw(sh).ellipse((cx - 70, H - 14, cx + 70, H + 10), fill=(60, 40, 25, 70))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(8)))
    im.alpha_composite(p, (cx - p.width // 2, y))

# 靴: 右上。人の頭にかからない大きさ・位置。床の影を 1 つだけ
shoe = Image.open(f'{d}/L17.png'); shoe = shoe.crop(shoe.getbbox())
s = 0.62; shoe = shoe.resize((int(shoe.width * s), int(shoe.height * s)), Image.LANCZOS)
sx, sy = W - shoe.width - 28, 18
sh = Image.new('RGBA', (W, H), 0)
ImageDraw.Draw(sh).ellipse((sx + 20, sy + shoe.height - 18, sx + shoe.width - 10, sy + shoe.height + 10), fill=(50, 30, 15, 120))
im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10)))
im.alpha_composite(shoe, (sx, sy))

dr = ImageDraw.Draw(im)
def run(x, y, parts):
    """[(文字, フォント, 色, 下げ)] を 1 行に並べる（ベースラインをそろえる）"""
    for t, f, col, dy in parts:
        dr.text((x, y + dy), t, font=f, fill=col, anchor='ls')
        x += dr.textlength(t, font=f) - (4 if f.size > 100 else 0)
    return x

# かかとの「+6cm」の矢印（上向き）
hx, hy0, hy1 = sx + 40, sy + shoe.height - 8, sy + 70


# 見出し（左上）。かなは小さく、数字は大きく、差し色は茶 1 色
M = font('ShipporiMinchoB1-800.ttf', 1)
mf = lambda s: font('ShipporiMinchoB1-800.ttf', s)
num = font('PlayfairDisplay-900.ttf', 128)
# 1 行目の上の肩書き（黒の札に白字）
tag = '164cmの低身長が本気で選んだ'
tf = font('NotoSansJP-900.ttf', 28)
tw = dr.textlength(tag, font=tf)
dr.rectangle((34, 16, 34 + tw + 24, 58), fill=INK)
dr.text((46, 50), tag, font=tf, fill=(250, 246, 238), anchor='ls')
run(30, 168, [('背が', mf(64), INK, 0), ('+6cm', num, BROWN, 6), ('盛れる', mf(78), INK, 0)])
run(30, 262, [('茶色', mf(104), INK, 0), ('の', mf(66), INK, 0), ('革靴', mf(104), INK, 0)])
# 英字のサブ
dr.text((sx + shoe.width // 2 + 10, sy + shoe.height + 46), 'Brown Leather Shoes  ×  6 Coordinates', font=font('BodoniModa-700.ttf', 26), fill=INK, anchor='ms')
# shiun のロゴ（黒）を英字の左に小さく
logo = Image.open('/home/user/-shiun-reservation/editing/thumbs/assets/logos/shiun_black.png').convert('RGBA')
logo = logo.crop(logo.getbbox()); lh = 30; logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
im.alpha_composite(logo, (W - logo.width - 30, 14))
im.convert('RGB').save(out)
print('saved', out)
