"""ショートの編集表（EDL）の全カットについて、語の頭・尾が切れていないかをピンマイクの音で確かめる。
python3 cut_check.py edl.json mic_dir [--asr]
- 子音（サ・シ・ス・ハ・カ・タ行）や文末の「す」「た」は全体の音量では小さいので、高い帯域（3〜8kHz）の音量でも見る
- 5ms ごとに「声あり」（全体の音量か高い帯域の音量がノイズの底 +8dB 超）を決め、次を数える（基準はユーザーが直したショート 4 本）:
  切れ: 声が始まって 0.05 秒以上たった所から始まる／声が 0.12 秒以上続くのに終わる（ユーザーのカットでも 1 本に 6〜8 か所。初版は 80 か所）
  詰め足りない: 頭に 0.03 秒・尾に 0.04 秒を超える無音／カットの中に 0.12 秒を超える間
- 同じクリップの前後のカットで元の時刻が重なる（同じ音が 2 度鳴る）所も出す
- --asr: 本線の音をつないで faster-whisper で起こし直し、字幕と並べて出す（耳の代わりの突き合わせ）
"""
import sys, json, subprocess, os
import numpy as np
from scipy.signal import butter, sosfiltfilt

edl = json.load(open(sys.argv[1])); MIC = sys.argv[2]; ASR = '--asr' in sys.argv
SR = 48000
W = int(0.010 * SR)
EDGE = 0.030
sos = butter(4, [3000, 8000], btype='band', fs=SR, output='sos')
cache = {}


def mic(name):
    if name not in cache:
        raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', f'{MIC}/{name}', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32).astype(np.float64)
        hf = sosfiltfilt(sos, x)
        n = len(x) // W
        db = lambda y: 10 * np.log10(np.mean(y[:n * W].reshape(n, W) ** 2, axis=1) + 1e-12)
        e, h = db(x), db(hf)
        cache[name] = (x, hf, np.percentile(e, 10), np.percentile(h, 10))
    return cache[name]


def lvl(y):
    return 10 * np.log10(np.mean(y ** 2) + 1e-12) if len(y) else -120


# 5ms ごとに「声あり」を決める（全体の音量か 3〜8kHz の音量が、ノイズの底 +8dB を超える）
F = int(0.005 * SR)
vcache = {}


def voiced(name):
    if name not in vcache:
        x, hf, fe, fh = mic(name)
        n = len(x) // F
        db = lambda y: 10 * np.log10(np.mean(y[:n * F].reshape(n, F) ** 2, axis=1) + 1e-12)
        vcache[name] = np.maximum(db(x) - fe, db(hf) - fh) > 8
    return vcache[name]


# 基準はユーザー（編集者）が直したショート 4 本のカット 303 本（10/13）:
#   頭は声の出だしの 0.005 秒前（中央値）、尾は声の終わりの残響の 0.01 秒内側（中央値）。カットの中に 0.12 秒を超える間は 1 つも無い
HEAD_CLIP, TAIL_CLIP = 0.050, 0.120   # これ以上、声の途中から始まる／声の途中で終わる → 切れ（ユーザーのカットでも 1 本に 6〜8 か所はある。言い直しを途中で切る所。多すぎないかを見る）
HEAD_LOOSE, TAIL_LOOSE = 0.030, 0.040  # これ以上、無音を残している → 詰め足りない
GAP_MAX = 0.12                         # カットの中の間（ま）の上限
bad_head, bad_tail, over, loose_head, loose_tail, gaps = [], [], [], [], [], []
t = 0.0
for i, s in enumerate(edl['segments']):
    c = edl['clips'][s['clip']]
    d = s['out'] - s['in']
    if not c.get('mic'):
        t += d
        continue
    v = voiced(c['mic'])
    ia, ib = int((s['in'] + c['offset']) * SR / F), int((s['out'] + c['offset']) * SR / F)
    sub = next((u['text'] for u in edl.get('subs', []) if u['at'] <= t + 0.05 < u['at'] + u['dur']), '')
    seg = v[ia:ib]
    if seg.any():
        if v[ia]:  # 声の途中から始まっている長さ
            k = ia
            while k > 0 and v[k - 1]:
                k -= 1
            if (ia - k) * 0.005 >= HEAD_CLIP:
                bad_head.append((i, round(t, 2), round((ia - k) * 0.005, 3), sub))
        else:
            lead = int(np.argmax(seg)) * 0.005
            if lead > HEAD_LOOSE:
                loose_head.append((i, round(t, 2), round(lead, 3), sub))
        if v[ib - 1]:
            k = ib
            while k < len(v) and v[k]:
                k += 1
            if (k - ib) * 0.005 >= TAIL_CLIP:
                bad_tail.append((i, round(t + d, 2), round((k - ib) * 0.005, 3), sub))
        else:
            trail = int(np.argmax(seg[::-1])) * 0.005
            if trail > TAIL_LOOSE:
                loose_tail.append((i, round(t + d, 2), round(trail, 3), sub))
        idx = np.where(seg)[0]
        run = 0
        for x_ in seg[idx[0]:idx[-1] + 1]:
            if not x_:
                run += 1
            else:
                if run * 0.005 > GAP_MAX:
                    gaps.append((i, round(t, 2), round(run * 0.005, 3), sub))
                run = 0
    t += d
for i, (p, q) in enumerate(zip(edl['segments'], edl['segments'][1:])):
    if p['clip'] == q['clip'] and q['in'] < p['out'] - 0.005 and q['out'] > p['in']:
        over.append((i + 1, round(p['out'] - q['in'], 3)))

print(f'カット {len(edl["segments"])}・頭が切れていそう {len(bad_head)}・尾が切れていそう {len(bad_tail)}・音が重なる継ぎ目 {len(over)}'
      f'・詰め足りない頭 {len(loose_head)}・尾 {len(loose_tail)}・{GAP_MAX} 秒を超える間 {len(gaps)}')
for name, L in (('頭の切れ', bad_head), ('尾の切れ', bad_tail), ('頭の無音', loose_head), ('尾の無音', loose_tail), ('間', gaps)):
    for i, at, v_, sub in L:
        print(f'  {name} #{i} {at:6.2f}s {v_}秒 「{sub}」')
for i, ov in over:
    print(f'  重なり #{i} {ov}s')

if ASR:
    from faster_whisper import WhisperModel
    parts = []
    for s in edl['segments']:
        c = edl['clips'][s['clip']]
        if not c.get('mic'):
            parts.append(np.zeros(int((s['out'] - s['in']) * SR)))
            continue
        x = mic(c['mic'])[0]
        parts.append(x[int((s['in'] + c['offset']) * SR):int((s['out'] + c['offset']) * SR)])
    y = np.concatenate(parts).astype(np.float32)
    y16 = y[::3]  # 48k → 16k（声の帯域なら足りる）
    m = WhisperModel('medium', device='cpu', compute_type='int8')
    segs, _ = m.transcribe(y16, language='ja', word_timestamps=True, beam_size=5, condition_on_previous_text=False)
    words = [(w.start, w.end, w.word) for sg in segs for w in sg.words]
    print('\n起こし直し（時刻・字幕・聞こえた語）:')
    for u in edl.get('subs', []):
        heard = ''.join(w for a, b, w in words if a < u['at'] + u['dur'] and b > u['at'])
        print(f"  {u['at']:6.2f}  {u['text'].replace(chr(10), ' ')}  ｜  {heard}")
