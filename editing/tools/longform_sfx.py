"""わむうの長編の効果音を、置いた部品から決まりで付ける（完成版 6 本では効果音はどれも、ほかの部品の頭と同じ時刻にある）。

    python3 longform_sfx.py PARTS.json OUT.json [--cuts AN.json]   # PARTS の sfx:* を捨てて付け直す

--cuts: 本線（spine）の継ぎ目に、部品の頭と終わりを吸着させる（±1.5 秒以内の一番近い継ぎ目）。
  完成版 6 本では部品の頭の 97% が本線の継ぎ目ちょうど（事実 92/95・アイキャッチ 22/22・インサート 73/74）。
  本番ではカット済みの XML の本線を longform_analyze.py にかけたものを渡す

決まり（A6・A8・A10・A12・A13・A15 から）:
  （6 本で、その部品の頭に効果音が付いている割合）
  keyboard  最初のアイキャッチより前の fact（冒頭のタイプライター）の頭（10/10）
  cursor    channel（10/10）・insert:bg（13/21）・shiun_card（7/7）・item_label（17/27）の頭、「Coming soon」の告知（3/3）
  page      insert:web（shiun_card と同時でないもの。18/39）・color（その時刻の最初の 1 枚。16/16）の頭
  click     topic（話題の箱。11/12）の頭
  knife     tsukkomi（告知を除く）の頭
  scene     transition の頭（10/10）
  taiko     price の頭
  shutter   2 枚目からの coord の頭（7/21）
  付けない  insert:cam（25/72 に何かしら付くが種類がばらばら）・opinion（11/48）
"""
import json
import sys


def main():
    P = json.load(open(sys.argv[1]))
    ev = [e for e in P['events'] if not e['kind'].startswith('sfx:')]
    if '--cuts' in sys.argv:
        import bisect
        A = json.load(open(sys.argv[sys.argv.index('--cuts') + 1]))
        cuts = sorted({x['start'] for x in A['spine']} | {x['end'] for x in A['spine']})

        def snap(t):
            i = bisect.bisect_left(cuts, t)
            c = min((cuts[j] for j in (i - 1, i) if 0 <= j < len(cuts)), key=lambda c: abs(c - t))
            return c if abs(c - t) <= 1.5 else t
        for e in ev:
            if e['kind'] in ('bgm',):
                continue
            a, b = snap(e['start']), snap(e['end'])
            e['start'], e['end'] = a, (b if b > a + 0.3 else e['end'])
    by = lambda k: sorted([e for e in ev if e['kind'] == k], key=lambda e: e['start'])
    eye = by('eyecatch')
    t_main = eye[0]['start'] if eye else 0
    sfx = []
    add = lambda k, t, d=0.3: sfx.append({'kind': 'sfx:' + k, 'start': round(t, 3), 'end': round(t + d, 3), 'text': k})
    for e in by('fact'):
        if e['start'] < t_main:
            add('keyboard', e['start'], 1.0)
    for e in by('channel') + by('insert:bg') + by('shiun_card') + by('item_label'):
        add('cursor', e['start'], 1.0)
    sc = by('shiun_card')
    for e in by('insert:web'):
        if not any(abs(e['start'] - s['start']) < 0.5 for s in sc):
            add('page', e['start'])
    seen = set()
    for e in by('color'):
        k = round(e['start'], 1)
        if k not in seen:
            seen.add(k)
            add('page', e['start'])
    for e in by('topic'):
        add('click', e['start'], 0.2)
    for e in by('tsukkomi'):
        add('cursor' if 'Coming soon' in e.get('text', '') else 'knife', e['start'])
    for e in by('transition'):
        add('scene', e['start'], 1.9)
    for i, e in enumerate(by('price')):
        add('taiko', e['start'], 1.0)
    co = by('coord')
    for a in co[1:]:
        add('shutter', a['start'], 0.4)
    P['events'] = sorted(ev + sfx, key=lambda e: e['start'])
    json.dump(P, open(sys.argv[2], 'w'), ensure_ascii=False, indent=0)
    from collections import Counter
    print(dict(Counter(e['kind'] for e in sfx)))


if __name__ == '__main__':
    main()
