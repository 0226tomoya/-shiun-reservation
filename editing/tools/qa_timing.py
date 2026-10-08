"""編集点の精度チェック（フレーム単位）。XML の有理数のまま計算する。

    python3 qa_timing.py EDIT.fcpxml [プロジェクト名]

調べること:
  1. フレームずれ: 接続クリップ・テロップの頭と終わりが、シーケンスのフレームの格子に乗っているか
  2. インサートの切れ目: B-roll（レーン 3 以上の映像・写真）のかたまりの頭と終わり、かたまりの中の切り替わりが、
     メインのカットの編集点と一致しているか（理想: 編集点で切り替わる）
  3. 一瞬の隙間: インサートとインサートの間に 0.5 秒未満だけトークが見える所
  4. 素材の長さ不足: 動画インサートの使う範囲が、素材の長さを超えていないか
  5. 字幕の切れ目: 字幕の頭と終わりがメインの編集点と一致しているか
"""
import sys
import unicodedata
import xml.etree.ElementTree as ET
from fractions import Fraction

VIDEO = {'video', 'asset-clip', 'clip', 'ref-clip', 'sync-clip', 'mc-clip'}


def T(s):
    s = (s or '0s').rstrip('s')
    return Fraction(s)


def mmss(t):
    t = float(t)
    return f'{int(t // 60)}:{t % 60:05.2f}'


def norm(s):
    return unicodedata.normalize('NFC', s or '')


def main():
    src = sys.argv[1]
    pname = sys.argv[2] if len(sys.argv) > 2 else '本編'
    root = ET.parse(src).getroot()
    res = {e.get('id'): e for e in root.find('resources')}
    proj = [p for p in root.iter('project') if norm(p.get('name')) == norm(pname)][0]
    seq = proj.find('sequence')
    fd = T(res[seq.get('format')].get('frameDuration'))
    spine = seq.find('spine')

    cuts = set()
    items = []  # (abs0, abs1, el, host)
    for e in spine:
        if e.get('offset') is None:
            continue
        off, du, st = T(e.get('offset')), T(e.get('duration')), T(e.get('start'))
        cuts.add(off)
        cuts.add(off + du)
        for ch in e:
            if ch.get('lane') is None or ch.get('offset') is None:
                continue
            a = off + T(ch.get('offset')) - st
            items.append((a, a + T(ch.get('duration')), ch, e))
    total = max(cuts)

    def on_grid(t):
        return (t / fd).denominator == 1

    def is_text(el, word):
        return word in ''.join(el.itertext())

    # 1. フレームずれ
    off_grid = [(a, el) for a, b, el, _ in items if not on_grid(a) or not on_grid(b)]

    # 2. インサート（レーン 3 以上の映像）。音だけのもの（レーン負）は除く
    ins = sorted([(a, b, el) for a, b, el, _ in items
                  if el.tag in VIDEO and int(el.get('lane')) >= 3], key=lambda x: x[0])
    # かたまりにまとめる（重なり・接しているもの）
    blocks = []
    for a, b, el in ins:
        if blocks and a <= blocks[-1][1] + fd / 2:
            blocks[-1][1] = max(blocks[-1][1], b)
            blocks[-1][2].append((a, b))
        else:
            blocks.append([a, b, [(a, b)]])
    edge_off = [(a, b) for a, b, _ in blocks if a not in cuts or b not in cuts]
    inner_switch = []
    for a, b, parts in blocks:
        for pa, pb in parts:
            for t in (pa, pb):
                if a < t < b and t not in cuts and t not in inner_switch:
                    inner_switch.append(t)
    # 3. 一瞬の隙間
    flashes = [(blocks[k][1], blocks[k + 1][0]) for k in range(len(blocks) - 1)
               if blocks[k + 1][0] - blocks[k][1] < Fraction(1, 2)]
    # 4. 素材の長さ不足
    short = []
    for a, b, el, _ in items:
        if el.tag in ('asset-clip', 'clip', 'video') and int(el.get('lane')) >= 3:
            r = res.get(el.get('ref'))
            if r is None or r.tag != 'asset' or r.get('duration') in (None, '0s'):
                continue
            if r.get('hasVideo') == '1' and r.get('duration') and T(r.get('duration')) > 0 and el.tag != 'video':
                used_end = T(el.get('start') or r.get('start') or '0s') + T(el.get('duration'))
                src_end = T(r.get('start') or '0s') + T(r.get('duration'))
                if used_end > src_end:
                    short.append((a, norm(el.get('name')), float(used_end - src_end)))
    # 5. 字幕
    subs = [(a, b, el) for a, b, el, _ in items if el.tag == 'title' and el.get('lane') == '7']
    sub_off = [(a, b) for a, b, _ in subs if a not in cuts or b not in cuts]

    print(f'シーケンス {1 / fd:.2f}fps・長さ {mmss(total)}・メインの編集点 {len(cuts)} か所')
    print(f'1. フレームずれ: {len(off_grid)} / {len(items)} 要素')
    print(f'2. インサートのかたまり {len(blocks)}: 頭か終わりが編集点とずれている {len(edge_off)}、'
          f'かたまりの中で編集点以外で切り替わる {len(inner_switch)} か所')
    print(f'3. 0.5 秒未満だけトークが見える隙間: {len(flashes)}')
    print(f'4. 素材の長さ不足（動画が途中で終わる）: {len(short)}')
    print(f'5. 字幕 {len(subs)}: 頭か終わりが編集点とずれている {len(sub_off)}')
    if '-v' in sys.argv:
        for a, b in edge_off[:15]:
            print(f'   インサート {mmss(a)}–{mmss(b)}')
        for a, b in flashes[:15]:
            print(f'   隙間 {mmss(a)}–{mmss(b)}（{float(b - a):.2f} 秒）')
        cl = sorted(cuts)
        import bisect

        def gapcut(t):
            i = bisect.bisect_left(cl, t)
            return min(abs(float(t - c)) for c in cl[max(0, i - 1):i + 1])
        for t in inner_switch[:30]:
            print(f'   切り替わり {mmss(t)}（一番近い編集点まで {gapcut(t):.2f} 秒）')
        for a, b in sub_off[:15]:
            print(f'   字幕 {mmss(a)}–{mmss(b)}（{gapcut(a):.2f} / {gapcut(b):.2f} 秒）')
        for a, b in edge_off[:15]:
            print(f'   インサート端 {mmss(a)}（{gapcut(a):.2f}）– {mmss(b)}（{gapcut(b):.2f}）')
        for a, n, over in short[:15]:
            print(f'   長さ不足 {mmss(a)} {n}（{over:.2f} 秒足りない）')
    bad = len(off_grid) + len(edge_off) + len(inner_switch) + len(flashes) + len(short)
    print('合計の問題:', bad)


if __name__ == '__main__':
    main()
