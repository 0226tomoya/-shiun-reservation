"""short_overlay.py の出力（縦ショート）から、確認用の静止画を作る（簡易）。

    python3 short_overlay_preview.py OUT.fcpxml "プロジェクト名" OUTDIR 秒 [秒 …] [--sheet SHEET.jpg]

- 本線: 作業用の動画（PROXY_DIR/DSCFxxxx.mp4、1080x1920）から、mc-clip の start（＝映像の時刻）でその瞬間のコマを取る。
  mc-source の adjust-transform と、調整レイヤー（lane 1）の拡大・位置を掛ける（位置 1 = 画面の高さの 1% = 19.2px）。
- 画像: 手元のファイル（SNS 用高画質は「番号」で、色調整済みは名前で対応）を、画面に収まる大きさ → scale → 位置。
- テロップ: 字幕（Klee One で代用）・商品名/価格/発売日（Cormorant Garamond で代用、縦 1.4 倍などの調整も掛ける）・身長ラベル。
  字の大きさ・位置は近似（字幕は画面の縦の中央。08 月の完成動画で字の高さ約 38px）。
"""
import glob
import os
import subprocess
import sys
import unicodedata as ud
import xml.etree.ElementTree as ET
from fractions import Fraction as F
from urllib.parse import unquote

from PIL import Image, ImageDraw, ImageFont

S = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/'
PROXY = os.environ.get('SHORT_PROXY', S + 'short_src/proxy/')
SNS = os.environ.get('SHORT_SNS', S + 'm3/SNS用高画質/')
COLOR = os.environ.get('SHORT_COLOR', S + 'ins_src/色調整済み/')
SNS_FOLDER = {'5.COW LEATHER LOAFER 2': '6.COW LEATHER LOAFER'}  # Mac のフォルダ → 手元のフォルダ
KLEE = os.path.expanduser('~/.fonts/KleeOne-600.ttf')
SERIF = os.path.expanduser('~/.fonts/CormorantGaramond-700.ttf')
W, H = 1080, 1920
U = H / 100  # 位置 1 単位 = 画面の高さの 1%
PT = 1.57    # テロップの大きさ（pt → px の近似）
N = lambda s: ud.normalize('NFC', s or '')


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return F(int(a), int(b))
    return F(s)


def local_image(src):
    src = N(unquote(src))
    if '/SNS用高画質/' in src:
        folder, fn = src.split('/SNS用高画質/', 1)[1].rsplit('/', 1)
        folder = SNS_FOLDER.get(folder, folder)
        num = fn[3:5]
        c = glob.glob(os.path.join(SNS, folder, num + '*'))
        return c[0] if c else None
    if '/色調整済み/' in src:
        p = os.path.join(COLOR, src.rsplit('/', 1)[1])
        return p if os.path.exists(p) else None
    return None


def transform(img, scale, pos):
    """画面サイズの画を、中心から scale 倍して pos（%）だけ動かす"""
    sx = float(scale.split()[0]) if scale else 1.0
    px, py = (float(v) for v in (pos or '0 0').split())
    w, h = int(img.width * sx), int(img.height * sx)
    big = img.resize((w, h))
    out = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    out.paste(big, (int(W / 2 - w / 2 + px * U), int(H / 2 - h / 2 - py * U)))
    return out


def place_image(path, scale, pos):
    src = Image.open(path)
    src.draft('RGB', (2400, 2400))
    src = src.convert('RGBA')
    fit = min(W / src.width, H / src.height)
    sx = float((scale or '1 1').split()[0])
    w, h = int(src.width * fit * sx), int(src.height * fit * sx)
    src = src.resize((w, h))
    px, py = (float(v) for v in (pos or '0 0').split())
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    layer.paste(src, (int(W / 2 - w / 2 + px * U), int(H / 2 - h / 2 - py * U)))
    return layer


