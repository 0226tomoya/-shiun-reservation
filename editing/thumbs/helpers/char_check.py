"""tune・split の後に崩れやすい字を見つける（7周目 high_1 で分かったこと）。
  - 細い字（1 i I l ! - ー ・ , .）の大きさが、同じ行（grp）の中央値から 15% 以上ずれている
  - 縦書きの行で、字の順番（上→下）が入れ替わっている／横書きの行で左→右が入れ替わっている
  - 同じ行の字どうしが大きく重なっている
python3 char_check.py [ID ...]（省略で全 spec）
"""
import json, os, sys, glob, statistics
TH = '/home/user/-shiun-reservation/editing/thumbs'
THIN = set('1iIl!-ー・,.|')
ids = sys.argv[1:] or [os.path.basename(f)[:-5] for f in sorted(glob.glob(os.path.join(TH, 'specs', '*.json')))]
for vid in ids:
    Ls = json.load(open(os.path.join(TH, 'specs', vid + '.json'))).get('layers', [])
    g = {}
    for i, L in enumerate(Ls):
        if L.get('type') == 'text' and L.get('grp'):
            g.setdefault(L['grp'], []).append(i)
    for k, idx in g.items():
        if len(idx) < 3:
            continue
        med = statistics.median(Ls[i].get('size', 80) for i in idx)
        for i in idx:
            t = Ls[i].get('text', '')
            if t in THIN and abs(Ls[i].get('size', 80) / med - 1) > 0.15:
                print(f"{vid}\t{k}\tL{i}「{t}」の大きさ {Ls[i].get('size')} が行の中央値 {med:.0f} と違う")
        vert = Ls[idx[0]].get('vertical')
        a = 'y' if vert else 'x'
        pos = [Ls[i][a] for i in idx]
        for j in range(1, len(idx)):
            if pos[j] < pos[j - 1] - 0.3 * med and not Ls[idx[j]].get('rotate'):
                print(f"{vid}\t{k}\tL{idx[j-1]}「{Ls[idx[j-1]].get('text')}」と L{idx[j]}「{Ls[idx[j]].get('text')}」の順番が逆（{'縦' if vert else '横'}）")
            if abs(pos[j] - pos[j - 1]) < 0.25 * med and Ls[idx[j]].get('text', '').strip() and Ls[idx[j - 1]].get('text', '').strip():
                print(f"{vid}\t{k}\tL{idx[j-1]} と L{idx[j]} が重なっている")
