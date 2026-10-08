"""本編の間に差し込み（身長別比較など）をした後、確認動画用の音声に同じ長さの無音を入れる。

    python3 shift_audio.py BEFORE.fcpxml AFTER.fcpxml IN.wav OUT.wav

BEFORE と AFTER の本編スパインの同じ要素（マルチカム）の位置の差から、差し込んだ位置と長さを出す。
"""
import sys
import wave
import xml.etree.ElementTree as ET
from fractions import Fraction


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fraction(int(a), int(b))
    return Fraction(s)


def offsets(path):
    r = ET.parse(path).getroot()
    p = [p for p in r.iter('project') if p.get('name') == '本編'][0]
    return [(T(e.get('offset')), e.tag, e.get('ref'), e.get('start'), e.get('duration')) for e in p.find('sequence/spine')]


def main():
    before, after, src, out = sys.argv[1:5]
    a, b = offsets(before), offsets(after)
    # 元のスパインの要素を順に、後のスパインの中で探す（間にある知らない要素が差し込み）
    ins = []  # (元の時刻, 長さ)
    j = 0
    prev = Fraction(0)
    for x in a:
        while j < len(b) and b[j][1:] != x[1:]:
            j += 1
        assert j < len(b), '本編のカットが変わっている'
        d = b[j][0] - x[0]
        if d != prev:
            ins.append((x[0], d - prev))
            prev = d
        j += 1
    w = wave.open(src, 'rb')
    ch, sw, fr = w.getnchannels(), w.getsampwidth(), w.getframerate()
    data = w.readframes(w.getnframes())
    w.close()
    bpf = ch * sw
    o = wave.open(out, 'wb')
    o.setnchannels(ch)
    o.setsampwidth(sw)
    o.setframerate(fr)
    pos = 0
    for t, d in ins:
        cut = int(round(t * fr)) * bpf
        o.writeframes(data[pos:cut])
        o.writeframes(b'\0' * (int(round(d * fr)) * bpf))
        pos = cut
    o.writeframes(data[pos:])
    o.close()
    print('無音を入れた位置:', [(round(float(t), 2), round(float(d), 2)) for t, d in ins], '->', out)


if __name__ == '__main__':
    main()