def text_block(lines, font, size, stretch=(1.0, 1.0), stroke=0, align='center', spacing=0):
    f = ImageFont.truetype(font, max(8, int(size)))
    tmp = Image.new('RGBA', (10, 10))
    d = ImageDraw.Draw(tmp)
    bbs = [d.textbbox((0, 0), ln, font=f, stroke_width=stroke) for ln in lines]
    lw = max(b[2] - b[0] for b in bbs) + 4
    lh = int(size * 1.25 + spacing)
    img = Image.new('RGBA', (lw, lh * len(lines) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (ln, b) in enumerate(zip(lines, bbs)):
        x = (lw - (b[2] - b[0])) / 2 if align == 'center' else (lw - (b[2] - b[0]) if align == 'right' else 0)
        d.text((x - b[0], i * lh), ln, font=f, fill=(255, 255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 90))
    if stretch != (1.0, 1.0):
        img = img.resize((int(img.width * stretch[0]), int(img.height * stretch[1])))
    return img


def frame(proj, t, res):
    t = F(t).limit_denominator(60000)
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    spine = list(proj.find('sequence/spine'))
    over = []
    for c in spine:
        off, st, du = T(c.get('offset')), T(c.get('start')), T(c.get('duration'))
        for x in c:
            if x.get('lane') is None:
                continue
            a = off + T(x.get('offset')) - st
            if a <= t < a + T(x.get('duration')):
                over.append(x)
        if c.tag == 'mc-clip' and off <= t < off + du:
            media = res[c.get('ref')]
            clip = N(media.get('name')).split()[0]
            vt = float(st + (t - off))
            p = f'/tmp/_ovp_{clip}_{vt:.3f}.png'
            if not os.path.exists(p):
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{vt:.3f}', '-i', PROXY + clip + '.mp4', '-frames:v', '1', p], check=True)
            im = Image.open(p).convert('RGBA').resize((W, H))
            ms = [m for m in c.findall('mc-source') if m.get('angleID') == 'V1']
            tf = ms[0].find('adjust-transform') if ms else None
            if tf is not None:
                im = transform(im, tf.get('scale'), tf.get('position'))
            canvas = im
        elif c.tag != 'mc-clip' and off <= t < off + du:
            canvas = Image.new('RGBA', (W, H), (20, 20, 20, 255))
            ImageDraw.Draw(canvas).text((40, 40), 'AI 音声: ' + N(c.get('name'))[-20:], font=ImageFont.truetype(KLEE, 30), fill='white')
    over.sort(key=lambda x: int(x.get('lane')))
    for x in over:
        lane = int(x.get('lane'))
        if lane < 0:
            continue
        name = N(x.get('name'))
        if x.tag == 'title' and name == 'Adjustment Layer':
            tf = x.find('adjust-transform')
            canvas = transform(canvas.convert('RGBA'), tf.get('scale'), tf.get('position'))
        elif x.tag == 'video':
            a = res[x.get('ref')]
            lp = local_image(a.find('media-rep').get('src'))
            tf = x.find('adjust-transform')
            if lp:
                canvas.alpha_composite(place_image(lp, tf.get('scale'), tf.get('position')))
            else:
                ImageDraw.Draw(canvas).rectangle((0, 0, W, H), fill=(120, 0, 0, 255))
        elif x.tag == 'title':
            txt = N(''.join(s.text or '' for s in x.find('text')))
            st = x.find('text-style-def/text-style')
            font, size = st.get('font'), float(st.get('fontSize'))
            prm = {N(p.get('name')): p.get('value') for p in x.findall('param')}
            px, py = (float(v) for v in prm.get('位置', '0 0').split())
            adj = tuple(float(v) for v in prm.get('調整', '1 1').split())
            tf = x.find('adjust-transform')
            sc = float((tf.get('scale') or '1 1').split()[0]) if tf is not None else 1.0
            tx, ty = (float(v) for v in ((tf.get('position') if tf is not None else None) or '0 0').split())
            if font == 'Klee':
                blk = text_block(txt.split('\n'), KLEE, size * PT * sc, stroke=3)
                cx, cy = W / 2 + px * sc, H / 2 + 10  # 字幕は画面の縦の中央（位置 −415＋ベースライン 405）
                canvas.alpha_composite(blk, (int(cx - blk.width / 2), int(cy - blk.height / 2)))
            else:
                al = st.get('alignment', 'center')
                blk = text_block(txt.split('\n'), SERIF, size * PT * sc, stretch=adj, align=al)
                cx, cy = W / 2 + (px * sc) + tx * U, H / 2 - (py * sc) - ty * U
                x0 = cx - blk.width / 2 if al == 'center' else cx - blk.width
                canvas.alpha_composite(blk, (int(x0), int(cy - blk.height / 2)))
    return canvas.convert('RGB')


def main():
    args = sys.argv[1:]
    sheet = None
    if '--sheet' in args:
        i = args.index('--sheet')
        sheet = args[i + 1]
        del args[i:i + 2]
    path, pname, outdir = args[:3]
    times = [float(v) for v in args[3:]]
    r = ET.parse(path).getroot()
    res = {e.get('id'): e for e in r.find('resources')}
    proj = [p for p in r.iter('project') if N(p.get('name')) == N(pname)][0]
    os.makedirs(outdir, exist_ok=True)
    ims = []
    for t in times:
        im = frame(proj, t, res)
        p = os.path.join(outdir, f'{t:07.2f}.jpg')
        im.save(p, quality=85)
        ims.append((t, im))
    if sheet:
        tw, th = 360, 640
        s = Image.new('RGB', (tw * min(4, len(ims)), th * ((len(ims) + 3) // 4)), 'white')
        d = ImageDraw.Draw(s)
        for k, (t, im) in enumerate(ims):
            x, y = (k % 4) * tw, (k // 4) * th
            s.paste(im.resize((tw, th)), (x, y))
            d.text((x + 6, y + 6), f'{t:.2f}s', fill='yellow', font=ImageFont.truetype(KLEE, 26))
        s.save(sheet, quality=85)
        print(sheet)


if __name__ == '__main__':
    main()
