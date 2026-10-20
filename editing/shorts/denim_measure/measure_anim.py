"""デニムの股上・股下の解説動画に、メジャー風の線と数字（ゴシック）を重ねる。
    python3 measure_anim.py IN.mp4 OUT.mp4 [--still 秒 OUT.png]
線と数字は話す時刻（文字起こしの単語の時刻）に合わせて出す。字幕は入れない"""
import sys, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 60000 / 1001
F = '/root/.fonts/'
INK = (34, 34, 34)
ft = lambda n, s: ImageFont.truetype(F + n, s)
F_LABEL, F_NUM, F_UNIT = ft('NotoSansJP-500.ttf', 30), ft('NotoSansJP-700.ttf', 76), ft('NotoSansJP-500.ttf', 34)

# デニムの位置（1920×1080 の画で測った値）
WAIST, CROTCH, HEM_L, HEM_R = 118, 482, 985, 970
CROTCH_X = 963
X_TOTAL, X_PARTS = 660, 1250        # 総丈の線（左）、股上・股下の線（右）
CM_PX = (HEM_L - WAIST) / 100       # 総丈 100cm として 1cm の長さ（目盛り用）

# 出す時刻（秒）: 線が伸び始める時刻、数字が出る時刻
TOTAL = dict(line=1.38, num=1.98, y0=WAIST, y1=HEM_L, x=X_TOTAL, side=-1, label='総丈', value=100)
RISE = dict(line=3.40, num=4.54, y0=WAIST, y1=CROTCH, x=X_PARTS, side=1, label='股上', value=27)
INSEAM = dict(line=6.40, num=7.14, y0=CROTCH, y1=HEM_R, x=X_PARTS, side=1, label='股下', value=73)
GROW, FADE, COUNT = 0.55, 0.30, 0.45  # 線が伸びる長さ、文字が出る長さ、数字が数え上がる長さ


def ease(t):  # 0〜1 を滑らかに止める（easeOutCubic）
    t = min(max(t, 0), 1); return 1 - (1 - t) ** 3


def tape(d, x, y0, y1, p, side):
    """メジャーの線: 本線＋両端の横線＋5cm ごとの目盛り（10cm ごとに長く）。p は伸びた割合"""
    if p <= 0: return
    ye = y0 + (y1 - y0) * p
    d.line((x, y0, x, ye), fill=INK, width=3)
    d.line((x - 16, y0, x + 16, y0), fill=INK, width=3)
    n = 0
    while True:
        yy = y0 + n * 5 * CM_PX
        if yy > ye or yy > y1 - 2: break
        if n:
            L = 14 if n % 2 == 0 else 8
            d.line((x, yy, x - side * L, yy), fill=INK, width=2)
        n += 1
    if p >= 1:
        d.line((x - 16, y1, x + 16, y1), fill=INK, width=3)


def label(img, seg, t):
    """「股上」と「27cm」。数字は 0 から数え上がり、全体は下から 12px 浮き上がりながら出る"""
    k = ease((t - seg['num']) / FADE)
    if k <= 0: return
    v = round(seg['value'] * ease((t - seg['num']) / COUNT))
    lay = Image.new('RGBA', (W, H), 0); d = ImageDraw.Draw(lay)
    cy = (seg['y0'] + seg['y1']) / 2 + 12 * (1 - k)
    num, unit = str(v), 'cm'
    wn, wu = d.textlength(num, font=F_NUM), d.textlength(unit, font=F_UNIT)
    w = wn + 6 + wu
    x = seg['x'] + 34 if seg['side'] > 0 else seg['x'] - 34 - max(w, d.textlength(seg['label'], font=F_LABEL))
    d.text((x, cy - 18), seg['label'], font=F_LABEL, fill=INK, anchor='ls')
    d.text((x, cy + 62), num, font=F_NUM, fill=INK, anchor='ls')
    d.text((x + wn + 6, cy + 62), unit, font=F_UNIT, fill=INK, anchor='ls')
    a = lay.getchannel('A').point(lambda q: int(q * k)); lay.putalpha(a)
    img.alpha_composite(lay)


def dashed(d, x0, x1, y, p):
    """股の高さの点線（股の点から右の線まで）。p で左から伸びる"""
    xe = x0 + (x1 - x0) * p; x = x0
    while x < xe:
        d.line((x, y, min(x + 10, xe), y), fill=INK, width=2); x += 18


def frame(t):
    img = Image.new('RGBA', (W, H), 0); d = ImageDraw.Draw(img)
    for seg in (TOTAL, RISE, INSEAM):
        tape(d, seg['x'], seg['y0'], seg['y1'], ease((t - seg['line']) / GROW), seg['side'])
    dashed(d, CROTCH_X + 14, X_PARTS - 20, CROTCH, ease((t - RISE['line']) / GROW))
    d.ellipse((CROTCH_X - 5, CROTCH - 5, CROTCH_X + 5, CROTCH + 5), fill=INK) if t >= RISE['line'] else None
    for seg in (TOTAL, RISE, INSEAM):
        label(img, seg, t)
    return img


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    if '--still' in sys.argv:
        i = sys.argv.index('--still'); t = float(sys.argv[i + 1])
        bg = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', src, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
        import io
        b = Image.open(io.BytesIO(bg)).convert('RGBA'); b.alpha_composite(frame(t)); b.convert('RGB').save(sys.argv[i + 2]); sys.exit()
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src]))
    n = int(math.ceil(dur * FPS))
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', '60000/1001', '-i', '-',
                          '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]', '-map', '[v]', '-map', '0:a',
                          '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-c:a', 'copy', '-shortest', out], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait(); print('saved', out, n, 'frames')
