"""服の寸法の解説動画に、メジャー風の線と数字（データ入力風）と効果音を重ねる。どの服でも使える版。
    python3 measure_kit.py SPEC.json [--still 秒 OUT.png] [--check OUT.png]
SPEC.json の書き方は README.md（同じフォルダ）と presets.json（服の種類ごとの型）。
  --check は服の点（ランドマーク）と線の置き場所を、最後の状態で 1 枚に描く（置き場所の確認用）
2026-10-20 のデニムの動画（editing/shorts/denim_measure）でユーザーが気に入った見た目・音をそのまま使う"""
import sys, json, math, subprocess, io, os, re, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = '/root/.fonts/'
INK, WHITE = (34, 34, 34), (250, 250, 248)
ft = lambda n, s: ImageFont.truetype(F + n, s)
GROW, TYPE_GAP, CARET_BLINK, CARET_HOLD = 0.55, 0.075, 0.5, 0.75
SR = 48000
SFX_DB = dict(key=-22, whoosh=-30)
MUTE_GAIN_DB = 8


def ease(t):
    t = min(max(t, 0), 1); return 1 - (1 - t) ** 3


# ---------- 点と線 ----------
def resolve(p, pts):
    """点は [x, y] か、ランドマークの名前（"肩先L"）か、{"mid": [名前, 名前]}（2 点の中点）"""
    if isinstance(p, str): return np.array(pts[p], float)
    if isinstance(p, dict) and 'mid' in p: return (resolve(p['mid'][0], pts) + resolve(p['mid'][1], pts)) / 2
    if isinstance(p, dict) and 'at' in p: return resolve(p['at'], pts) + np.array(p.get('d', [0, 0]), float)
    return np.array(p, float)


BOX_H = 136  # 数字の箱の高さ（見出し・数字・下線）
MARGIN = 60  # 服の外に置く縦の線の、服の端からの距離


def path_points(item, pts):
    """kind: "v"（縦。from/to の高さだけ使い、x は left/right = 服の外か数字）、"h"（横。from/to の x、y は from/to の平均か数字）、無し = path の折れ線"""
    kind = item.get('kind')
    if kind == 'v':
        a, b = resolve(item['from'], pts), resolve(item['to'], pts); bb = pts.get('bbox')
        x = item.get('x', 'left')
        X = bb[0] - MARGIN if x == 'left' else bb[2] + MARGIN if x == 'right' else float(x)
        return [np.array([X, a[1]]), np.array([X, b[1]])]
    if kind == 'h':
        a, b = resolve(item['from'], pts), resolve(item['to'], pts)
        Y = item.get('y', (a[1] + b[1]) / 2); Y = float(Y) + item.get('dy', 0)
        return [np.array([a[0], Y]), np.array([b[0], Y])]
    P = [resolve(p, pts) for p in item['path']]
    off = item.get('offset', 0)
    if off and len(P) == 2:
        u = (P[1] - P[0]) / (np.linalg.norm(P[1] - P[0]) + 1e-9); n = np.array([-u[1], u[0]])
        P = [p + n * off for p in P]
    return P


def along(P, s):
    """折れ線 P の、始めから長さ s の点と向き"""
    for a, b in zip(P, P[1:]):
        L = np.linalg.norm(b - a)
        if s <= L or b is P[-1]:
            u = (b - a) / (L + 1e-9); return a + u * min(s, L), u
        s -= L
    return P[-1], (P[-1] - P[-2]) / (np.linalg.norm(P[-1] - P[-2]) + 1e-9)


def plen(P):
    return sum(np.linalg.norm(b - a) for a, b in zip(P, P[1:]))


def pick_color(bg, P):
    """線が乗る所の明るさで、墨か白かを決める（黒い服の上は白）"""
    if bg is None: return INK
    g = np.asarray(bg.convert('L'))
    L = plen(P); v = []
    for s in np.linspace(0, L, 40):
        q, _ = along(P, s); x, y = int(q[0]), int(q[1])
        if 0 <= x < g.shape[1] and 0 <= y < g.shape[0]: v.append(g[max(0, y - 3):y + 4, max(0, x - 3):x + 4].mean())
    return WHITE if v and np.median(v) < 110 else INK


