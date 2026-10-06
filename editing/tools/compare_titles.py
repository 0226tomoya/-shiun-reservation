"""2 つの flatten 結果（実際 / シミュレーション）のテロップを 1 本ずつ突き合わせ、書式・位置の一致率を出す。

    python3 compare_titles.py actual.json simulated.json [--detail]
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role, text, first_style, pos, tr, ROLE_JA  # noqa: E402


def load(p):
    return [i for i in json.load(open(p)) if i['enabled'] != '0' and i['tag'] == 'title' and len(i['path']) <= 1]


def key(i):
    return (round(i['t0'], 2), i['lane'], text(i).strip())


def props(i):
    st = first_style(i)
    (tx, ty), sc = tr(i)
    x, y = pos(i)
    return {'effect': (i.get('effect') or {}).get('name'), 'font': st.get('font'), 'face': st.get('fontFace'),
            'size': st.get('fontSize'), 'color': st.get('fontColor'), 'pos': (round(x), round(y)),
            'transform': (round(tx, 1), round(ty, 1)), 'scale': round(sc, 2), 'stretch': i.get('params', {}).get('調整')}


def near(k, a, b):
    """見た目で区別できない差（12px 以内、色 0.001 以内）なら True。"""
    if k == 'pos':
        return abs(a[0] - b[0]) <= 12 and abs(a[1] - b[1]) <= 12
    if k == 'transform':
        return abs(a[0] - b[0]) * 10.8 <= 12 and abs(a[1] - b[1]) * 10.8 <= 12
    if k == 'color':
        try:
            return all(abs(float(x) - float(y)) < 1e-3 for x, y in zip(a.split(), b.split()))
        except (AttributeError, ValueError):
            return False
    return False


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    detail = '--detail' in sys.argv
    bm = {key(i): i for i in b}
    res = collections.defaultdict(lambda: collections.Counter())
    diffs = collections.defaultdict(collections.Counter)
    for i in a:
        r = role(i)
        if r in (None, 'empty', 'other', 'adjustment_main', 'adjustment_other'):
            continue
        j = bm.get(key(i))
        if j is None:
            res[r]['unmatched'] += 1
            continue
        pa, pb = props(i), props(j)
        bad = [k for k in pa if pa[k] != pb[k]]
        res[r]['total'] += 1
        res[r]['ok' if not bad else 'diff'] += 1
        if not [k for k in bad if not near(k, pa[k], pb[k])]:
            res[r]['near'] += 1
        for k in bad:
            diffs[r][(k, str(pa[k]), str(pb[k]))] += 1
    tot = sum(c['total'] for c in res.values())
    ok = sum(c['ok'] for c in res.values())
    nr = sum(c['near'] for c in res.values())
    print(f'全体: 完全一致 {ok}/{tot} ({ok / max(tot, 1) * 100:.1f}%)  見た目で同じ {nr}/{tot} ({nr / max(tot, 1) * 100:.1f}%)')
    for r, c in sorted(res.items(), key=lambda x: -x[1]['total']):
        print(f"  {ROLE_JA.get(r, r):16} 完全 {c['ok']:3} / 見た目 {c['near']:3} / {c['total']:3}", ('' if not c['unmatched'] else f"(未照合 {c['unmatched']})"))
        for (k, va, vb), n in diffs[r].most_common(6 if detail else 3):
            print(f'      差: {k:9} 実際={va}  型={vb}  ×{n}')


if __name__ == '__main__':
    main()
