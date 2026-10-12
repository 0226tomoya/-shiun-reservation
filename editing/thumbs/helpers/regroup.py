"""5 周目までに 1 字ずつに分けた字（"grp" が無い）を、行ごとにまとめて "grp" を付け直す。
同じ行 = 1 字の text レイヤーで、大きさ・回転・斜体・縦書きがほぼ同じ、中心の高さ（縦書きは横位置）が近く、並びが続いているもの。
python3 regroup.py ID [--apply]   （--apply なしは案を表示するだけ）
付けた後は helpers/tune_group.py ID --grp R3 --apply で行ごとに合わせられる。
"""
import json, os, sys
TH = '/home/user/-shiun-reservation/editing/thumbs'
vid = sys.argv[1]
sp = os.path.join(TH, 'specs', vid + '.json')
spec = json.load(open(sp))
Ls = spec['layers']
cand = [i for i, L in enumerate(Ls) if L['type'] == 'text' and not L.get('grp') and len((L.get('text') or '').strip()) <= 2 and not L.get('runs')]
groups = []
for i in cand:
    L = Ls[i]
    sz = L.get('size', 80)
    key = (round(L.get('rotate') or 0), round(L.get('skew') or 0), bool(L.get('vertical')))
    placed = False
    for g in groups:
        M = Ls[g[-1]]
        if g[-1] != i - 1 and abs(i - g[-1]) > 2:  # レイヤーの並びが続いていること（間に 1 つまで）
            continue
        msz = M.get('size', 80)
        mkey = (round(M.get('rotate') or 0), round(M.get('skew') or 0), bool(M.get('vertical')))
        if mkey != key or abs(msz - sz) > 0.5 * max(msz, sz):
            continue
        a, b = ('x', 'y') if L.get('vertical') else ('y', 'x')
        if abs(M[a] - L[a]) > 0.6 * max(msz, sz):  # 行の高さがそろっている
            continue
        if abs(M[b] - L[b]) > 2.2 * max(msz, sz):  # 隣の字が遠すぎない
            continue
        g.append(i); placed = True; break
    if not placed:
        groups.append([i])
groups = [g for g in groups if len(g) >= 2]
for n, g in enumerate(groups):
    print(f"R{n}: {''.join(Ls[i]['text'] for i in g)}  layers={','.join(map(str, g))}")
if '--apply' in sys.argv:
    for n, g in enumerate(groups):
        for i in g:
            Ls[i]['grp'] = f'R{n}'
    json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
    print(len(groups), 'groups applied')
