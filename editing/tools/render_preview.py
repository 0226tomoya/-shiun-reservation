"""確認用の動画を書き出す: 撮影データのプロキシ（メインカメラ）＋構図（調整レイヤーの拡大・位置）＋テロップ＋インサート（素材がないものは枠）＋ピンマイク音声。

    python3 render_preview.py EDIT.fcpxml FLAT.json PROXY_DIR AUDIO.wav OUT.mp4 [--from 秒 --to 秒] [--lut FILE.cube]

- PROXY_DIR: `<素材名>_<番号>.mp4` と、その頭の素材内時刻を書いた `<…>.mp4.start`（960x540・全フレームがキーフレーム）
- 長さはシーケンスのフレーム数で決める（59.94p）。カットを重ねてもずれが積み上がらない
- テロップは preview_frames と同じ描き方（フォントは近いもので代用）
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from fractions import Fraction

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preview_frames as pf  # noqa: E402
from roles import role  # noqa: E402

W, H = 960, 540


def T(s):
    return Fraction((s or '0s').rstrip('s'))


def ff(args):
    r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-500:])


def probe_dur(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                capture_output=True, text=True).stdout)


def overlay_frame(items, t):
    """メインカメラ以外（テロップ・インサート・挿入素材）を透明の上に描く。"""
    im = Image.new('RGBA', (pf.W, pf.H), (0, 0, 0, 0))
    act = [i for i in items if i['t0'] <= t < i['t1'] and i['tag'] != 'mc-clip' and i['lane'] not in (None, '-1')
           and role(i) not in ('adjustment_main', 'adjustment_other') and not str(i['lane']).startswith('in')]
    act.sort(key=lambda i: int(i['lane']) if str(i['lane']).lstrip('-').isdigit() else 0)
    for i in act:
        if i['tag'] == 'title':
            pf.draw_title(im, i)
        else:
            pf.draw_media(im, i, (i['name'] or '')[:30] + ('（ぼかし）' if any(f['name'] == 'ガウス' for f in i.get('filters', [])) else ''))
    return im.resize((W, H))


def main():
    edit, flat, pdir, audio, out = sys.argv[1:6]
    opt = dict(zip(sys.argv[6::2], sys.argv[7::2]))
    lut = opt.get('--lut')
    root = ET.parse(edit).getroot()
    res = {e.get('id'): e for e in root.find('resources')}
    proj = [p for p in root.iter('project') if p.get('name') == '本編'][0]
    seq = proj.find('sequence')
    FD = T(res[seq.get('format')].get('frameDuration'))
    fps = f'{FD.denominator}/{FD.numerator}'
    spine = [e for e in seq.find('spine') if e.get('offset') is not None]
    total = T(seq.get('duration'))
    a0 = Fraction(opt.get('--from', '0'))
    a1 = Fraction(opt['--to']) if '--to' in opt else total
    a0, a1 = round(a0 / FD) * FD, round(a1 / FD) * FD

    # マルチカムの映像アングル: マルチカム内時刻 → 素材名と素材内時刻
    def angle_map(mc_ref):
        mc = res[mc_ref].find('multicam')
        ang = next(a for a in mc.findall('mc-angle') if any(c.tag == 'asset-clip' and res[c.get('ref')].get('hasVideo') == '1' for c in a))
        return [(T(c.get('offset')), T(c.get('duration')), T(c.get('start') or res[c.get('ref')].get('start')), c.get('name'))
                for c in ang if c.tag == 'asset-clip']

    maps = {}
    proxies = {}
    for p in glob.glob(os.path.join(pdir, '*.mp4')):
        if p.endswith('.part.mp4') or not os.path.exists(p + '.start'):
            continue
        name = os.path.basename(p).rsplit('_', 1)[0]
        s = float(open(p + '.start').read())
        proxies.setdefault(name, []).append((s, s + probe_dur(p), p))

    tmp = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(out)))
    segs, missing = [], 0
    for k, e in enumerate(spine):
        off, du = T(e.get('offset')), T(e.get('duration'))
        s, t = max(off, a0), min(off + du, a1)
        if t <= s:
            continue
        n = int((t - s) / FD)
        if n <= 0:
            continue
        seg = os.path.join(tmp, f'{k:05d}.mp4')
        src = None
        if e.tag == 'mc-clip':
            if e.get('ref') not in maps:
                maps[e.get('ref')] = angle_map(e.get('ref'))
            tau = T(e.get('start')) + (s - off)
            for o, d, st, name in maps[e.get('ref')]:
                if o <= tau < o + d:
                    st_src = float(st + tau - o)
                    src = next(((ps, pp) for ps, pe, pp in proxies.get(name, []) if ps <= st_src and st_src + float(t - s) <= pe + 0.05), None)
                    break
        if src is not None:
            ps, pp = src
            # 調整レイヤー（lane 1）の構図: 位置は画面の高さの 1%（540p で 5.4px）、拡大は中心から
            vf = []
            adj = next((c for c in e if c.tag == 'title' and c.get('lane') == '1'), None)
            tr = adj.find('adjust-transform') if adj is not None else None
            if tr is not None:
                x, y = (float(v) for v in (tr.get('position') or '0 0').split())
                sc = float((tr.get('scale') or '1 1').split()[0])
                sw, sh = int(round(W * sc / 2) * 2), int(round(H * sc / 2) * 2)
                cx = (sw - W) / 2 - x * 5.4
                cy = (sh - H) / 2 + y * 5.4
                vf.append(f'scale={sw}:{sh}')
                if sc >= 1:
                    vf.append(f'crop={W}:{H}:{max(0, min(sw - W, cx)):.0f}:{max(0, min(sh - H, cy)):.0f}')
                else:
                    vf.append(f'pad={W}:{H}:{max(0, -cx):.0f}:{max(0, -cy):.0f}')
            if lut:
                vf.append(f'lut3d={lut}')
            vf.append(f'fps={fps}')
            ff(['-ss', f'{st_src - ps:.4f}', '-i', pp, '-frames:v', str(n), '-vf', ','.join(vf), '-an',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-g', '1', '-pix_fmt', 'yuv420p', seg])
        else:
            if e.tag == 'mc-clip':
                missing += 1
            label = (e.get('name') or e.tag).replace(':', ' ').replace("'", '')
            col = '0x202020' if e.tag != 'mc-clip' else '0x803030'
            txt = f'挿入: {label}' if e.tag != 'mc-clip' else 'プロキシなし'
            ff(['-f', 'lavfi', '-i', f'color=c={col}:s={W}x{H}:r={fps}', '-frames:v', str(n),
                '-vf', f"drawtext=fontfile={pf.SANS}:text='{txt}':x=40:y=40:fontsize=28:fontcolor=white",
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-g', '1', '-pix_fmt', 'yuv420p', seg])
        segs.append(seg)
        if len(segs) % 100 == 0:
            print('base', len(segs), flush=True)
    lst = os.path.join(tmp, 'base.txt')
    open(lst, 'w').write(''.join(f"file '{p}'\n" for p in segs))
    base = os.path.join(tmp, 'base.mp4')
    ff(['-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', base])

    # テロップ・インサートの層（表示が変わる瞬間ごとに 1 枚）
    items = [i for i in json.load(open(flat)) if i['enabled'] != '0' and len(i['path']) <= 1]
    vis = [i for i in items if i['tag'] != 'mc-clip' and i['lane'] not in (None, '-1') and role(i) not in ('adjustment_main', 'adjustment_other')
           and not str(i['lane']).startswith('in')]
    f0, f1 = float(a0), float(a1)
    pts = sorted({x for i in vis for x in (i['t0'], i['t1']) if f0 < x < f1} | {f0, f1})
    pts = [round(x / float(FD)) * float(FD) for x in pts]
    pts = sorted(set(pts))
    lines = []
    for k, (s, t) in enumerate(zip(pts, pts[1:])):
        p = os.path.join(tmp, f'o{k:05d}.png')
        overlay_frame(items, (s + t) / 2).save(p)
        lines.append(f"file '{p}'\nduration {t - s:.6f}\n")
    lines.append(f"file '{p}'\n")
    olst = os.path.join(tmp, 'ovl.txt')
    open(olst, 'w').write(''.join(lines))
    ovl = os.path.join(tmp, 'ovl.mov')
    ff(['-f', 'concat', '-safe', '0', '-i', olst, '-vf', f'fps={fps},format=rgba', '-c:v', 'qtrle', ovl])

    draw = (f"drawtext=fontfile={pf.SANS}:text='%{{eif\\:floor((t+{f0})/60)\\:d}}\\:%{{eif\\:mod(floor(t+{f0})\\,60)\\:d\\:2}}"
            f".%{{eif\\:floor(mod((t+{f0})*10\\,10))\\:d}}':x=w-tw-8:y=h-th-8:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.7")
    ff(['-i', base, '-i', ovl, '-ss', f'{f0:.4f}', '-t', f'{f1 - f0:.4f}', '-i', audio,
        '-filter_complex', f'[0:v][1:v]overlay=0:0:shortest=1,{draw}[v]', '-map', '[v]', '-map', '2:a',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k',
        '-movflags', '+faststart', out])
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print(f'-> {out} ({os.path.getsize(out) / 1e6:.1f}MB)  プロキシなしのカット: {missing}')


if __name__ == '__main__':
    main()
