"""ラインナップ動画の編集データを、型（A18 / A19 / A23 の実測）と比べて採点する。

    python3 evaluate_lineup.py FLAT.json [--duration 秒]

FLAT.json は fcpxml_flatten.py の出力。100 点満点で、項目ごとの得点と「足りないもの」を重い順に出す。
"""
import json
import os
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role, text  # noqa: E402


def clamp(x):
    return max(0.0, min(1.0, x))


def ramp(v, lo, hi):
    """lo 以下で 0、hi 以上で 1。"""
    return clamp((v - lo) / (hi - lo)) if hi != lo else float(v >= hi)


def band(v, lo, hi, tol):
    """lo〜hi なら 1、外れるほど下がる（tol 外れで 0）。"""
    if lo <= v <= hi:
        return 1.0
    d = lo - v if v < lo else v - hi
    return clamp(1 - d / tol)


def evaluate(items):
    it = [i for i in items if i['enabled'] != '0']
    top = [i for i in it if len(i['path']) <= 1]
    total = max(i['t1'] for i in it)
    mc = [i for i in top if i['tag'] == 'mc-clip']
    mc_time = sum(i['dur'] for i in mc)
    titles = [i for i in top if i['tag'] == 'title']
    roles = Counter(role(i) for i in titles)
    names = Counter(unicodedata.normalize('NFC', i['name'] or '') for i in top if i['tag'] in ('ref-clip', 'asset-clip'))

    def covered(pred, within=None):
        mask = [False] * (int(total * 10) + 2)
        for i in top:
            if pred(i):
                for k in range(int(i['t0'] * 10), int(i['t1'] * 10)):
                    mask[k] = True
        if within is None:
            return sum(mask) / len(mask)
        n = sum(1 for a, b in within for k in range(int(a * 10), int(b * 10)))
        m = sum(1 for a, b in within for k in range(int(a * 10), int(b * 10)) if mask[k])
        return m / n if n else 0

    talk = [(i['t0'], i['t1']) for i in mc]
    overlay = covered(lambda i: i['tag'] in ('video', 'clip', 'asset-clip', 'ref-clip') and i['lane'] not in (None, '-1')
                      and i['name'] != 'BGM' and not str(i['lane']).startswith('in'))
    broll = [i for i in top if i['tag'] in ('video', 'clip', 'asset-clip') and i['lane'] not in (None, '-1')]
    broll_med = sorted(i['dur'] for i in broll)[len(broll) // 2] if broll else 0
    fx = Counter(f['name'] for i in broll for f in i.get('filters', []))
    l1 = covered(lambda i: i['tag'] == 'title' and i['lane'] == '1' and (i.get('effect') or {}).get('name') == 'Adjustment Layer', talk)
    graded = sum(1 for i in top if i['tag'] == 'title' and i['lane'] == '1' and any(f['name'] == 'カラー調整' for f in i.get('filters', [])))
    label_cov = covered(lambda i: i['tag'] == 'title' and role(i) == 'product_label', talk)
    minutes = total / 60
    eyecatch = names.get('アイキャッチ', 0)
    products = max(1, roles.get('product_center', 0) // 2 or eyecatch)
    chapters = sum(1 for i in it for m in i.get('markers', []) if m['tag'] == 'chapter-marker')
    size_blocks = roles.get('size_height_label', 0) / 5
    bgm = names.get('BGM', 0)

    crit = [
        # (項目, 配点, 得点 0-1, 足りないときの説明)
        ('構成: 名前カード・OP コレクション名', 4, (roles['name_card'] > 0) * 0.5 + (roles['collection_label'] > 0) * 0.5, 'OP の名前カード / 左上のコレクション名'),
        ('構成: 商品ごとのアイキャッチ', 4, ramp(eyecatch, 0, max(products, 4)), '商品区間の頭のアイキャッチ'),
        ('構成: カウントダウン・エンディング', 3, (names.get('7', 0) > 0) * 0.5 + (names.get('エンディング', 0) > 0) * 0.5, 'OP のカウントダウン / ED のエンディング動画'),
        ('構成: チャプター', 2, ramp(chapters, 0, 6), 'チャプターマーカー（OP / 商品 / 身長別比較 / ED）'),
        ('構成: 身長別比較', 8, ramp(size_blocks, 0, 3), '身長別比較（5 人 × 9.6 秒）を 3〜4 回'),
        ('テロップ: 商品名ラベル（トーク中）', 6, ramp(label_cov, 0.3, 0.75), 'トーク中の左上の商品名ラベル'),
        ('テロップ: 中央商品名（紹介イン・価格）', 4, ramp(roles['product_center'], 0, 2 * max(products, 4)), '紹介インの中央商品名と、価格ありの中央商品名'),
        ('テロップ: 字幕', 10, ramp(roles['subtitle'] / minutes, 0, 1.9), '字幕（素材・加工・シルエットの説明、締めの一言）'),
        ('テロップ: セクションラベル', 5, ramp(roles['section_label'], 0, 23), 'B-roll の Material / Design / Silhouette / Detail ラベル'),
        ('B-roll: 重なり時間', 14, band(overlay, 0.45, 0.6, 0.45), 'B-roll・写真で 45〜57% を覆う'),
        ('B-roll: 1 カットの長さ', 4, band(broll_med, 3.5, 7, 5) if broll else 0, 'B-roll 1 カット 3.5〜7 秒（中央値 5.3〜5.9）'),
        ('B-roll: 演出の種類', 6, (min(fx['基本3D'], 20) / 20 + min(fx['拡大'], 6) / 6 + (fx['カラー調整'] > 0)) / 3, '置き撮りの基本3D、写真の拡大、B-roll のカラー調整'),
        ('映像: 調整レイヤー（構図・色）', 8, ramp(l1, 0.5, 0.95) * 0.6 + ramp(graded, 0, len(mc) * 0.1) * 0.4, 'メインの lane 1 調整レイヤー（構図プリセット＋カラー調整）'),
        ('映像: カットのテンポ', 6, band(sorted(i['dur'] for i in mc)[len(mc) // 2] if mc else 0, 1.1, 1.35, 0.8), 'メインのカット長の中央値 1.18〜1.27 秒'),
        ('音: BGM・SE', 6, (bgm > 0) * 0.7 + (eyecatch > 0) * 0.3, 'BGM（-17dB ループ）と、アイキャッチの SE'),
        ('テロップ: 型どおりの書式', 10, conformity(titles), '型と違う書式・位置のテロップ'),
    ]
    score = sum(w * s for _, w, s, _ in crit)
    return score, crit, {'overlay': overlay, 'label_cov': label_cov, 'l1': l1, 'subs_per_min': roles['subtitle'] / minutes,
                         'broll_med': broll_med, 'roles': dict(roles), 'eyecatch': eyecatch, 'mc_time': mc_time}


def conformity(titles):
    """役割ごとに、最も多い書式と同じ書式のテロップの割合（同じ動画の中で揃っているか）。"""
    from collections import defaultdict
    groups = defaultdict(list)
    for i in titles:
        r = role(i)
        if r in (None, 'empty', 'other', 'adjustment_main', 'adjustment_other'):
            continue
        st = [i['styles'][x['ref']] for t in i['texts'] for x in t['runs'] if x['text'].strip()]
        # 型の中での使い分け（セクションラベルの語、価格の有無）は別グループで比べる
        if r == 'section_label':
            r = (r, text(i).strip())
        elif r in ('product_center', 'product_label'):
            r = (r, '¥' in text(i))
        groups[r].append(json.dumps([st[:1], i.get('params', {}).get('調整')], sort_keys=True))
    if not groups:
        return 0.0
    ok = sum(Counter(v).most_common(1)[0][1] for v in groups.values())
    return ok / sum(len(v) for v in groups.values())


def main():
    items = json.load(open(sys.argv[1]))
    score, crit, info = evaluate(items)
    print(f'総合 {score:.1f} / 100')
    for name, w, s, _ in crit:
        print(f'  {name:28} {w * s:5.1f} / {w}')
    print('足りないもの（影響の大きい順）:')
    for name, w, s, why in sorted(crit, key=lambda c: -(c[1] * (1 - c[2]))):
        if s < 0.999:
            print(f'  -{w * (1 - s):4.1f}  {why}')
    print('指標:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in info.items() if k != 'roles'})


if __name__ == '__main__':
    main()
