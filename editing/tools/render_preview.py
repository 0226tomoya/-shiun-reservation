"""確認用の動画を書き出す: 撮影データのプロキシ（メインカメラ）＋構図（調整レイヤーの拡大・位置）＋テロップ＋インサート（素材がないものは枠）＋ピンマイク音声。

    python3 render_preview.py EDIT.fcpxml FLAT.json PROXY_DIR AUDIO.wav OUT.mp4 [--from 秒 --to 秒] [--lut FILE.cube]

- PROXY_DIR: `<素材名>_<番号>.mp4` と、その頭の素材内時刻を書いた `<…>.mp4.start`（960x540・全フレームがキーフレーム）
- 長さはシーケンスのフレーム数で決める（59.94p）。カットを重ねてもずれが積み上がらない
- テロップは preview_frames と同じ描き方（フォントは近いもので代用）
"""
import glob
import json
import unicodedata
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


MEDIA = {'map': [], 'vid': None}
_img_cache = {}


def local_file(src):
    """XML の素材パスを、手元に取り込んだファイルに置き換える（--media の map: [部分文字列, 手元のフォルダ]）。"""
    if not src:
        return None
    for sub, d in MEDIA['map']:
        if sub in src:
            rel = src.split(sub, 1)[1]
            for cand in (rel, os.path.splitext(rel)[0] + '.jpg', os.path.splitext(rel)[0] + '.JPG', os.path.splitext(rel)[0] + '.png'):
                p = os.path.join(d, cand)
                if os.path.exists(p):
                    return p
    return None


def vid_proxy(i):
    """EC 動画・LOOK 動画のプロキシ（--media の vid/<素材名>/proxy.mp4）。"""
    if not MEDIA['vid'] or not i.get('src'):
        return None
    name = os.path.splitext(os.path.basename(i['src']))[0]
    p = os.path.join(MEDIA['vid'], name, 'proxy.mp4')
    return p if os.path.exists(p) else None


def mid_value(v, default):
    if isinstance(v, dict):  # キーフレーム（パン）は真ん中の値で近似
        ks = v.get('keyframes') or []
        if ks:
            a, b = ks[0][1].split(), ks[-1][1].split()
            return ' '.join(str((float(x) + float(y)) / 2) for x, y in zip(a, b))
        return v.get('value') or default
    return v or default


def draw_image(im, i, path):
    """FCP の置き方で画像を描く: 画面に収まる大きさ（アスペクト維持）→ 拡大 → 位置（1 単位 = 画面の高さの 1%）。"""
    from PIL import ImageFilter
    tr = i.get('adjust-transform') or {}
    sc = float(str(mid_value(tr.get('scale'), '1 1')).split()[0])
    x, y = (float(v) for v in str(mid_value(tr.get('position'), '0 0')).split()[:2])
    blur = any(f['name'] == 'ガウス' for f in i.get('filters', []))
    key = (path, round(sc, 3), blur)
    if key not in _img_cache:
        src = Image.open(path)
        src.draft('RGB', (2400, 2400))
        src = src.convert('RGBA')
        fit = min(pf.W / src.width, pf.H / src.height)
        w, h = max(1, int(src.width * fit * sc)), max(1, int(src.height * fit * sc))
        src = src.resize((w, h))
        if blur:
            src = src.filter(ImageFilter.GaussianBlur(28))
        _img_cache[key] = src
    img = _img_cache[key]
    cx, cy = pf.W / 2 + x * 10.8, pf.H / 2 - y * 10.8
    im.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2))) if (
        cx - img.width / 2 >= 0 and cy - img.height / 2 >= 0 and cx + img.width / 2 <= pf.W and cy + img.height / 2 <= pf.H) else \
        _paste_clip(im, img, int(cx - img.width / 2), int(cy - img.height / 2))


def _paste_clip(im, img, x0, y0):
    L, T_ = max(0, x0), max(0, y0)
    R, B = min(pf.W, x0 + img.width), min(pf.H, y0 + img.height)
    if R <= L or B <= T_:
        return
    im.alpha_composite(img.crop((L - x0, T_ - y0, R - x0, B - y0)), (L, T_))


