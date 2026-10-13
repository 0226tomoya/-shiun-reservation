"""カメラの動画の音とピンマイクの音を合わせる（マイクの時刻 = 動画の時刻 + offset 秒）。
python3 av_sync.py 動画.mp4 マイク1.wav [マイク2.wav ...]
1) 粗い位置: 両方の「声の大きさの変化」（10ms ごとの対数エネルギーの差分）を相互相関（マイクの種類・音量・距離の違いに強い）。
2) 細かい位置: 48kHz の波形で、粗い位置の ±30ms を 15 秒の窓 3 か所で相互相関（帯域 300〜3000Hz に絞る）。3 か所のずれの差＝ドリフト。
"""
import sys, subprocess, json
import numpy as np
from scipy.signal import butter, sosfiltfilt


def load(p, sr):
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def env(x, sr, hop=0.01):
    h = int(sr * hop); m = len(x) // h
    e = np.log((x[:m * h].reshape(m, h) ** 2).mean(1) + 1e-8)
    d = np.diff(e, prepend=e[0]); d[d < 0] = 0
    return (d - d.mean()) / (d.std() + 1e-9)


def xc(a, b):
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    c = np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)
    return c


vid, mics = sys.argv[1], sys.argv[2:]
SR = 16000
V16 = load(vid, SR); ev = env(V16, SR)
cands = []
for m in mics:
    a16 = load(m, SR)
    if len(a16) < SR * 3:
        continue
    ea = env(a16, SR)
    c = xc(ev, ea); n = len(c)
    k = int(np.argmax(c)); lag = k if k < n // 2 else k - n
    c2 = c.copy(); c2[max(0, k - 200):k + 200] = -np.inf
    ratio = float(c[k] / (np.max(c2) + 1e-9))
    # 重なっている長さ（短すぎる重なりは信用しない）
    ov = min(len(ev), len(ea) - lag) - max(0, -lag)
    print(f'{m.split("/")[-1]}\toffset={lag/100:+.2f}s\tpeak={ratio:.2f}x\toverlap={ov/100:.0f}s', file=sys.stderr)
    cands.append((ratio, m, lag / 100, ov / 100))
cands.sort(reverse=True)
if not cands or cands[0][0] < 1.5:
    print(json.dumps({'video': vid, 'mic': None, 'cands': [(round(r, 2), m.split('/')[-1], o) for r, m, o, _ in cands]}, ensure_ascii=False)); sys.exit()
ratio, m, off, ov = cands[0]
HR = 48000
sos = butter(4, [300, 3000], 'bandpass', fs=HR, output='sos')
V = sosfiltfilt(sos, load(vid, HR)); A = sosfiltfilt(sos, load(m, HR))
fine = []
dur = len(V) / HR
for frac in (0.15, 0.5, 0.85):
    t0 = max(0, min(dur - 16, dur * frac))
    seg = V[int(t0 * HR):int((t0 + 15) * HR)]
    s = int((t0 + off - 0.03) * HR)
    if len(seg) < HR * 3 or s < 0 or s + len(seg) + int(0.06 * HR) > len(A):
        continue
    win = A[s:s + len(seg) + int(0.06 * HR)]
    c = np.correlate(win, seg, 'valid')
    k = int(np.argmax(np.abs(c)))
    fine.append((t0, (s + k) / HR - t0, bool(c[k] < 0)))
offs = [o for _, o, _ in fine]
res = {'video': vid, 'mic': m, 'offset': round(float(np.median(offs)), 5) if offs else round(off, 3), 'coarse': off,
       'checks': [(round(t, 1), round(o, 5)) for t, o, _ in fine], 'drift_ms': round((max(offs) - min(offs)) * 1000, 2) if len(offs) > 1 else None,
       'inverted': any(i for *_, i in fine), 'peak_ratio': round(ratio, 2), 'overlap_s': ov}
print(json.dumps(res, ensure_ascii=False))