def tape(d, P, p, col, value, tick_side, cap=16):
    """メジャーの線: 本線＋両端の横線＋5cm ごとの目盛り（10cm ごとに長く）。目盛りの間隔はその寸法の数字から決める"""
    if p <= 0: return
    L = plen(P); cut = L * p
    # 本線
    acc = 0; prev = P[0]
    for a, b in zip(P, P[1:]):
        seg = np.linalg.norm(b - a)
        if acc + seg >= cut:
            e = a + (b - a) * ((cut - acc) / (seg + 1e-9)); d.line((*prev, *e), fill=col, width=3); break
        d.line((*prev, *b), fill=col, width=3); prev = b; acc += seg
    def perp(q, u, l, w):
        n = np.array([-u[1], u[0]]) * tick_side
        d.line((*(q - n * l * (0 if w == 'tick' else 1)), *(q + n * l)), fill=col, width=2 if w == 'tick' else 3)
    q, u = along(P, 0); n = np.array([-u[1], u[0]])
    d.line((*(q - n * cap), *(q + n * cap)), fill=col, width=3)
    try: v = float(value)
    except Exception: v = 0
    if v > 0:
        step = L / v * 5; k = 1
        while k * step < cut and k * step < L - 2:
            q, u = along(P, k * step); perp(q, u, 14 if k % 2 == 0 else 8, 'tick'); k += 1
    if p >= 1:
        q, u = along(P, L); n = np.array([-u[1], u[0]])
        d.line((*(q - n * cap), *(q + n * cap)), fill=col, width=3)


def dashed(d, a, b, p, col):
    a, b = np.array(a, float), np.array(b, float); L = np.linalg.norm(b - a)
    if L < 1 or p <= 0: return
    u = (b - a) / L; s = 0
    while s < L * p:
        e = min(s + 10, L * p); d.line((*(a + u * s), *(a + u * e)), fill=col, width=2); s += 18


# ---------- 文字（データ入力風） ----------
class Typo:
    def __init__(self, scale=1.0):
        self.label, self.num, self.unit = ft('NotoSansJP-500.ttf', round(30 * scale)), ft('NotoSansJP-700.ttf', round(76 * scale)), ft('NotoSansJP-500.ttf', round(34 * scale))
        self.s = scale


def typed(item):
    chars = list(str(item['value'])) + list(item.get('unit', 'cm'))
    return chars, [item['num_at'] + k * TYPE_GAP for k in range(len(chars))]


def label_box(item, P, ty, d):
    """見出し＋数字の置き場所（左上の点）。label_at があればそこ、無ければ線の真ん中から外へ"""
    full_w = d.textlength(str(item['value']), font=ty.num) + 6 * ty.s + d.textlength(item.get('unit', 'cm'), font=ty.unit)
    h = BOX_H * ty.s
    if 'label_at' in item:
        x, y = item['label_at']; return x, y, full_w
    pos = item.get('label_pos'); bb = item.get('_bbox')
    if item.get('kind') == 'v':
        my = (P[0][1] + P[-1][1]) / 2; X = P[0][0]
        side = item.get('label_pos') or item.get('x', 'left')
        return (X - 34 - full_w if side == 'left' else X + 34), my - h / 2, full_w
    if pos in ('left', 'right') and bb is not None:
        my = (P[0][1] + P[-1][1]) / 2
        if pos == 'right': return bb[2] + MARGIN + 34, my - h / 2, full_w
        return bb[0] - MARGIN - 34 - full_w, my - h / 2, full_w
    mid, u = along(P, plen(P) / 2); n = np.array([-u[1], u[0]]) * item.get('label_side', 1)
    gap = item.get('label_gap', 34)
    c = mid + n * gap
    # 線から離れる向きに箱を寄せる
    x = c[0] if n[0] > 0.3 else c[0] - full_w if n[0] < -0.3 else c[0] - full_w / 2
    y = c[1] - h / 2 if abs(n[1]) < 0.7 else (c[1] if n[1] > 0 else c[1] - h)
    return x, y, full_w