def overlay_frame(items, t):
    """メインカメラ以外（テロップ・インサート・挿入素材）を透明の上に描く。動画のインサートは土台側で入れるので描かない。"""
    im = Image.new('RGBA', (pf.W, pf.H), (0, 0, 0, 0))
    act = [i for i in items if i['t0'] <= t < i['t1'] and i['tag'] != 'mc-clip' and i['lane'] not in (None, '-1')
           and role(i) not in ('adjustment_main', 'adjustment_other') and not str(i['lane']).startswith('in')]
    act.sort(key=lambda i: int(i['lane']) if str(i['lane']).lstrip('-').isdigit() else 0)
    # 画面全体を覆う動画のインサート（土台に差し替え済み）より下のレーンは、FCP でも隠れるので描かない
    vlanes = [int(i['lane']) for i in act if i['tag'] in ('asset-clip', 'clip') and str(i['lane']).isdigit() and vid_proxy(i)
              and not (i.get('path') and i['path'][0] == 'Adjustment Layer')]
    floor = max(vlanes) if vlanes else -99
    act = [i for i in act if not (str(i['lane']).lstrip('-').isdigit() and int(i['lane']) < floor)]
    for i in act:
        if i['tag'] == 'title':
            pf.draw_title(im, i)
        elif i['tag'] in ('asset-clip', 'clip') and vid_proxy(i):
            continue
        elif any(k in unicodedata.normalize('NFC', (i['name'] or '') + '/' + '/'.join(i.get('path') or [])) for k in ('サイズスペック線',)) \
                or unicodedata.normalize('NFC', i['name'] or '') == 'カスタム':
            continue  # 身長別比較の枠・線（Mac のダウンロードにある部品で、手元にない）
        elif local_file(i.get('src')):
            draw_image(im, i, local_file(i.get('src')))
        else:
            pf.draw_media(im, i, (i['name'] or '')[:30] + ('（ぼかし）' if any(f['name'] == 'ガウス' for f in i.get('filters', [])) else ''))
    return im.resize((W, H))


