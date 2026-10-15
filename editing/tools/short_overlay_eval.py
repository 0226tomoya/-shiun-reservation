"""ショートの字幕・カード・効果音の自動配置（short_overlay_auto.py）を、過去の正解（short_gold.py）で採点する評価ループ。
    python3 short_overlay_eval.py GOLD_DIR [--grid]
入力は正解から作る: 本線のカット（cuts）と、字幕の文を字幕の時間に字数で割り振った発言（words。文字起こしの代わり）。
  商品の呼び方（name_hint）は eval の HINT（台本・EC から人が渡すもの）。
点（100 点）: 字幕の頭が正解の頭と 0.05 秒以内で一致する F1×40 + 字幕の終わりの F1×15（文字起こしの誤字に左右されないよう、文ではなく区切りで比べる）
            + カードの種類ごとの最初の頭が 0.3 秒以内の割合×30 + 効果音の頭の F1（0.2 秒）×15
2 つの回し方:
  再現: その動画だけで一番よい決まり（PARAMS）を探して点を出す（1 度できたものを再現できるか）
  当てはめ: 他の動画で一番よい決まりを、その動画に当てる（次の動画に型で作れるか）
"""
import glob
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from short_overlay_auto import P, predict

HINT = {'ヘンリー': ['ヘンリー'], 'パンツ2本': ['ストレート', 'スラックス', 'パンツ', 'デニム'], 'シャツ': ['シャツ'], 'ローファー8月': ['ローファー']}
# 色（EC の色名のカタカナ。文字起こしの誤りに備えて語尾だけも入れる）
COLORS = {'ヘンリー': ['ブラック', 'グレー'], 'シャツ': ['チャコール', 'コール'], 'パンツ2本': ['ブラック'], 'ローファー8月': ['ブラック', 'ブラウン']}


YT = {'ヘンリー': 'qqpFGu6Z_l4', 'シャツ': '1QG4_uwcG5g', 'パンツ2本': 'Wf1gD-pnQUo'}
YT_DIR = os.environ.get('YT_SUBS', '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/ws/vw')


def yt_words(name):
    f = os.path.join(YT_DIR, f"{YT.get(name, '-')}_web.ja.json3")
    if not os.path.exists(f):
        return None
    W = []
    for e in json.load(open(f)).get('events', []):
        t0 = e['tStartMs'] / 1000
        for s in e.get('segs', []):
            tx = s.get('utf8', '').strip()
            if tx and not tx.startswith('['):
                W.append([t0 + s.get('tOffsetMs', 0) / 1000, tx])
    W.sort()
    return [[a, (W[i + 1][0] if i + 1 < len(W) else a + 0.3), w] for i, (a, w) in enumerate(W)]


def make_input(g):
    yw = yt_words(g['name'])
    if yw:  # 公開動画の自動字幕（カードの間の発言も入る）
        return {'length': g['length'], 'cuts': g['cuts'], 'words': yw, 'product': {'name_hint': HINT.get(g['name'], []), 'colors': COLORS.get(g['name'], [])}, 'src': 'youtube'}
    words = []
    for t0, du, tx in g['subs']:
        s = tx.replace('/', '')
        n = max(1, len(s))
        for i, ch in enumerate(s):
            words.append([t0 + du * i / n, t0 + du * (i + 1) / n, ch])
    return {'length': g['length'], 'cuts': g['cuts'], 'words': words, 'product': {'name_hint': HINT.get(g['name'], [])}}


def f1(a, b, tol):
    used, tp = set(), 0
    for x in a:
        j = next((j for j, y in enumerate(b) if j not in used and abs(x - y) <= tol), None)
        if j is not None:
            used.add(j); tp += 1
    P_ = tp / max(len(a), 1); R = tp / max(len(b), 1)
    return 2 * P_ * R / max(P_ + R, 1e-9)


def score(pred, g, subs_only=False):
    ps, gs = [s[0] for s in pred['subs']], [s[0] for s in g['subs']]
    sf = f1(ps, gs, 0.05)
    tm = f1([s[0] + s[1] for s in pred['subs']], [s[0] + s[1] for s in g['subs']], 0.05)  # 字幕の終わり（区切り）
    kinds = {}
    for c in g['cards']:
        kinds.setdefault(c[3], c[0])
    pk = {}
    for c in pred['cards']:
        pk.setdefault(c[3], c[0])
    hit = [1 if k in pk and abs(pk[k] - v) <= 0.3 else 0 for k, v in kinds.items() if k in ('product', 'price', 'release', 'sizetable', 'height', 'color')]
    ch = sum(hit) / max(len(hit), 1)
    sef = f1([x[0] for x in pred['se']], [x[0] for x in g['se']], 0.2) if g['se'] else 1.0
    if subs_only:  # 発言がカードの間に無い（正解の字幕から作った材料）→ 字幕だけで 100 点に換算
        return {'点': round((sf * 40 + tm * 15) / 55 * 100, 1), '字幕の頭F1': round(sf, 3), '字幕の終わりF1': round(tm, 3), 'カード': None, '効果音F1': None}
    pts = sf * 40 + tm * 15 + ch * 30 + sef * 15
    return {'点': round(pts, 1), '字幕の頭F1': round(sf, 3), '字幕の終わりF1': round(tm, 3), 'カード': round(ch, 3), '効果音F1': round(sef, 3)}


GRID = {'target': [9, 10, 11, 12, 13], 'max_chars': [16, 18, 22], 'min_chars': [4, 5, 6, 7, 8], 'lag': [0.1, 0.2, 0.3]}


def sc(g, p):
    inp = make_input(g)
    return score(predict(inp, p), g, subs_only=inp.get('src') != 'youtube')


def best(golds, grid=GRID):
    bp, bs = None, -1
    keys = list(grid)
    for vals in itertools.product(*[grid[k] for k in keys]):
        p = dict(P); p.update(dict(zip(keys, vals)))
        s = sum(sc(g, p)['点'] for g in golds) / len(golds)
        if s > bs:
            bs, bp = s, p
    return bp, bs


def main():
    golds = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(sys.argv[1], '*.json')))]
    print('== 今の決まりのまま')
    for g in golds:
        print(g['name'], sc(g, P))
    if '--grid' in sys.argv:
        print('== 再現（その動画で一番よい決まり）')
        for g in golds:
            p, s = best([g]); print(g['name'], round(s, 1), {k: p[k] for k in GRID})
        print('== 当てはめ（他の動画で決めた決まりを当てる）')
        tot = []
        for i, g in enumerate(golds):
            p, _ = best(golds[:i] + golds[i + 1:])
            r = sc(g, p); tot.append(r['点'])
            print(g['name'], r, {k: p[k] for k in GRID})
        print('当てはめの平均', round(sum(tot) / len(tot), 1))


if __name__ == '__main__':
    main()
