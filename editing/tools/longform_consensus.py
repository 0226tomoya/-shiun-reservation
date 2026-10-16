"""長編の部品を別々に作った案（3 つ以上）から、半分以上が同じ所に置いた部品だけを残す（出しすぎを減らす）。

    python3 longform_consensus.py OUT.json PRED1.json PRED2.json PRED3.json [...]

- 文のある部品（fact・opinion・vertical・tsukkomi・topic・color・coord・item_card・shiun_card・price）:
  頭が ±3 秒以内で、文の近さ 0.3 以上（fact・opinion・vertical は種類が違ってもまとめる）のものを 1 つのかたまりにし、
  過半数の案に出てくるかたまりだけ残す。残すのは頭が真ん中の案の部品、種類は多数決
- 時刻だけの部品（eyecatch・transition・insert:web・insert:cam・sfx:*）: 頭 ±2 秒（効果音は ±0.5 秒）で同じように
- 1 つだけの部品（heading・item_label・op_profile・title_call・channel・closing・ending・bgm）: 部品の数が真ん中の案のものをそのまま
"""
import json
import statistics
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

TEXT = {'fact', 'opinion', 'vertical', 'tsukkomi', 'topic', 'color', 'coord', 'item_card', 'shiun_card', 'price'}
FAMILY = {'fact': 'tel', 'opinion': 'tel', 'vertical': 'tel'}
TIME = {'eyecatch': 2.0, 'transition': 2.0, 'insert:web': 2.0, 'insert:cam': 2.0}
WHOLE = {'heading', 'item_label', 'op_profile', 'title_call', 'channel', 'closing', 'ending', 'bgm', 'insert:bg'}


def n(s):
    return ''.join(c for c in unicodedata.normalize('NFKC', s or '') if not c.isspace())


def main():
    out = sys.argv[1]
    runs = [json.load(open(p))['events'] for p in sys.argv[2:]]
    R = len(runs)
    need = R // 2 + 1
    res = []
    # 1 つだけの部品: 種類ごとに、数が真ん中の案から
    for k in sorted({e['kind'] for r in runs for e in r if e['kind'] in WHOLE}):
        cnt = sorted(((sum(e['kind'] == k for e in r), i) for i, r in enumerate(runs)))
        i = cnt[len(cnt) // 2][1]
        res += [e for e in runs[i] if e['kind'] == k]
    # かたまりにまとめる
    items = [(i, e) for i, r in enumerate(runs) for e in r if e['kind'] not in WHOLE]
    used = set()
    items.sort(key=lambda x: x[1]['start'])
    for a in range(len(items)):
        if a in used:
            continue
        ia, ea = items[a]
        fam = FAMILY.get(ea['kind'], ea['kind'])
        tol = 0.5 if ea['kind'].startswith('sfx:') else TIME.get(ea['kind'], 3.0)
        group = [(ia, ea)]
        used.add(a)
        for b in range(a + 1, len(items)):
            if b in used:
                continue
            ib, eb = items[b]
            if eb['start'] - ea['start'] > tol:
                break
            if ib in {g[0] for g in group} or FAMILY.get(eb['kind'], eb['kind']) != fam:
                continue
            if ea['kind'] in TEXT and SequenceMatcher(None, n(ea.get('text')), n(eb.get('text'))).ratio() < 0.3:
                continue
            group.append((ib, eb))
            used.add(b)
        if len({g[0] for g in group}) >= need:
            st = statistics.median(e['start'] for _, e in group)
            rep = min(group, key=lambda g: abs(g[1]['start'] - st))[1]
            rep = dict(rep)
            rep['kind'] = Counter(e['kind'] for _, e in group).most_common(1)[0][0]
            res.append(rep)
    res.sort(key=lambda e: e['start'])
    json.dump({'events': res}, open(out, 'w'), ensure_ascii=False, indent=0)
    print(dict(Counter(e['kind'] for e in res)))


if __name__ == '__main__':
    main()