def main():
    edit, flat, pdir, audio, out = sys.argv[1:6]
    opt = dict(zip(sys.argv[6::2], sys.argv[7::2]))
    if opt.get('--media'):
        MEDIA.update(json.load(open(opt['--media'], encoding='utf-8')))
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
        sz = [c for c in e if c.tag == 'asset-clip' and (c.get('lane') or '').isdigit()] if e.tag == 'title' else []
        if src is None and sz and MEDIA['vid']:
            # 身長別比較のブロック: 2 本の動画を FCP の位置・拡大・切り取りどおりに並べる（下: lane 1、上: lane 2）
            ins, fcx, last = [], [f'color=c=black:s={W}x{H}:r={fps}:d={float(t - s) + 1:.3f}[bg]'], 'bg'
            for c in sorted(sz, key=lambda c: int(c.get('lane'))):
                pp_ = os.path.join(MEDIA['vid'], c.get('name'), 'proxy.mp4')
                if not os.path.exists(pp_):
                    continue
                ss_ = T(c.get('start') or '0s') + (s - off) + (T(e.get('start')) - T(c.get('offset')))
                ins += ['-ss', f'{float(ss_):.4f}', '-i', pp_]
                k_ = len(ins) // 4 - 1
                tr_ = c.find('adjust-transform')
                x_, y_ = (float(v) for v in ((tr_.get('position') if tr_ is not None else None) or '0 0').split())
                sc_ = float(((tr_.get('scale') if tr_ is not None else None) or '1 1').split()[0])
                cr_ = c.find('adjust-crop/trim-rect')
                # 切り取り（trim-rect）の値は位置と同じく画面の高さの %
                L_, R_, Tp_, B_ = (float(cr_.get(k, 0)) * H / 100 if cr_ is not None else 0 for k in ('left', 'right', 'top', 'bottom'))
                sw_, sh_ = int(round(W * sc_ / 2) * 2), int(round(H * sc_ / 2) * 2)
                cw_, ch_ = int(sw_ - (L_ + R_) * sc_) // 2 * 2, int(sh_ - (Tp_ + B_) * sc_) // 2 * 2
                cx0, cy0 = int(L_ * sc_), int(Tp_ * sc_)
                ox = int(W / 2 + x_ * H / 100 - sw_ / 2 + cx0)
                oy = int(H / 2 - y_ * H / 100 - sh_ / 2 + cy0)
                # ガウス（FCP の Amount 0〜1）: 0.5 で顔が判別できない強さ（確認動画の近似）
                g_ = next((f_ for f_ in c.findall('filter-video') if f_.get('name') == 'ガウス'), None)
                amt = float(next((q.get('value') for q in g_.findall('param') if q.get('name') == 'Amount'), '0.2')) if g_ is not None else 0
                blur_ = f',gblur=sigma={max(1.0, amt * 40 * sc_):.1f}' if g_ is not None else ''
                fcx.append(f'[{k_}:v]fps={fps},scale={sw_}:{sh_}{blur_},crop={cw_}:{ch_}:{cx0}:{cy0}[v{k_}]')
                fcx.append(f'[{last}][v{k_}]overlay={ox}:{oy}:eof_action=pass[o{k_}]')
                last = f'o{k_}'
            if os.environ.get('RP_DEBUG'):
                print('合成:', ';'.join(fcx), file=sys.stderr)
            ff(ins + ['-filter_complex', ';'.join(fcx), '-map', f'[{last}]', '-frames:v', str(n), '-an',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-g', '1', '-pix_fmt', 'yuv420p', seg])
            segs.append(seg)
            continue
        if src is None and e.tag == 'asset-clip':
            # スパインに直接置いた素材（カウントダウンなど）: 手元に取り込んだファイルがあればそのまま描く
            import unicodedata as _ud0
            import urllib.parse as _up0
            a_ = res.get(e.get('ref'))
            mr_ = a_.find('media-rep') if a_ is not None else None
            lf_ = local_file(_ud0.normalize('NFC', _up0.unquote(mr_.get('src')))) if mr_ is not None else None
            if lf_:
                ss_ = T(e.get('start') or '0s') - T(a_.get('start') or '0s') + (s - off)
                ff(['-ss', f'{float(ss_):.4f}', '-i', lf_, '-frames:v', str(n), '-vf', f'scale={W}:{H},fps={fps}', '-an',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-g', '1', '-pix_fmt', 'yuv420p', seg])
                segs.append(seg)
                continue
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

    # EC 動画・LOOK 動画（画面全体を覆うインサート）の区間は、土台をその動画のプロキシに差し替える
    import unicodedata as _ud
    import urllib.parse as _up
    a_start = {}
    for r_ in res.values():
        if r_.tag == 'asset' and r_.find('media-rep') is not None:
            a_start[_ud.normalize('NFC', _up.unquote(r_.find('media-rep').get('src')))] = T(r_.get('start') or '0s')
    evs = []
    for i in items:
        if i['tag'] in ('asset-clip', 'clip') and str(i['lane']).isdigit() and int(i['lane']) >= 3 and vid_proxy(i) \
                and not (i.get('path') and i['path'][0] == 'Adjustment Layer'):  # 身長別比較のブロックの中の動画は土台側で合成済み
            t0_, t1_ = round(Fraction(i['t0']) / FD) * FD, round(Fraction(i['t1']) / FD) * FD
            if t1_ <= a0 or t0_ >= a1:
                continue
            off_in = T(i.get('start_attr') or '0s') - a_start.get(i.get('src'), 0)
            evs.append((max(t0_, a0), min(t1_, a1), int(i['lane']), vid_proxy(i), off_in + (max(t0_, a0) - t0_)))
    if evs:
        pts = sorted({a0, a1} | {x for e_ in evs for x in e_[:2]})
        parts = []
        for k, (s_, t_) in enumerate(zip(pts, pts[1:])):
            cov = [e_ for e_ in evs if e_[0] <= s_ and t_ <= e_[1]]
            n_ = int(round((t_ - s_) / FD))
            if n_ <= 0:
                continue
            if cov:
                e_ = max(cov, key=lambda x: x[2])
                p_ = os.path.join(tmp, f'ev{k:05d}.mp4')
                ff(['-ss', f'{float(e_[4] + (s_ - e_[0])):.4f}', '-i', e_[3], '-frames:v', str(n_), '-vf', f'fps={fps}', '-an',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-g', '1', '-pix_fmt', 'yuv420p', p_])
                parts.append(f"file '{p_}'\n")
            else:
                parts.append(f"file '{base}'\ninpoint {float(s_ - a0):.6f}\noutpoint {float(t_ - a0):.6f}\n")
        lst2 = os.path.join(tmp, 'base2.txt')
        open(lst2, 'w').write(''.join(parts))
        base2 = os.path.join(tmp, 'base2.mp4')
        ff(['-f', 'concat', '-safe', '0', '-i', lst2, '-vf', f'fps={fps}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
            '-g', '1', '-pix_fmt', 'yuv420p', base2])
        base = base2
        print('EC/LOOK 動画の差し替え', len(evs), '本', flush=True)
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
