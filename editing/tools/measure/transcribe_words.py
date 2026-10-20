"""動画の声を文字起こしして、単語と時刻を words.json に書く（measure_kit.py の自動の時刻合わせに使う）。
    python3 transcribe_words.py IN.mp4 OUT_words.json"""
import sys, json, subprocess, numpy as np
from faster_whisper import WhisperModel

src, out = sys.argv[1], sys.argv[2]
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
a = np.frombuffer(pcm, '<i2').astype('float32') / 32768
m = WhisperModel('large-v3', device='cpu', compute_type='int8')
segs, _ = m.transcribe(a, language='ja', word_timestamps=True)
W = [{'w': w.word, 's': round(w.start, 3), 'e': round(w.end, 3)} for s in segs for w in s.words]
json.dump(W, open(out, 'w'), ensure_ascii=False, indent=0)
print(''.join(w['w'] for w in W))
