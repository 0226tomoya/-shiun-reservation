"""確認動画・音量の確認用に、編集どおりにピンマイク音声をつないだ声の音声を作る。

    python3 edit_audio.py EDIT.fcpxml PINMIC.wav OUT.wav [--bgm BGM.wav]

- 本編スパインのマルチカム（mc-clip）は、ピンマイク音声の同じ時刻（マルチカムの start ＝ ピンマイクの時刻）を切り出してつなぐ。
  クリップの adjust-volume（amount の dB）と、マルチカムの音のアングルの中の音量（A24 はピンマイク +6dB）も掛ける。それ以外（アイキャッチ・身長別ブロック・カウントダウン・ED）は無音。
- --bgm: BGM の音声ファイルが手元にあれば、XML の BGM（lane が負の ref-clip）の位置・音量（キーフレームを含む）で重ねる。
  無ければ声だけになる（音量の確認は声だけの値として扱う）。
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

import numpy as np

SR = 48000


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fraction(int(a), int(b))
    return Fraction(s)


def db(el):
    av = el.find('adjust-volume')
    if av is None or av.get('amount') is None:
        return 0.0
    return float(av.get('amount').replace('dB', ''))


def load(path):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def main():
    edit, mic, out = sys.argv[1:4]
    root = ET.parse(edit).getroot()
    proj = [p for p in root.iter('project') if p.get('name') == '本編'][0]
    seq = proj.find('sequence')
    total = T(seq.get('duration'))
    voice = load(mic)
    res = {e.get('id'): e for e in root.find('resources')}

    def angle_gain(e):
        """mc-clip が音に使っているアングル（srcEnable が audio / all）の中のクリップの音量（dB）"""
        m = res.get(e.get('ref'))
        mc = m.find('multicam') if m is not None else None
        if mc is None:
            return 0.0
        ids = [s.get('angleID') for s in e.findall('mc-source') if s.get('srcEnable') in ('audio', 'all')]
        for ang in mc.findall('mc-angle'):
            if ang.get('angleID') in ids:
                for c in ang:
                    if c.get('ref') and c.find('adjust-volume') is not None:
                        return db(c)
        return 0.0
    buf = np.zeros(int(float(total) * SR) + SR, dtype=np.float32)
    n = 0
    for e in seq.find('spine'):
        if e.tag != 'mc-clip':
            continue
        off, st, du = T(e.get('offset')), T(e.get('start')), T(e.get('duration'))
        a, b = int(float(st) * SR), int(float(st + du) * SR)
        o = int(float(off) * SR)
        seg = voice[a:b] * (10 ** ((db(e) + angle_gain(e)) / 20))
        buf[o:o + len(seg)] += seg[:len(buf) - o]
        n += 1
    if '--bgm' in sys.argv:
        bgm = load(sys.argv[sys.argv.index('--bgm') + 1])
        for host in seq.find('spine'):
            for c in host:
                if c.tag == 'ref-clip' and (c.get('lane') or '').startswith('-'):
                    hoff = T(host.get('offset')) + T(c.get('offset')) - T(host.get('start') or '0s')
                    cs, cd = T(c.get('start') or '0s'), T(c.get('duration'))
                    seg = bgm[int(float(cs) * SR) % max(1, len(bgm)):][:int(float(cd) * SR)].copy()
                    seg *= 10 ** (db(c) / 20)
                    o = int(float(hoff) * SR)
                    buf[o:o + len(seg)] += seg[:len(buf) - o]
    buf = buf[:int(float(total) * SR)]
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', out],
                   input=buf.tobytes(), check=True)
    print('つないだカット', n, '長さ', round(float(total), 2), '秒 ->', out)


if __name__ == '__main__':
    main()
