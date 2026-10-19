"""A25 サムネ v2（雑誌の表紙の型。雰囲気優先）"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
d, out = sys.argv[1], sys.argv[2]
W, H = 1280, 720
F = '/root/.fonts/'
INK = (28, 24, 21)
BROWN = (120, 70, 29)
f = lambda n, s: ImageFont.truetype(F + n, s)

# 紙: 原案の背景（無地のクリーム）＋ごく弱い粒子と周辺減光
bg = Image.open(f'{d}/L1.png').crop((1106, 0, 2386, 720)).convert('RGB')
a = np.asarray(bg).astype(float)
yy, xx = np.mgrid[0:H, 0:W]
r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.75)) ** 2)
a *= (1.02 - 0.10 * np.clip(r, 0, 1.4) ** 2)[..., None]
im = Image.fromarray(np.clip(a, 0, 255).astype('uint8')).convert('RGBA')

# 奥の大きな筆記体「Coordinate」（原案の文字レイヤーの画、薄く）
co = Image.open(f'{d}/T_Coordinate.png')
co.putalpha(co.getchannel('A').point(lambda v: int(v * 0.55)))
im.alpha_composite(co, (-63, 60))

# 6 人（原案の位置・重なりのまま）
for k, (x, y) in {11: (142, 170), 16: (165, 171), 15: (498, 170), 12: (656, 170), 14: (824, 170), 13: (980, 170)}.items():
    p = Image.open(f'{d}/L{k}.png')
    if k == 16:
        al = p.getchannel('A'); al.paste(0, (0, 0, 150, 120)); p.putalpha(al)  # 浮いた白い点を消す
    im.alpha_composite(p, (x, y + 10))

# 人の足元を紙になじませる（下の方を紙色へ薄くフェード）
fade = Image.new('RGBA', (W, H), 0)
fa = np.zeros((H, W, 4), 'uint8'); fa[..., :3] = np.asarray(bg)[..., :3]
fa[..., 3] = (np.clip((yy - 560) / 160, 0, 1) * 150).astype('uint8')
im = Image.alpha_composite(im, Image.fromarray(fa))

# 靴（主役）: 原案の中央。床の接地影と、柔らかい落ち影
shoe = Image.open(f'{d}/L17.png'); shoe = shoe.crop(shoe.getbbox())
s = 0.92; shoe = shoe.resize((int(shoe.width * s), int(shoe.height * s)), Image.LANCZOS)
sx, sy = (W - shoe.width) // 2 + 6, H - shoe.height - 58
sh = Image.new('RGBA', (W, H), 0); dd = ImageDraw.Draw(sh)
dd.ellipse((sx + 10, sy + shoe.height - 40, sx + shoe.width + 10, sy + shoe.height + 26), fill=(40, 26, 14, 120))
im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(22)))
sh = Image.new('RGBA', (W, H), 0); dd = ImageDraw.Draw(sh)
dd.ellipse((sx + 40, sy + shoe.height - 12, sx + shoe.width - 20, sy + shoe.height + 8), fill=(20, 12, 6, 170))
im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
im.alpha_composite(shoe, (sx, sy))

# 誌名（原案の見出しの画）
t = Image.open(f'{d}/T_Brown_Leather_Shoes.png')
im.alpha_composite(t, (125, 20))
dr = ImageDraw.Draw(im)

def spaced(x, y, text, font, fill, track, anchor='l'):
    w = sum(dr.textlength(c, font=font) for c in text) + track * (len(text) - 1)
    if anchor == 'm': x -= w / 2
    if anchor == 'r': x -= w
    for c in text:
        dr.text((x, y), c, font=font, fill=fill, anchor='ls'); x += dr.textlength(c, font=font) + track
    return w

# 誌名の下の罫線とキャプション（小さい字間の広い英字）
cap = f('CormorantGaramond-600.ttf', 19)
w = spaced(W / 2, 138, 'ONE PAIR ,  SIX COORDINATES', cap, INK, 5, 'm')
dr.line((W / 2 - w / 2 - 150, 132, W / 2 - w / 2 - 22, 132), fill=INK, width=1)
dr.line((W / 2 + w / 2 + 22, 132, W / 2 + w / 2 + 150, 132), fill=INK, width=1)

# 左上・右上の号数風の小さい表記
small = f('CormorantGaramond-600.ttf', 17)
spaced(40, 168, '2026  AUTUMN', small, INK, 4)
spaced(W - 40, 168, "MEN'S  STYLE", small, INK, 4, 'r')

# 右端の縦書きの一文（明朝・細め）
vf = f('ShipporiMincho-400.ttf', 24)
x0, y = W - 52, 250
for c in '一足で、六つの装い。':
    if c in '、。':  # 縦書きの句読点は字の枠の右上へ
        dr.text((x0 + 15, y - 17), c, font=vf, fill=INK, anchor='mt'); y += 20
    else:
        dr.text((x0, y), c, font=vf, fill=INK, anchor='mt'); y += 34

# 左下のブランド
logo = Image.open('/home/user/-shiun-reservation/editing/thumbs/assets/logos/shiun_black.png').convert('RGBA')
logo = logo.crop(logo.getbbox()); lh = 26; logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
im.alpha_composite(logo, (40, H - 30 - lh))
spaced(W - 40, H - 34, 'COW LEATHER U-TIP DERBY  ( +6cm )', small, INK, 3, 'r')

# 粒子
g = np.random.default_rng(1).normal(0, 4.5, (H, W, 1))
a = np.clip(np.asarray(im.convert('RGB')).astype(float) + g, 0, 255).astype('uint8')
Image.fromarray(a).save(out)
print('saved', out)
