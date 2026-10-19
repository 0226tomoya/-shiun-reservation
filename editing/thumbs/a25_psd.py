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
import struct, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden_overlay import spiral

d, out = sys.argv[1], sys.argv[2]
W, H = 1280, 720
F = '/root/.fonts/'
INK = (28, 24, 21)
f = lambda n, s: ImageFont.truetype(F + n, s)
yy, xx = np.mgrid[0:H, 0:W]
# 配置（フィボナッチ構図）: 螺旋の目（右下）に靴の U チップの先を置き、余白・間隔は 21・34・55、線は黄金比（0.236・0.382・0.618）に揃える
LAY = dict(M=55,            # 左右の余白
           LABEL_Y=170,     # 2026 AUTUMN・MEN'S STYLE の基線 = 高さ × 0.236
           SUB_Y=136,       # サブタイトルの基線（タイトルの下 34）
           RULE=89,         # サブタイトル両側の罫線の長さ
           VERT_TOP=275,    # 縦書きの 1 字目の上端 = 高さ × 0.382
           VERT_END=615,
           COL_GAP=34, STAGGER=60,  # 縦書きの列の間と、2 列目を下げる量    # 縦書きの最後の字の下端の上限 = 高さ × 0.854
           SHOE_S=0.92,     # 靴の倍率
           SHOE_PT=(690, 200),  # 靴の画像の中で目に合わせる点（U チップの縫い目の先）
           TITLE_K=0.9, TITLE_TOP=34)  # タイトルの倍率と上端
LAY.update(json.loads(os.environ.get('A25_LAYOUT', '{}')))
EYE = spiral(W, H, 0)[1]
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
s = LAY['SHOE_S']; shoe = shoe.resize((int(shoe.width * s), int(shoe.height * s)), Image.LANCZOS)
sx, sy = round(EYE[0] - LAY['SHOE_PT'][0] * s), round(EYE[1] - LAY['SHOE_PT'][1] * s)
a = canvas(); ImageDraw.Draw(a).ellipse((sx + 10, sy + shoe.height - 40, sx + shoe.width + 10, sy + shoe.height + 26), fill=(40, 26, 14, 120))
L_shadow_soft = a.filter(ImageFilter.GaussianBlur(22))
a = canvas(); ImageDraw.Draw(a).ellipse((sx + 40, sy + shoe.height - 12, sx + shoe.width - 20, sy + shoe.height + 8), fill=(20, 12, 6, 170))
L_shadow_contact = a.filter(ImageFilter.GaussianBlur(6))

SUB = 'ELEVATED  INSOLE  SHOES'   # サブタイトル（両側の罫線は文字の幅に合わせて伸び縮み）
# 右の縦書きの候補。最初のものを表示し、残りは非表示のレイヤーで入れる
VERTS = ['あえて、/ブラウンという選択肢。']  # 「/」で列を分ける
cap, small = f('CormorantGaramond-600.ttf', 19), f('CormorantGaramond-600.ttf', 17)
def _cap(dr):
    y, R = LAY['SUB_Y'], LAY['RULE']
    w = spaced(dr, W / 2, y, SUB, cap, INK, 5, 'm')
    dr.line((W / 2 - w / 2 - 21 - R, y - 6, W / 2 - w / 2 - 21, y - 6), fill=INK, width=1)
    dr.line((W / 2 + w / 2 + 21, y - 6, W / 2 + w / 2 + 21 + R, y - 6), fill=INK, width=1)