def layout(spec, ty, size):
    """全部の数字の箱を決め、重なったら下へずらす（同じ列で 12px あける）"""
    d = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    boxes = []
    for m in sorted(spec['items'], key=lambda m: m['_P'][0][1] + m['_P'][-1][1]):
        x, y, w = label_box(m, m['_P'], ty, d); h = BOX_H * ty.s
        for _ in range(20):
            hit = [b for b in boxes if x < b[0] + b[2] and b[0] < x + w and y < b[1] + b[3] + 12 and b[1] < y + h + 12]
            if not hit: break
            y = max(b[1] + b[3] for b in hit) + 12
        y = min(max(y, 8), size[1] - h - 8); x = min(max(x, 8), size[0] - w - 8)
        m['_box'] = (x, y, w); boxes.append((x, y, w, h))


def draw_label(img, item, P, t, ty, col):
    k = ease((t - item['num_at'] + 0.15) / 0.2)
    if k <= 0: return
    chars, at = typed(item); n = sum(1 for a in at if t >= a)
    lay = Image.new('RGBA', img.size, 0); d = ImageDraw.Draw(lay)
    x, y, full_w = item['_box']
    v = str(item['value']); nd = len(v); unit = item.get('unit', 'cm')
    num, un = ''.join(chars[:min(n, nd)]), ''.join(chars[nd:n])
    s = ty.s; base = y + 112 * s
    d.text((x, y + 32 * s), item['label'], font=ty.label, fill=col + (int(255 * k),), anchor='ls')
    d.text((x, base), num, font=ty.num, fill=col, anchor='ls')
    if un: d.text((x + d.textlength(v, font=ty.num) + 6 * s, base), un, font=ty.unit, fill=col, anchor='ls')
    d.line((x, base + 18 * s, x + (full_w + 14 * s) * k, base + 18 * s), fill=col + (110,), width=2)
    end = at[-1]
    if t < end + CARET_HOLD and (t < end or ((t - end) % CARET_BLINK) < CARET_BLINK / 2):
        wn = d.textlength(num, font=ty.num) if n <= nd else d.textlength(v, font=ty.num) + 6 * s + d.textlength(un, font=ty.unit)
        cx = x + wn + 5 * s; d.rectangle((cx, base - 56 * s, cx + 3 * s, base + 4 * s), fill=col)
    img.alpha_composite(lay)


# ---------- 仕様の読み込み ----------
# ストアのサイズ表の項目名の言い換え（シャツは着丈を前後に分ける、タンクトップは総丈、など）
ALIASES = {'着丈': ['着丈(後)', '後ろ身頃', '総丈'], '総丈': ['着丈'], '着丈(前)': ['前身頃']}


def load_spec(fn):
    spec = json.load(open(fn))
    base = os.path.dirname(os.path.abspath(fn))
    presets = json.load(open(os.path.join(HERE, 'presets.json')))
    pts = spec.get('points', {})
    if 'preset' in spec:  # 型から測る所を作る（spec の items で上書き・追加）
        pre = presets[spec['preset']]
        want = spec.get('use') or [m['label'] for m in pre['items']]
        items = [dict(m) for m in pre['items'] if m['label'] in want]
        for m in spec.get('items', []):
            for i, x in enumerate(items):
                if x['label'] == m['label']: items[i] = {**x, **m}; break
            else: items.append(m)
        spec['guides'] = pre.get('guides', []) + spec.get('guides', [])
    else:
        items = spec['items']
    # 数字: ストアのサイズ表から（product_id と size）
    if 'store' in spec:
        st = {d['product_id']: d for d in json.load(open(spec['store'].get('json', os.path.join(HERE, '../../knowledge/store_sizes.json'))))}
        row = st[spec['store']['product_id']]['sizes'][spec['store']['size']]
        for m in items:
            keys = [m['store_key']] if 'store_key' in m else [m['label']] + ALIASES.get(m['label'], [])
            key = next((k for k in keys if k in row), None)
            if 'value' not in m and key: m['value'] = row[key].replace('cm', '').replace(' ', '')
    # 時刻: 文字起こし（words.json: [{"w": "着丈", "s": 1.2}, ...]）から、見出しの言葉と次の数字を探す
    if 'words' in spec:
        W = json.load(open(os.path.join(base, spec['words'])))
        auto_timing(items, W)
    for m in items:
        m.setdefault('unit', 'cm')
        if 'line_at' not in m or 'num_at' not in m: raise SystemExit(f"{m['label']}: 時刻（line_at / num_at）が決まらない。words か手で入れる")
        if 'value' not in m: raise SystemExit(f"{m['label']}: 数字（value）が無い")
    spec['items'] = [m for m in items]
    spec['points'] = pts
    return spec


