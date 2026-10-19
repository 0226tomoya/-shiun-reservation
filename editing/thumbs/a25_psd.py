"""A25 サムネ v2 を PSD で書き出す。元の PSD（src.psd）を土台に、v2 で変えた所だけを入れる。
    python3 a25_psd.py 作業フォルダ（src.psd・L*.png がある所） OUT.psd
元の文字レイヤー（Brown Leather Shoes・Coordinate）は打ち直せる文字のまま残す。足した文字は画のレイヤー（名前に書体を書く）

Photoshop で「互換性がありません」と出て開けなかった原因（2026-10-19）:
  1. psd-tools は保存し直すだけでスマートオブジェクトの埋め込みデータ（lnk2）の末尾（contentID）を落とす → 全体のタグブロックは元のバイトを戻す
  2. frompil は RGB の PSD だと透明をマスクにし、レイヤー ID も付けない → fromarray で透明度付きにし、ID を振る
検証は psd_tools_js/check.js（ag-psd）でも読む。予備に psd_tools_js/write.js で全部画の PSD も作れる"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from psd_tools.constants import BlendMode, Tag
import struct

d, out = sys.argv[1], sys.argv[2]
W, H = 1280, 720
F = '/root/.fonts/'
INK = (28, 24, 21)
f = lambda n, s: ImageFont.truetype(F + n, s)
yy, xx = np.mgrid[0:H, 0:W]
bgimg = Image.open(f'{d}/L1.png').crop((1106, 0, 2386, 720)).convert('RGB')

def canvas():
    return Image.new('RGBA', (W, H), 0)

def text_layer(draw_fn):
    c = canvas(); draw_fn(ImageDraw.Draw(c)); return c

def spaced(dr, x, y, text, font, fill, track, anchor='l'):
    w = sum(dr.textlength(c, font=font) for c in text) + track * (len(text) - 1)
    x -= {'l': 0, 'm': w / 2, 'r': w}[anchor]
    for ch in text:
        dr.text((x, y), ch, font=font, fill=fill, anchor='ls'); x += dr.textlength(ch, font=font) + track
    return w

# --- 新しいレイヤーの画（v2 と同じ値） ---
r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.75)) ** 2)
fac = 1.02 - 0.10 * np.clip(r, 0, 1.4) ** 2
vig = np.zeros((H, W, 4), 'uint8'); vig[..., 3] = (np.clip(1 - fac, 0, 1) * 255).astype('uint8')
L_vig = Image.fromarray(vig)

fa = np.zeros((H, W, 4), 'uint8'); fa[..., :3] = np.asarray(bgimg)
fa[..., 3] = (np.clip((yy - 560) / 160, 0, 1) * 150).astype('uint8')
L_fade = Image.fromarray(fa)

shoe = Image.open(f'{d}/L17.png'); shoe = shoe.crop(shoe.getbbox())
s = 0.92; shoe = shoe.resize((int(shoe.width * s), int(shoe.height * s)), Image.LANCZOS)
sx, sy = (W - shoe.width) // 2 + 6, H - shoe.height - 58
a = canvas(); ImageDraw.Draw(a).ellipse((sx + 10, sy + shoe.height - 40, sx + shoe.width + 10, sy + shoe.height + 26), fill=(40, 26, 14, 120))
L_shadow_soft = a.filter(ImageFilter.GaussianBlur(22))
a = canvas(); ImageDraw.Draw(a).ellipse((sx + 40, sy + shoe.height - 12, sx + shoe.width - 20, sy + shoe.height + 8), fill=(20, 12, 6, 170))
L_shadow_contact = a.filter(ImageFilter.GaussianBlur(6))

cap, small = f('CormorantGaramond-600.ttf', 19), f('CormorantGaramond-600.ttf', 17)
def _cap(dr):
    w = spaced(dr, W / 2, 138, 'ONE PAIR ,  SIX COORDINATES', cap, INK, 5, 'm')
    dr.line((W / 2 - w / 2 - 150, 132, W / 2 - w / 2 - 22, 132), fill=INK, width=1)
    dr.line((W / 2 + w / 2 + 22, 132, W / 2 + w / 2 + 150, 132), fill=INK, width=1)
L_cap = text_layer(_cap)
L_season = text_layer(lambda dr: spaced(dr, 40, 168, '2026  AUTUMN', small, INK, 4))
L_mens = text_layer(lambda dr: spaced(dr, W - 40, 168, "MEN'S  STYLE", small, INK, 4, 'r'))
L_item = text_layer(lambda dr: spaced(dr, W - 40, H - 34, 'COW LEATHER U-TIP DERBY  ( +6cm )', small, INK, 3, 'r'))
vf = f('ShipporiMincho-400.ttf', 24)
def _vert(dr):
    x0, y = W - 52, 250
    for ch in '一足で、六つの装い。':
        if ch in '、。':
            dr.text((x0 + 15, y - 17), ch, font=vf, fill=INK, anchor='mt'); y += 20
        else:
            dr.text((x0, y), ch, font=vf, fill=INK, anchor='mt'); y += 34
L_vert = text_layer(_vert)
logo = Image.open('/home/user/-shiun-reservation/editing/thumbs/assets/logos/shiun_black.png').convert('RGBA')
logo = logo.crop(logo.getbbox()); lh = 26; logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
L_logo = canvas(); L_logo.alpha_composite(logo, (40, H - 30 - lh))
L_shoe = canvas(); L_shoe.alpha_composite(shoe, (sx, sy))
g = np.random.default_rng(1).normal(0, 4.5, (H, W))
grain = np.clip(128 + g * 2, 0, 255).astype('uint8')
L_grain = Image.fromarray(np.dstack([grain, grain, grain, np.full((H, W), 255, 'uint8')]))
co = Image.open(f'{d}/T_Coordinate.png')
co.putalpha(co.getchannel('A').point(lambda v: int(v * 0.55)))
L_coord = canvas(); L_coord.alpha_composite(co, (-63, 60))

# --- PSD ---
p = PSDImage.open(f'{d}/src.psd')
ab = p[0]
by = {l.name: l for l in ab}

# グループの終わりの区切り（</Layer group>）も ID を持つので、全レコードの最大の次から振る
_ids = iter(range(max(r.tagged_blocks.get_data(Tag.LAYER_ID, 0) for r in p._record.layer_and_mask_information.layer_info.layer_records) + 1, 10 ** 6))

def mk(img, name, top, left):
    """透明度付きの普通のレイヤーにする（frompil は RGB の PSD だと透明をマスクにしてしまい、Photoshop が嫌う形になる）。
    日本語の名前は Unicode の名前欄に入れ、古い名前欄は英数字だけにする。レイヤー ID も振る"""
    lay = PixelLayer.fromarray(np.asarray(img.convert('RGBA')), p, 'Layer', top=top, left=left)
    lay.name = name
    lay._record.name = 'Layer'
    lay._record.tagged_blocks.set_data(Tag.LAYER_ID, next(_ids))
    return lay


def add(img, name, before, blend=None, opacity=255):
    """img（キャンバス大）を中身の範囲に切って、before のレイヤーの下に入れる"""
    bb = img.getbbox()
    lay = mk(img.crop(bb), name, bb[1], bb[0])
    if blend: lay.blend_mode = blend
    lay.opacity = opacity
    ab.insert(ab.index(before), lay)
    return lay

# 背景の上に周辺減光
add(L_vig, '周辺減光', by['Coordinate'])
# Coordinate（筆記体）: 元の文字レイヤーは隠して残し、v2 の位置・濃さの画を足す
by['Coordinate'].visible = False
add(L_coord, 'Coordinate（v2 の位置・濃さ。元の文字レイヤーは下に非表示で残す）', by['グループ 2'])
# 筆記体の飾り（Fall・Men's・2026・Fashion）は非表示
by['グループ 2'].visible = False
# 6 人は元の位置から 10px 下へ。2 人目の左上の白い点を消す
for l in list(by['グループ 1']):
    l.top = l.top + 10
    if l.left == 165:
        arr = l.numpy()  # 0〜1
        arr[:120, :150, 3] = 0
        im = Image.fromarray((arr * 255).astype('uint8'), 'RGBA')
        nl = mk(im, l.name, l.top, l.left)
        g1 = by['グループ 1']; g1.insert(g1.index(l), nl); l.visible = False; l.name = l.name + '（元・白い点あり）'
add(L_fade, '足元を紙になじませる', by['レイヤー 3 のコピー'])
add(L_shadow_soft, '靴の影（ぼかし）', by['レイヤー 3 のコピー'])
add(L_shadow_contact, '靴の接地影', by['レイヤー 3 のコピー'])
by['レイヤー 3 のコピー'].visible = False
by['レイヤー 3 のコピー'].name = '靴（元の大きさ・位置）'
add(L_shoe, '靴（92%・下へ）', by['Gemini_Generated_Image_gtgf75gtgf75gtgf'])
top = by['Brown Leather Shoes']
bb = L_cap.getbbox()
ab.append(mk(L_cap.crop(bb), 'キャプション ONE PAIR, SIX COORDINATES（Cormorant Garamond SemiBold 19・字間 5）＋罫線', bb[1], bb[0]))
for img, nm in ((L_season, '2026 AUTUMN（Cormorant Garamond SemiBold 17）'), (L_mens, "MEN'S STYLE（Cormorant Garamond SemiBold 17）"),
                (L_vert, '縦書き 一足で、六つの装い。（しっぽり明朝 Regular 24）'), (L_item, '商品名 COW LEATHER U-TIP DERBY (+6cm)（Cormorant Garamond SemiBold 17）'),
                (L_logo, 'shiun ロゴ')):
    bb = img.getbbox(); ab.append(mk(img.crop(bb), nm, bb[1], bb[0]))
gr = mk(L_grain, '粒子（オーバーレイ）', 0, 0); gr.blend_mode = BlendMode.OVERLAY; gr.opacity = 255
ab.append(gr)
p.save(out)


def global_blocks(b):
    """レイヤーとマスク情報の後ろにある、全体のタグブロックの位置（始まり・終わり）"""
    o = 26; o += 4 + struct.unpack('>I', b[o:o + 4])[0]; o += 4 + struct.unpack('>I', b[o:o + 4])[0]
    lm_end = o + 4 + struct.unpack('>I', b[o:o + 4])[0]
    q = o + 8 + struct.unpack('>I', b[o + 4:o + 8])[0]
    q += 4 + struct.unpack('>I', b[q:q + 4])[0]
    return o, q, lm_end


# psd-tools はスマートオブジェクトの埋め込みデータ（lnk2）の末尾（contentID）を落とすので、全体のタグブロックは元のバイトに戻す
src, new = open(f'{d}/src.psd', 'rb').read(), open(out, 'rb').read()
so, sq, se = global_blocks(src)
no, nq, ne = global_blocks(new)
body = new[no + 4:nq] + src[sq:se]
open(out, 'wb').write(new[:no] + struct.pack('>I', len(body)) + body + new[ne:])
print('saved', out)
for l in PSDImage.open(out)[0]:
    print(' ', 'vis' if l.visible else 'HID', l.kind, l.name)