L_cap = text_layer(_cap)
L_season = text_layer(lambda dr: spaced(dr, LAY['M'], LAY['LABEL_Y'], '2026  AUTUMN', small, INK, 4))
L_mens = text_layer(lambda dr: spaced(dr, W - LAY['M'], LAY['LABEL_Y'], "MEN'S  STYLE", small, INK, 4, 'r'))
L_item = text_layer(lambda dr: spaced(dr, W - LAY['M'], H - 34, 'COW LEATHER U-TIP DERBY  ( +6cm )', small, INK, 3, 'r'))
VS = 21  # 縦書きの字の大きさ（フィボナッチ数）
vf = f('ShipporiMincho-400.ttf', VS)
def _vert(dr, text):
    """縦書き。「/」で列を分け、右から左へ並べる（2 列目以降は STAGGER だけ下げる）。
    句読点は字の枠の右上に置く。1 列が 0.854 の線（VERT_END）を越えるときだけ字の送りを縮める"""
    cols = text.split('/')
    adv = lambda c: 0.59 if c in '、。' else 1
    y_top = LAY['VERT_TOP']
    need = max(sum(adv(c) for c in col) + (k and LAY['STAGGER'] / 30) for k, col in enumerate(cols))
    step = min(30, (LAY['VERT_END'] - y_top) / need)
    for k, col in enumerate(cols):
        x0, y = W - LAY['M'] - 12 - k * LAY['COL_GAP'], y_top + (LAY['STAGGER'] * step / 30 if k else 0)
        for ch in col:
            if ch in '、。':
                dr.text((x0 + VS * 0.55, y - VS * 0.12), ch, font=vf, fill=INK, anchor='mt')
            else:
                dr.text((x0, y), ch, font=vf, fill=INK, anchor='mt')
            y += adv(ch) * step


L_verts = [text_layer(lambda dr, t=t: _vert(dr, t)) for t in VERTS]
logo = Image.open('/home/user/-shiun-reservation/editing/thumbs/assets/logos/shiun_black.png').convert('RGBA')
logo = logo.crop(logo.getbbox()); lh = 26; logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
L_logo = canvas(); L_logo.alpha_composite(logo, (LAY['M'], H - 30 - lh))
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
if LAY['TITLE_K'] != 1.0 or LAY['TITLE_TOP'] != top.top:
    k = LAY['TITLE_K']; t = top._record.tagged_blocks.get_data(Tag.TYPE_TOOL_OBJECT_SETTING)
    xx, xy, yx, yy, tx, ty = t.transform
    im = top.topil().convert('RGBA'); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    nleft, ntop = round(tx + (top.left - tx) * k), LAY['TITLE_TOP']
    t.transform = (xx * k, xy * k, yx * k, yy * k, tx, ntop + (ty - top.top) * k)
    tmp = PixelLayer.fromarray(np.asarray(im), p, 'tmp', top=ntop, left=nleft); p.remove(tmp)
    r = top._record; r.top, r.left, r.bottom, r.right = tmp._record.top, tmp._record.left, tmp._record.bottom, tmp._record.right
    r.channel_info = tmp._record.channel_info; top._channels = tmp._channels
bb = L_cap.getbbox()
ab.append(mk(L_cap.crop(bb), f'サブタイトル {" ".join(SUB.split())}（Cormorant Garamond SemiBold 19・字間 5）＋罫線', bb[1], bb[0]))
for img, nm in ((L_season, '2026 AUTUMN（Cormorant Garamond SemiBold 17）'), (L_mens, "MEN'S STYLE（Cormorant Garamond SemiBold 17）"),
                (L_item, '商品名 COW LEATHER U-TIP DERBY (+6cm)（Cormorant Garamond SemiBold 17）'),
                (L_logo, 'shiun ロゴ')):
    bb = img.getbbox(); ab.append(mk(img.crop(bb), nm, bb[1], bb[0]))
for i, (img, t) in enumerate(zip(L_verts, VERTS)):
    bb = img.getbbox(); lay = mk(img.crop(bb), f'縦書き{"" if i == 0 else "（候補・非表示）"} {t.replace('/', '')}（しっぽり明朝 Regular {VS}）', bb[1], bb[0])
    lay.visible = i == 0; ab.insert(ab.index(by['Brown Leather Shoes']) + 1, lay)
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
