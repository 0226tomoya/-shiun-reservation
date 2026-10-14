"""ショートの編集表（EDL）のカットを、ユーザー（編集者）の詰め方に合わせて詰め直す。
python3 short_jetcut.py edl.json mic_dir out.json

基準（10/13、ユーザーが直したショート 4 本・303 カット）:
- カットの中に 0.08 秒を超える間を残さない（その間で切って詰める。ユーザーのカットには 0.12 秒を超える間は 1 つも無い）
- 頭は声の判定（全体の音量か 3〜8kHz の音量がノイズの底 +8dB 超）の出だしから 0.02 秒後、尾は判定の終わりの 0.08 秒前（判定は息・残響も拾うので、ユーザーの切り位置に合わせた値）
- 0.20 秒未満の声のかたまり（息・舌打ち・物音）は、前後の声に付いていなければ捨てる
どの発言を使うか（中身の選び方）は変えない。EDL の各カットの範囲の中だけで詰める。
"""
import json
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfiltfilt

SR = 48000
F = int(0.005 * SR)
GAP = 0.08  # かたまりをつなぐ間の上限。10/14 cut_score.py で 0.12→0.08 で 4 本平均 75.2→76.2 点（0.06 は 77.8 点だが尾の切れがユーザーより増えるので見送り）
HEAD, TAIL = -0.020, -0.115  # 声の判定の出だしから 0.02 秒後・終わりの 0.115 秒前（10/14 cut_score.py で 4 本の点が最も高く、尾の切れはユーザーのカット以下。前は -0.080）
MIN_BLOB = 0.20


def voiced(path):
    x = np.frombuffer(subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    h = sosfiltfilt(butter(4, [3000, 8000], btype='band', fs=SR, output='sos'), x)
    n = len(x) // F
    db = lambda y: 10 * np.log10(np.mean(y[:n * F].reshape(n, F) ** 2, axis=1) + 1e-12)
    e, hh = db(x), db(h)
    return np.maximum(e - np.percentile(e, 10), hh - np.percentile(hh, 10)) > 8


def blobs(v, a, b):
    """[a, b)（フレーム）の中の声のかたまりを、間 GAP 以下ならつないで返す"""
    seg = v[a:b]
    out = []
    i = 0
    while i < len(seg):
        if seg[i]:
            j = i
            while j < len(seg) and seg[j]:
                j += 1
            if out and (i - out[-1][1]) * 0.005 <= GAP:
                out[-1][1] = j
            else:
                out.append([i, j])
            i = j
        else:
            i += 1
    return [(a + s, a + e) for s, e in out]


CONNECT = {'で', 'そして', 'あと', 'なので', 'で、', 'そして、', 'と', 'は', 'が', 'を', 'に', 'も', 'ね', 'よ'}


def words_of(mic_dir, mic):
    """文字起こし（scratchpad/short_src/asr/<マイク>.json と同じ形）の単語。無ければ空"""
    import os
    for d in (os.environ.get('SHORT_ASR_DIR', ''), mic_dir + '/../../asr'):
        f = os.path.join(d, mic[:-4] + '.json')
        if d and os.path.exists(f):
            return [w for sg in json.load(open(f)) for w in sg['words']]
    return []


def main():
    edl = json.load(open(sys.argv[1]))
    mic_dir = sys.argv[2]
    drop = '--drop-connectors' in sys.argv  # つなぎの言葉だけのかたまり（0.6 秒未満）を抜く（ユーザーの直しの傾向）
    cache = {}
    new = []
    for s in edl['segments']:
        c = edl['clips'][s['clip']]
        if not c.get('mic'):
            new.append(s)
            continue
        if c['mic'] not in cache:
            cache[c['mic']] = voiced(f"{mic_dir}/{c['mic']}")
        v = cache[c['mic']]
        off = c['offset']
        a, b = int((s['in'] + off) * SR / F), int((s['out'] + off) * SR / F)
        bl = [x for x in blobs(v, a, b) if (x[1] - x[0]) * 0.005 >= MIN_BLOB]
        if drop:
            W = cache.setdefault(('w', c['mic']), words_of(mic_dir, c['mic']))
            keep = []
            for s0, s1 in bl:
                t0, t1 = s0 * 0.005, s1 * 0.005
                txt = ''.join(w['word'] for w in W if w['end'] > t0 + 0.02 and w['start'] < t1 - 0.02).strip('、。 ')
                if t1 - t0 < 0.6 and txt in CONNECT:
                    continue
                keep.append((s0, s1))
            bl = keep
        for s0, s1 in bl:
            t0 = max(s['in'], s0 * 0.005 - off - HEAD)
            t1 = min(s['out'], s1 * 0.005 - off + TAIL)
            if t1 - t0 >= 0.15:
                new.append({**s, 'in': round(t0, 4), 'out': round(t1, 4)})
    old_len = sum(x['out'] - x['in'] for x in edl['segments'])
    new_len = sum(x['out'] - x['in'] for x in new)
    edl = {**edl, 'segments': new}
    json.dump(edl, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
    d = sorted(x['out'] - x['in'] for x in new)
    print(f'カット {len(new)}・長さ {old_len:.1f} → {new_len:.1f} 秒・中央値 {d[len(d) // 2]:.2f} 秒')


if __name__ == '__main__':
    main()
