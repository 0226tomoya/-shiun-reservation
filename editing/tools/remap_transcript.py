"""本編を切ったりアイキャッチを外したりした後、文字起こしの時刻を新しいタイムラインに合わせる。

    python3 remap_transcript.py OLD_V1.fcpxml NEW_V1.fcpxml TRANSCRIPT_IN.json TRANSCRIPT_OUT.json

古い v1 の時刻 → その時刻に映っている本編（マルチカム）の素材の時刻 → 新しい v1 でその素材の時刻が映る時刻、と写す。
切って無くなった単語は消し、全部の単語が消えた行は "removed": true にする（字幕は付けない）。
行の番号は変えない（字幕の seg 番号がそのまま使える）。

    python3 remap_transcript.py --src OLD_V1.fcpxml TRANSCRIPT_IN.json WORDS_SRC.json
は、単語を素材の時刻に直して書き出す（assemble_lineup の --words に渡す）。
"""
import json
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fraction(int(a), int(b))
    return Fraction(s)


def spans(path):
    r = ET.parse(path).getroot()
    p = [p for p in r.iter('project') if p.get('name') == '本編'][0]
    out = []
    for e in p.find('sequence/spine'):
        if e.tag == 'mc-clip':
            out.append((float(T(e.get('offset'))), float(T(e.get('duration'))), e.get('ref'), float(T(e.get('start')))))
    return out


def to_src(old, tin, tout):
    """文字起こしの単語を、素材（マルチカム）の時刻に直して [[ref, 頭, 終わり, 語], ...] で書き出す。
    組み立て（assemble_lineup）が、各カットで何を話しているかを知るのに使う。"""
    so = spans(old)
    tr = json.load(open(tin, encoding='utf-8'))
    segs = tr['segments'] if isinstance(tr, dict) else tr
    out = []
    for k, s in enumerate(segs):
        for w in s.get('words', []):
            for off, du, ref, st in so:
                if off <= w['start'] < off + du:
                    a = st + (w['start'] - off)
                    out.append([ref, round(a, 3), round(a + w['end'] - w['start'], 3), w['word'], k + 1])
                    break
    json.dump(out, open(tout, 'w', encoding='utf-8'), ensure_ascii=False)
    print('素材の時刻の単語', len(out), '->', tout)


def main():
    if sys.argv[1] == '--src':
        return to_src(*sys.argv[2:5])
    old, new, tin, tout = sys.argv[1:5]
    so, sn = spans(old), spans(new)
    by_ref = {}
    for off, du, ref, st in sn:
        by_ref.setdefault(ref, []).append((st, st + du, off))

    def mp(t):
        for off, du, ref, st in so:
            if off <= t < off + du:
                src = st + (t - off)
                for a, b, o in by_ref.get(ref, []):
                    if a - 1e-6 <= src < b + 1e-6:
                        return o + (src - a)
                return None
        return None

    tr = json.load(open(tin, encoding='utf-8'))
    segs = tr['segments'] if isinstance(tr, dict) else tr
    n_rm = 0
    for s in segs:
        ws = []
        for w in s.get('words', []):
            a, b = mp(w['start']), mp(max(w['start'], w['end'] - 0.01))
            if a is None or b is None:
                continue
            ws.append(dict(w, start=round(a, 3), end=round(b + 0.01, 3)))
        if s.get('words') and not ws:
            s['removed'] = True
            n_rm += 1
            continue
        if ws:
            s['words'] = ws
            s['start'], s['end'] = ws[0]['start'], ws[-1]['end']
            s['text'] = ''.join(w['word'] for w in ws)
        else:
            a, b = mp(s['start']), mp(s['end'] - 0.01)
            if a is None:
                s['removed'] = True
                n_rm += 1
                continue
            s['start'], s['end'] = round(a, 3), round((b or a) + 0.01, 3)
    json.dump(tr, open(tout, 'w', encoding='utf-8'), ensure_ascii=False)
    print('消えた行', n_rm, '->', tout)


if __name__ == '__main__':
    main()
