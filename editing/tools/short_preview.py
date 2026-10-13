"""編集表（short_build.py と同じ EDL）から、確認用の縦動画（540x960）を ffmpeg で書き出す。
python3 short_preview.py edl.json proxy_dir mic_dir out.mp4
- 本線: 作業用の動画（proxy_dir/クリップ名.mp4）の映像＋ピンマイク（mic_dir/マイク.wav）の音を、ずれぶん動かして切り出す
- インサート: 本線の上に重ねる（音なし）
- 字幕・カード: drawtext（KleeOne。カードは近い書体で代用）。位置は型の値を 540x960 に換算
- BGM は確認用には入れない（効果音・BGM の有無は FCPXML 側で採点する）
"""
import sys, json, subprocess, os, tempfile, shlex

edl = json.load(open(sys.argv[1])); PX, MIC, OUT = sys.argv[2:5]
W, H = 540, 960
FONT = os.path.expanduser('~/.fonts/KleeOne-600.ttf')
if not os.path.exists(FONT):
    FONT = next((os.path.join(os.path.expanduser('~/.fonts'), f) for f in os.listdir(os.path.expanduser('~/.fonts')) if f.startswith('KleeOne')), '')
SERIF = os.path.expanduser('~/.fonts/CormorantGaramond-600.ttf')
if not os.path.exists(SERIF):
    SERIF = FONT
tmp = tempfile.mkdtemp()
parts = []
for i, s in enumerate(edl['segments']):
    c = edl['clips'][s['clip']]
    d = s['out'] - s['in']
    p = f'{tmp}/s{i:04d}.mp4'
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', f"{s['in']:.4f}", '-t', f'{d:.4f}', '-i', f"{PX}/{s['clip']}.mp4"]
    if c.get('mic'):
        cmd += ['-ss', f"{s['in'] + c['offset']:.4f}", '-t', f'{d:.4f}', '-i', f"{MIC}/{c['mic']}", '-map', '0:v', '-map', '1:a']
    else:
        cmd += ['-map', '0:v', '-map', '0:a?']
    cmd += ['-vf', f'scale={W}:{H},fps=30', '-ar', '48000', '-ac', '2', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '26', '-c:a', 'aac', '-b:a', '128k', p]
    subprocess.run(cmd, check=True)
    parts.append(p)
lst = f'{tmp}/list.txt'
open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
base = f'{tmp}/base.mp4'
subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', base], check=True)


def esc(t):
    return t.replace('\\', '\\\\').replace(':', '\\:').replace("'", "’").replace('%', '\\%')


inputs = ['-i', base]
fc = []
cur = '[0:v]'
k = 0
for j, ins in enumerate(edl.get('inserts', [])):
    inputs += ['-ss', f"{ins['in']:.3f}", '-t', f"{ins['out'] - ins['in']:.3f}", '-i', f"{PX}/{ins['clip']}.mp4"]
    k += 1
    sc = ins.get('scale', 1.0)
    fc.append(f"[{k}:v]scale={int(W * sc)}:{int(H * sc)},setpts=PTS-STARTPTS+{ins['at']:.3f}/TB[i{j}]")
    fc.append(f"{cur}[i{j}]overlay=x=(W-w)/2:y=(H-h)/2:enable='between(t,{ins['at']:.3f},{ins['at'] + ins['out'] - ins['in']:.3f})'[v{j}]")
    cur = f'[v{j}]'
dt = []
for s in edl.get('subs', []):
    lines = s['text'].split('\n')
    for li, ln in enumerate(lines):
        y = int(H * 0.5 + 432.992 / 1920 * H * 2 * 0.5 + (li - (len(lines) - 1)) * 34)  # 型の位置 0 -432.992（中央から下へ）
        dt.append(f"drawtext=fontfile={FONT}:text='{esc(ln)}':fontsize=28:fontcolor=white:borderw=2:bordercolor=black@0.5:x=(w-text_w)/2:y={y}:enable='between(t,{s['at']:.3f},{s['at'] + s['dur']:.3f})'")
for c in edl.get('cards', []):
    big = c['kind'] in ('product', 'price', 'hook')
    for li, ln in enumerate(c['lines']):
        fs = (34 if li == 0 else 16) if big else 18
        y = {'product': H * 0.45, 'price': H * 0.40, 'release': H * 0.52, 'hook': H * 0.70, 'height': H * 0.18, 'product_side': H * 0.45}.get(c['kind'], H * 0.5) + li * (fs + 8)
        x = '(w-text_w)/2' if c['kind'] != 'height' else '30'
        f = SERIF if c['kind'] != 'hook' else FONT
        dt.append(f"drawtext=fontfile={f}:text='{esc(ln)}':fontsize={fs}:fontcolor=white:borderw=1:bordercolor=black@0.4:x={x}:y={int(y)}:enable='between(t,{c['at']:.3f},{c['at'] + c['dur']:.3f})'")
if dt:
    fc.append(f"{cur}{','.join(dt)}[vo]")
    cur = '[vo]'
cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y'] + inputs
if fc:
    cmd += ['-filter_complex', ';'.join(fc), '-map', cur, '-map', '0:a']
cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-c:a', 'aac', '-b:a', '128k', OUT]
subprocess.run(cmd, check=True)
print(OUT)
