"""デニムの股上・股下の解説動画に、メジャー風の線と数字（ゴシック）を重ねる。v2 からは数字をデータ入力のように 1 字ずつ打ち込み、効果音（キー・確定・線のシュッ）を合成して混ぜる。
    python3 measure_anim.py IN.mp4 OUT.mp4 [--mute] [--still 秒 OUT.png]
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


TYPE_GAP, CARET_BLINK, CARET_HOLD = 0.075, 0.5, 0.75  # 1 字を打つ間隔、カーソルの点滅の周期、打ち終わってカーソルを残す長さ


def typed(seg):
    """入力する文字（数字＋cm）と、それぞれを打つ時刻"""
    chars = list(str(seg['value'])) + ['c', 'm']
    return chars, [seg['num'] + k * TYPE_GAP for k in range(len(chars))]


def label(img, seg, t):
    """データ入力の見た目: 見出し（股上など）が出て、数字と cm を 1 字ずつ打ち込む。
    入力欄の下線が伸び、打っている間は縦棒のカーソルが点滅する。打ち終わると少ししてカーソルが消える"""
    k = ease((t - seg['num'] + 0.15) / 0.2)
    if k <= 0: return
    chars, at = typed(seg)
    n = sum(1 for a in at if t >= a)
    lay = Image.new('RGBA', (W, H), 0); d = ImageDraw.Draw(lay)
    cy = (seg['y0'] + seg['y1']) / 2
    nd = len(str(seg['value']))
    num, unit = ''.join(chars[:min(n, nd)]), ''.join(chars[nd:n])
    full_w = d.textlength(str(seg['value']), font=F_NUM) + 6 + d.textlength('cm', font=F_UNIT)
    x = seg['x'] + 34 if seg['side'] > 0 else seg['x'] - 34 - full_w
    d.text((x, cy - 18), seg['label'], font=F_LABEL, fill=INK + (int(255 * k),), anchor='ls')
    wn = d.textlength(num, font=F_NUM) if num else 0
    d.text((x, cy + 62), num, font=F_NUM, fill=INK, anchor='ls')
    if unit:
        d.text((x + d.textlength(str(seg['value']), font=F_NUM) + 6, cy + 62), unit, font=F_UNIT, fill=INK, anchor='ls')
    # 入力欄の下線（見出しと一緒に左から伸びる）
    d.line((x, cy + 80, x + (full_w + 14) * k, cy + 80), fill=INK + (110,), width=2)
    # カーソル
    end = at[-1]
    if t < end + CARET_HOLD and (t < end or ((t - end) % CARET_BLINK) < CARET_BLINK / 2):
        cx = x + (wn if n <= nd else d.textlength(str(seg['value']), font=F_NUM) + 6 + d.textlength(unit, font=F_UNIT)) + 5
        d.rectangle((cx, cy + 6, cx + 3, cy + 66), fill=INK)
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


SR = 48000
ENTER = False  # 打ち終わりの確定音（ピロン）。ユーザーの指示で外した
SFX_DB = dict(key=-22, enter=-20, whoosh=-30)  # 効果音の大きさ（dBFS の目安）。声（−20 前後）より下に置く


def _db(x, db):
    return x / (np.abs(x).max() + 1e-9) * 10 ** (db / 20)


def key_click(rng):
    """キーを 1 回打つ音: 短い高めの雑音のはじき＋低い「コッ」"""
    n = int(SR * 0.035); t = np.arange(n) / SR
    noise = rng.normal(0, 1, n); noise = np.diff(np.concatenate([[0], noise]))  # 高い成分を残す
    body = np.sin(2 * np.pi * rng.uniform(1700, 2100) * t) * 0.5 + np.sin(2 * np.pi * 180 * t) * 0.6
    return _db((noise * 0.6 + body) * np.exp(-t / 0.006), SFX_DB['key'] + rng.uniform(-2, 1))


def enter_beep():
    """確定の「ピッ」: 柔らかい 2 つの高さの短い音"""
    out = []
    for f0, L in ((1568, 0.05), (2093, 0.09)):
        t = np.arange(int(SR * L)) / SR
        env = np.minimum(1, t / 0.004) * np.exp(-t / (L * 0.45))
        out.append(np.sin(2 * np.pi * f0 * t) * env)
    return _db(np.concatenate(out), SFX_DB['enter'])


def whoosh(L):
    """線が伸びるときのごく薄い「シュッ」: 帯域を絞った雑音を上げて下げる"""
    rng = np.random.default_rng(7); n = int(SR * L); t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    k = np.ones(24) / 24; x = x - np.convolve(x, k, 'same')       # 低い成分を落とす
    x = np.convolve(x, np.ones(4) / 4, 'same')                      # 高すぎる成分を落とす
    env = np.sin(np.pi * np.clip(t / L, 0, 1)) ** 2
    return _db(x * env, SFX_DB['whoosh'])


def write_sfx(path, dur):
    import wave
    rng = np.random.default_rng(1)
    track = np.zeros(int(SR * (dur + 1)))
    def put(x, at):
        i = int(at * SR); track[i:i + len(x)] += x[:len(track) - i]
    for seg in (TOTAL, RISE, INSEAM):
        put(whoosh(GROW + 0.1), seg['line'])
        chars, at = typed(seg)
        for a in at: put(key_click(rng), a)
        if ENTER: put(enter_beep(), at[-1] + 0.12)
    track = track[:int(SR * dur)]
    pcm = (np.clip(track, -1, 1) * 32767).astype('<i2')
    st = np.repeat(pcm[:, None], 2, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    MUTE = '--mute' in sys.argv  # 元の声を消して、音は効果音だけ（効果音は 8dB 上げる）
    if '--still' in sys.argv:
        i = sys.argv.index('--still'); t = float(sys.argv[i + 1])
        bg = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', src, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
        import io
        b = Image.open(io.BytesIO(bg)).convert('RGBA'); b.alpha_composite(frame(t)); b.convert('RGB').save(sys.argv[i + 2]); sys.exit()
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src]))
    n = int(math.ceil(dur * FPS))
    sfx_path = out.rsplit('.', 1)[0] + '_sfx.wav'
    write_sfx(sfx_path, dur)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', '60000/1001', '-i', '-',
                          '-i', sfx_path,
                          '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v];' + ('[2:a]volume=8dB,apad[a]' if MUTE else '[0:a][2:a]amix=inputs=2:normalize=0:duration=first[a]'),
                          '-map', '[v]', '-map', '[a]',
                          '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-c:a', 'aac', '-b:a', '256k', '-shortest', out], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait(); print('saved', out, n, 'frames')
