"""粗編集（カット済み）と完成の本編を比べ、粗編集の発言のうち完成で切られたものを並べる（仕上げのカットを学ぶため）。

    python3 finish_cut_diff.py ROUGH_MAP.json TRANSCRIPT(json か文字起こしのログ) FINAL.fcpxml PROJECT OUT.json

ROUGH_MAP: [[粗編集の時刻, 素材の頭, 長さ], ...]（粗編集どおりにつないだ音声の時刻 → 素材の時刻）
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction


def T(s):
    s = (s or '0s').rstrip('s')
    return Fraction(int(s.split('/')[0]), int(s.split('/')[1])) if '/' in s else Fraction(s)


def main():
    mp, trp, fin, proj, out = sys.argv[1:6]
    M = json.load(open(mp))
    if trp.endswith('.json'):
        segs = [(s['start'], s['end'], s['text']) for s in json.load(open(trp))]
    else:
        segs = []
        for l in open(trp, encoding='utf-8', errors='ignore'):
            m = re.match(r'\s*([0-9.]+)-\s*([0-9.]+) (.*)', l)
            if m:
                segs.append((float(m.group(1)), float(m.group(2)), m.group(3)))
    r = ET.parse(fin).getroot()
    p = [p for p in r.iter('project') if p.get('name') == proj][0]
    F = sorted((float(T(e.get('start'))), float(T(e.get('start')) + T(e.get('duration')))) for e in p.find('sequence/spine') if e.tag == 'mc-clip')

    def src(t):
        for a, s, d in M:
            if a <= t < a + d:
                return s + (t - a)
        return None

    def kept_frac(t0, t1):
        n = k = 0
        t = t0
        while t < t1:
            s = src(t)
            if s is not None:
                n += 1
                if any(x <= s < y for x, y in F):
                    k += 1
            t += 0.05
        return k / n if n else 1
    rows = []
    for a, b, txt in segs:
        rows.append({'t0': round(a, 2), 't1': round(b, 2), 'kept': round(kept_frac(a, b), 2), 'text': txt})
    json.dump(rows, open(out, 'w'), ensure_ascii=False, indent=0)
    cut = [x for x in rows if x['kept'] < 0.3]
    part = [x for x in rows if 0.3 <= x['kept'] < 0.9]
    print(f'発言 {len(rows)}: 丸ごと切られた {len(cut)} / 一部切られた {len(part)}')


if __name__ == '__main__':
    main()