def auto_timing(items, W):
    """見出しの言葉（say があればそれ）を言った時刻で線を伸ばし、その後の最初の数字の時刻で数字を打つ。
    言葉と数字の間に別の見出しの言葉が入るとき（「股上と股下を足した総丈が 100cm」）は、その言い方は使わない。
    数字も文字起こしから取る（value が無ければ）"""
    text, starts = '', []
    for w in W:
        for ch in w['w'].strip():
            text += ch; starts.append(w['s'])
    num = re.compile(r'[0-9０-９]+(?:[.．][0-9０-９]+)?')
    keys = [m.get('say', m['label']) for m in items]
    taken = set()
    for m, key in zip(items, keys):
        pos = 0
        while True:
            i = text.find(key, pos)
            if i < 0: break
            mm = num.search(text, i + len(key))
            between = text[i + len(key):mm.start()] if mm else ''
            if mm and mm.start() not in taken and not any(k in between for k in keys if k != key):
                m.setdefault('line_at', starts[i]); m.setdefault('num_at', starts[mm.start()])
                m.setdefault('value', mm.group(0).translate(str.maketrans('０１２３４５６７８９．', '0123456789.')))
                taken.add(mm.start()); break
            pos = i + 1


# ---------- 1 コマ ----------
def frame(spec, t, bg=None, ty=None):
    img = Image.new('RGBA', tuple(spec.get('size', [1920, 1080])), 0); d = ImageDraw.Draw(img)
    pts = spec['points']
    if '_laid' not in spec:
        for m in spec['items']:
            m['_bbox'] = pts.get('bbox'); m['_P'] = path_points(m, pts)
            m['_col'] = (INK if m['color'] == 'ink' else WHITE) if m.get('color') else pick_color(bg, m['_P'])
        layout(spec, ty, img.size); spec['_laid'] = True
    for m in spec['items']:
        P, col = m['_P'], m['_col']
        tape(d, P, ease((t - m['line_at']) / GROW), col, m['value'], m.get('tick_side', -1))
    for g in spec.get('guides', []):
        a = resolve(g['from'], pts)
        if isinstance(g['to'], dict) and 'line' in g['to']:
            L = next((m['_P'] for m in spec['items'] if m['label'] == g['to']['line']), None)
            if L is None: continue
            b = np.array([L[0][0] - np.sign(L[0][0] - a[0]) * 20, a[1]])
        else:
            b = resolve(g['to'], pts)
        at = g.get('at') if 'at' in g else next((m['line_at'] for m in spec['items'] if m['label'] == g.get('with')), None)
        if at is not None:
            gc = INK if g.get('color', 'ink') == 'ink' else WHITE
            dashed(d, a, b, ease((t - at) / GROW), gc)
    for m in spec['items']:
        P = m['_P']
        lc = INK if m.get('label_color', 'ink') == 'ink' else WHITE
        draw_label(img, m, P, t, ty, lc)
    return img


