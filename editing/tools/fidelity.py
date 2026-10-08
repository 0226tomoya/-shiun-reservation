"""過去の完成データ（A19・A23）と比べて、テロップの書式・位置・変形・効果が「実物にある組み合わせ」かを総当たりで調べる。

    python3 fidelity.py EDIT_FLAT.json REF_FLAT.json [REF_FLAT.json ...]

役割（roles.role）ごとに、各テロップの署名（ランごとのフォント・大きさ・色・縦横比、位置、変形、エフェクト、フィルタ）を作り、
参照データに同じ署名がないものを「型にない」として件数と例を出す。0 件なら書式は型どおり。
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role, text  # noqa: E402

SKIP = {None, 'empty', 'other', 'adjustment_main', 'adjustment_other'}


def r2(v):
    """数値の文字列を小数 1 桁に丸める（"-849.551 443.956" → "-849.6 444.0"）。"""
    if v is None:
        return None
    if isinstance(v, dict):
        return 'keyframes'
    try:
        return ' '.join(f'{float(x):.1f}' for x in str(v).split())
    except ValueError:
        return str(v)


def sig(i):
    runs = []
    for t in i['texts']:
        for x in t['runs']:
            if not x['text'].strip():
                continue
            st = i['styles'].get(x['ref'], {})
            runs.append((st.get('font'), st.get('fontSize'), st.get('fontColor'), st.get('bold'), st.get('alignment')))
    # 同じ書式が続くランはまとめる（行数の違いは署名に入れない）
    comp = []
    for r in runs:
        if not comp or comp[-1] != r:
            comp.append(r)
    p = i.get('params') or {}
    tr = i.get('adjust-transform') or {}
    return (tuple(comp), r2(p.get('位置')), r2(p.get('調整')), r2(tr.get('position')), r2(tr.get('scale')),
            (i.get('effect') or {}).get('name') if isinstance(i.get('effect'), dict) else i.get('effect'),
            tuple(sorted(f['name'] for f in i.get('filters', []))))


def load(p):
    return [i for i in json.load(open(p)) if i['enabled'] != '0' and len(i['path']) <= 1 and i['tag'] == 'title']


def main():
    edit = load(sys.argv[1])
    ref = defaultdict(Counter)
    for p in [a for a in sys.argv[2:] if not a.startswith('-')]:
        for i in load(p):
            r = role(i)
            if r not in SKIP:
                ref[r][sig(i)] += 1
    bad = defaultdict(list)
    total = Counter()
    for i in edit:
        r = role(i)
        if r in SKIP:
            continue
        total[r] += 1
        if sig(i) not in ref[r]:
            bad[r].append(i)
    n_bad = sum(len(v) for v in bad.values())
    print(f'型にない書式・位置: {n_bad} / {sum(total.values())}')
    for r, xs in sorted(bad.items(), key=lambda kv: -len(kv[1])):
        print(f'== {r}: {len(xs)} / {total[r]}')
        ex = Counter(sig(i) for i in xs).most_common(2)
        for s, n in ex:
            print('   A24 :', n, s)
        for s, n in ref[r].most_common(2):
            print('   型  :', n, s)
        if '-v' in sys.argv:
            for i in xs[:3]:
                print('     例', round(i['t0'], 1), text(i)[:40].replace('\n', '/'))


if __name__ == '__main__':
    main()
