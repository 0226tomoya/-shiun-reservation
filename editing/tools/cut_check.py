"""ショートの編集表（EDL）の全カットについて、語の頭・尾が切れていないかをピンマイクの音で確かめる。
python3 cut_check.py edl.json mic_dir [--asr]
- 子音（サ・シ・ス・ハ・カ・タ行）や文末の「す」「た」は全体の音量では小さいので、高い帯域（3〜8kHz）の音量でも見る
- 各カットの頭・尾 30ms で、全体の音量か高い帯域の音量がノイズの底 +8dB を超えていたら「切れている」とする
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


rows, bad_head, bad_tail, over = [], [], [], []
t = 0.0
for i, s in enumerate(edl['segments']):
    c = edl['clips'][s['clip']]
    d = s['out'] - s['in']
    if not c.get('mic'):
        t += d
        continue
    x, hf, fe, fh = mic(c['mic'])
    a, b = int((s['in'] + c['offset']) * SR), int((s['out'] + c['offset']) * SR)
    k = int(EDGE * SR)
    he, hh = lvl(x[a:a + k]) - fe, lvl(hf[a:a + k]) - fh
    te, th = lvl(x[b - k:b]) - fe, lvl(hf[b - k:b]) - fh
    sub = next((u['text'] for u in edl.get('subs', []) if u['at'] <= t + 0.05 < u['at'] + u['dur']), '')
    if max(he, hh) > 8:
        bad_head.append((i, round(t, 2), round(he, 1), round(hh, 1), sub))
    if max(te, th) > 8:
        bad_tail.append((i, round(t + d, 2), round(te, 1), round(th, 1), sub))
    t += d
for i, (p, q) in enumerate(zip(edl['segments'], edl['segments'][1:])):
    if p['clip'] == q['clip'] and q['in'] < p['out'] - 0.005 and q['out'] > p['in']:
        over.append((i + 1, round(p['out'] - q['in'], 3)))

print(f'カット {len(edl["segments"])}・頭が切れていそう {len(bad_head)}・尾が切れていそう {len(bad_tail)}・音が重なる継ぎ目 {len(over)}')
for name, L in (('頭', bad_head), ('尾', bad_tail)):
    for i, at, e, h, sub in L:
        print(f'  {name} #{i} {at:6.2f}s 全体 +{e}dB 高域 +{h}dB 「{sub}」')
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
