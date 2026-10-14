"""撮影素材の asset の頭（start）を実物のタイムコードに合わせる。FCP の素材の XML が無くても、ファイルの頭を ffprobe で読めば作れる。
    python3 fix_asset_tc.py IN.fcpxml tc.json OUT.fcpxml [--media-info out_media_info.json]

tc.json: {素材名: {"tc": "11:58:03:21", "rate": "30000/1001", "frames": 1005}}（tc が無い素材は 0 秒のまま正しいと記録する）
- asset の start を TC の時刻にする（NDF。29.97p は 1 コマ 1001/30000 秒、23.976p は 1001/24000 秒）
- その asset を ref で使う全要素（asset-clip・video・audio）の start に同じだけ足す（start が無ければ TC の時刻を書く）
- その要素につないだ要素の offset も同じだけ足す（親の start 基準のため）
- 長さ（duration）・パスは変えない
（2026-10-14、A24 の身長別の動画 31 本が「頭 0 秒」で再接続できなかった件）
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fr(int(a), int(b))
    return Fr(s)


def ts(f):
    f = Fr(f)
    return f'{f.numerator}s' if f.denominator == 1 else f'{f.numerator}/{f.denominator}s'


def tc_time(tc, rate):
    h, m, s, f = map(int, re.split('[:;]', tc))
    a, b = map(int, rate.split('/'))
    nominal = round(a / b)
    frames = ((h * 60 + m) * 60 + s) * nominal + f
    return frames * Fr(b, a)


def main():
    src, tcj, dst = sys.argv[1:4]
    tcs = json.load(open(tcj))
    tree = ET.parse(src)
    root = tree.getroot()
    shift, mi = {}, {}
    for a in root.find('resources').iter('asset'):
        n = a.get('name')
        if n not in tcs:
            continue
        info = tcs[n]
        off = tc_time(info['tc'], info['rate']) if info.get('tc') else Fr(0)
        old = T(a.get('start'))
        a.set('start', ts(off))
        shift[a.get('id')] = off - old
        rep = a.find('media-rep')
        mi[n] = {'asset': {'start': ts(off), 'duration': a.get('duration')}, 'src': rep.get('src') if rep is not None else ''}
    n_ref = 0
    for e in root.iter():
        d = shift.get(e.get('ref'))
        if d is None or e.tag not in ('asset-clip', 'video', 'audio', 'clip'):
            continue
        e.set('start', ts(T(e.get('start')) + d))
        for c in e:  # つないだ要素の offset は親の start 基準なので同じだけずらす
            if c.get('offset') is not None:
                c.set('offset', ts(T(c.get('offset')) + d))
        n_ref += 1
    tree.write(dst, encoding='UTF-8', xml_declaration=True)
    # 元の DOCTYPE を戻す
    head = open(src, encoding='utf-8').read(400)
    m = re.search(r'<!DOCTYPE[^>]*>', head)
    if m:
        body = open(dst, encoding='utf-8').read()
        body = body.replace("<?xml version='1.0' encoding='UTF-8'?>", '<?xml version="1.0" encoding="UTF-8"?>\n' + m.group(0), 1)
        open(dst, 'w', encoding='utf-8').write(body)
    if '--media-info' in sys.argv:
        json.dump(mi, open(sys.argv[sys.argv.index('--media-info') + 1], 'w'), ensure_ascii=False, indent=1)
    print(f'asset {len(shift)} 本の頭をタイムコードに合わせ、使っている所 {n_ref} か所の start をずらした')


if __name__ == '__main__':
    main()
