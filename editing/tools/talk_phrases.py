"""対談のカット済み XML と、マイク 2 本の文字起こしから、タイムライン上のフレーズ（話者つき）を作る。テロップ作りの材料。
    python3 talk_phrases.py BASE.fcpxml WAMU_ASR.json GUEST_ASR.json WAMU_16k.wav GUEST_16k.wav OUT.tsv [OUT.json]
    （GUEST_ASR.json に "-" を渡すと、WAMU_ASR.json を 2 本を足した音声の文字起こしとして扱い、全部の単語の話者を音量で決める）
- マルチカムのマイクのアングルは頭 0 秒でそろっている前提（mc-clip の start がそのままマイクの時刻）
- 話者: 2 本別々に起こしたときは、大きい方のマイクの単語だけ残す（同じ言葉の重複を消すため）。表示する話者は決めない（下の注）
- フレーズ: 0.3 秒を超える間・文の終わり・25 字で区切る
"""
import json
import sys
import wave
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr

import numpy as np


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fr(int(a), int(b))
    return Fr(s)


def energy(path):
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    hop = w.getframerate() // 20
    n = len(x) // hop
    return 10 * np.log10(np.mean(x[:n * hop].reshape(n, hop) ** 2, 1) + 1e-12)


def main():
    base, wa, ga, ww, gw, out = sys.argv[1:7]
    root = ET.parse(base).getroot()
    sp = root.find('.//project/sequence/spine')
    clips = [(float(T(c.get('offset'))), float(T(c.get('start'))), float(T(c.get('duration')))) for c in sp]
    Ew, Eg = energy(ww), energy(gw)
    L = min(len(Ew), len(Eg))

    def louder(t):
        i = min(L - 1, max(0, int(t / 0.05)))
        return Ew[i] - Eg[i]

    words = []
    srcs = (('わむう', wa), ('ゲスト', ga)) if ga != '-' else (('mix', wa),)
    for spk, f in srcs:
        for s in json.load(open(f)):
            for w in s['words']:
                mid = (w['start'] + w['end']) / 2
                d = louder(mid)
                if spk == 'mix':
                    words.append((w['start'], w['end'], w['word'], 'わむう' if d >= 0 else 'ゲスト'))
                elif (spk == 'わむう' and d >= 0) or (spk == 'ゲスト' and d < 0):
                    words.append((w['start'], w['end'], w['word'], spk))
    words.sort()
    # タイムラインへ
    tl = []
    for a, b, w, spk in words:
        for off, st, du in clips:
            if st - 0.05 <= (a + b) / 2 < st + du:
                tl.append((off + (a - st), off + (b - st), w, spk, (a + b) / 2))
                break
    tl.sort()
    # 話者は音量で決めない（10/15 A29: 調整済みのマイク 2 本は反響対策で音量の差が 0dB 付近の 1 つの山になり、話者に分かれなかった）。
    # 間 0.3 秒・文の終わり（。？）・25 字で区切る。誰の発言かはテロップを作る人が中身から判断する
    phrases, cur = [], None
    for a, b, w, spk, m in tl:
        if cur and (a - cur['end'] > 0.3 or len(cur['text']) >= 25 or cur['text'].rstrip().endswith(('。', '？', '?'))):
            phrases.append(cur); cur = None
        if cur is None:
            cur = {'start': a, 'end': b, 'spk': '?', 'text': ''}
        cur['text'] += w
        cur['end'] = b
    if cur:
        phrases.append(cur)
    with open(out, 'w') as f:
        f.write('番号\t頭\t終わり\t話者\t発言（文字起こし・誤認識あり）\n')
        for i, p in enumerate(phrases):
            f.write(f"{i}\t{p['start']:.2f}\t{p['end']:.2f}\t{p['spk']}\t{p['text'].strip()}\n")
    if len(sys.argv) > 7:
        json.dump(phrases, open(sys.argv[7], 'w'), ensure_ascii=False, indent=1)
    total = clips[-1][0] + clips[-1][2]
    print(f'単語 {len(tl)}・フレーズ {len(phrases)}・タイムライン {total:.1f} 秒・話者 ' +
          '（話者は中身から判断）')


if __name__ == '__main__':
    main()
