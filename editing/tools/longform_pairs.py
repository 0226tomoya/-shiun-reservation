"""完成版の事実・感想・縦書きのテロップと、その時刻の発言を対にした一覧（言い回しと種類のお手本）を作る。

    python3 longform_pairs.py 作業フォルダ A6x A8x ...   → 作業フォルダ/<動画>/pairs.txt

作業フォルダ/<動画>/ に asr/c*.json（起こし）と gold.json（longform_events.py の出力）があること。
"""
import glob
import json
import sys

S = sys.argv[1]
for v in sys.argv[2:]:
    segs = []
    for f in sorted(glob.glob(f'{S}/{v}/asr/c*.json')):
        segs += json.load(open(f))
    G = json.load(open(f'{S}/{v}/gold.json'))['events']
    out = [f'# {v}: 編集者が入れた事実・感想・縦書きのテロップと、その時刻の発言（起こしは誤認識あり）\n']
    for e in sorted(G, key=lambda e: e['start']):
        if e['kind'] not in ('fact', 'opinion', 'vertical'):
            continue
        sp = ' '.join(s['text'].strip() for s in segs if s['end'] > e['start'] - 2 and s['start'] < e['end'] + 0.5)
        out.append(f"{e['start']:.1f}  発言: {sp}\n      → {e['kind']}: {e['text'].replace(chr(10), '⏎')}\n")
    open(f'{S}/{v}/pairs.txt', 'w').write('\n'.join(out))
    print(v, len(out) - 1)