# ---------- 効果音 ----------
def _db(x, db): return x / (np.abs(x).max() + 1e-9) * 10 ** (db / 20)


def key_click(rng):
    n = int(SR * 0.035); t = np.arange(n) / SR
    noise = np.diff(np.concatenate([[0], rng.normal(0, 1, n)]))
    body = np.sin(2 * np.pi * rng.uniform(1700, 2100) * t) * 0.5 + np.sin(2 * np.pi * 180 * t) * 0.6
    return _db((noise * 0.6 + body) * np.exp(-t / 0.006), SFX_DB['key'] + rng.uniform(-2, 1))


def whoosh(L):
    rng = np.random.default_rng(7); n = int(SR * L); t = np.arange(n) / SR
    x = rng.normal(0, 1, n); x = x - np.convolve(x, np.ones(24) / 24, 'same'); x = np.convolve(x, np.ones(4) / 4, 'same')
    return _db(x * np.sin(np.pi * np.clip(t / L, 0, 1)) ** 2, SFX_DB['whoosh'])


def write_sfx(spec, path, dur):
    rng = np.random.default_rng(1); track = np.zeros(int(SR * (dur + 1)))
    def put(x, at):
        i = int(at * SR); track[i:i + len(x)] += x[:len(track) - i]
    for m in spec['items']:
        put(whoosh(GROW + 0.1), m['line_at'])
        for a in typed(m)[1]: put(key_click(rng), a)
    pcm = (np.clip(track[:int(SR * dur)], -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(np.repeat(pcm[:, None], 2, 1).tobytes())


def grab(src, t):
    b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', src, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    return Image.open(io.BytesIO(b)).convert('RGBA')


def main():
    spec = load_spec(sys.argv[1]); base = os.path.dirname(os.path.abspath(sys.argv[1]))
    src = os.path.join(base, spec['video']); out = os.path.join(base, spec.get('out', 'out.mp4'))
    W, H = [int(x) for x in subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', src]).decode().strip().split(',')]
    spec['size'] = [W, H]; ty = Typo(spec.get('text_scale', H / 1080))
    bg = grab(src, spec.get('bg_at', 0.5))
    if '--still' in sys.argv or '--check' in sys.argv:
        flag = '--still' if '--still' in sys.argv else '--check'; i = sys.argv.index(flag)
        t = float(sys.argv[i + 1]) if flag == '--still' else 1e6
        o = sys.argv[i + 2] if flag == '--still' else sys.argv[i + 1]
        b = grab(src, min(t, spec.get('bg_at', 0.5)) if flag == '--check' else t); b.alpha_composite(frame(spec, t, bg, ty))
        if flag == '--check':
            d = ImageDraw.Draw(b); f = ft('NotoSansJP-500.ttf', 20)
            for k, p in spec['points'].items():
                if k.startswith('_') or k == 'bbox': continue
                x, y = p; d.ellipse((x - 6, y - 6, x + 6, y + 6), outline=(230, 30, 30), width=3); d.text((x + 9, y - 24), k, font=f, fill=(230, 30, 30))
        b.convert('RGB').save(o); print('saved', o); return
    fps_s = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', src]).decode().strip()
    fps = eval(fps_s)
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src]))
    sfx = out.rsplit('.', 1)[0] + '_sfx.wav'; write_sfx(spec, sfx, dur)
    mute = spec.get('mute', True)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', fps_s, '-i', '-', '-i', sfx,
                          '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v];' +
                          (f'[2:a]volume={MUTE_GAIN_DB}dB,apad=whole_dur={dur:.3f}[a]' if mute else '[0:a][2:a]amix=inputs=2:normalize=0:duration=first[a]'),
                          '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-c:a', 'aac', '-b:a', '256k', '-t', f'{dur:.3f}', out], stdin=subprocess.PIPE)
    for i in range(int(math.ceil(dur * fps))):
        p.stdin.write(frame(spec, i / fps, bg, ty).tobytes())
    p.stdin.close(); p.wait(); print('saved', out)


if __name__ == '__main__':
    main()
