"""わむうの通常の長編（ひとりで話す購入品・レビュー回）の編集を、完成版の部品（longform_events.py の出力）と比べて 100 点で採点する。

    python3 longform_score.py GOLD.json PRED.json [--detail]

PRED.json: {"events": [{"kind", "start", "end", "text"}]}（kind は longform_events.py と同じ名前）
配点（合計 100）:
  構成 20 … アイキャッチ（±2 秒の F1）12、冒頭の型（op_profile・title_call・channel・sfx:keyboard があるか）4、締めの型（channel・closing・ending）4
  見出し 8 … 左上の見出しが出ている時間の重なり（IoU）4、文の近さ 4
  商品番号の箱 6 … item_label の時間の重なり（IoU）
  事実のテロップ 16 … fact（頭 ±3 秒か重なり、文の近さ 0.3 以上で対応）。F1 × 文の近さの平均
  感想のテロップ 10 … opinion（同じ）
  商品カード 10 … coord・item_card・shiun_card（頭 ±5 秒）の F1
  そのほかのテロップ 10 … price・color・tsukkomi・vertical・topic（頭 ±3 秒）の F1（種類ごとの平均）
  効果音 12 … sfx の種類ごとに（頭 ±0.5 秒）の F1（正解の数で重みづけ）
  インサート 8 … insert:web・insert:cam の時間の重なり（IoU）
"""
import json
import sys
import unicodedata
from difflib import SequenceMatcher


def norm(s):
    return ''.join(ch for ch in unicodedata.normalize('NFKC', s or '') if not ch.isspace())


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def match(G, P, tol, need_text=0.0):
    """頭の差 tol 以内か重なりで、1 対 1 に対応させる（近い順）。返り値: (対応の数, 文の近さの合計)"""
    pairs = []
    for i, g in enumerate(G):
        for j, p in enumerate(P):
            dt = abs(g['start'] - p['start'])
            ov = min(g['end'], p['end']) - max(g['start'], p['start'])
            if dt <= tol or ov > 0.5:
                s = sim(g.get('text'), p.get('text')) if need_text else 1.0
                if s >= need_text:
                    pairs.append((-(s) + dt / 100, i, j, s))
    pairs.sort()
    ug, up, n, ss = set(), set(), 0, 0.0
    for _, i, j, s in pairs:
        if i in ug or j in up:
            continue
        ug.add(i); up.add(j); n += 1; ss += s
    return n, ss


def f1(n, ng, np_):
    if ng == 0 and np_ == 0:
        return 1.0
    if ng == 0 or np_ == 0:
        return 0.0
    p, r = n / np_, n / ng
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def union(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def iou(G, P):
    g, p = union([(e['start'], e['end']) for e in G]), union([(e['start'], e['end']) for e in P])
    inter = 0.0
    for a, b in g:
        for c, d in p:
            inter += max(0.0, min(b, d) - max(a, c))
    tot = sum(b - a for a, b in g) + sum(b - a for a, b in p) - inter
    if tot <= 0:
        return 1.0 if not g and not p else 0.0
    return inter / tot


def main():
    gold = json.load(open(sys.argv[1]))['events']
    pred = json.load(open(sys.argv[2]))['events']
    by = lambda E, *ks: [e for e in E if e['kind'] in ks]
    pts, notes = {}, []
    # 構成
    G, P = by(gold, 'eyecatch'), by(pred, 'eyecatch')
    n, _ = match(G, P, 2.0)
    s_eye = 12 * f1(n, len(G), len(P))
    op = ['op_profile', 'title_call', 'channel', 'sfx:keyboard']
    dur = max(e['end'] for e in gold)
    has = lambda E, k, lo, hi: any(e['kind'] == k and lo <= e['start'] <= hi for e in E)
    s_op = sum(1 for k in op if has(gold, k, 0, 90) == has(pred, k, 0, 90))
    ed = ['channel', 'closing', 'ending']
    s_ed = sum(4 / 3 for k in ed if has(gold, k, dur - 120, dur) == has(pred, k, dur - 120, dur))
    pts['構成'] = round(s_eye + s_op + s_ed, 1)
    notes.append(f'アイキャッチ: 正解 {len(G)}・自作 {len(P)}・対応 {n}')
    # 見出し
    G, P = by(gold, 'heading'), by(pred, 'heading')
    tsim = max([sim(g['text'], p['text']) for g in G for p in P] or [0])
    pts['見出し'] = round(4 * iou(G, P) + 4 * tsim, 1)
    notes.append(f'見出し: 時間の重なり {iou(G, P):.0%}・文 {tsim:.2f}（正解「{G[0]["text"] if G else ""}」）')
    pts['商品番号の箱'] = round(6 * iou(by(gold, 'item_label'), by(pred, 'item_label')), 1)
    # 事実・感想
    for k, w, nm in (('fact', 16, '事実のテロップ'), ('opinion', 10, '感想のテロップ')):
        G, P = by(gold, k), by(pred, k)
        n, ss = match(G, P, 3.0, 0.3)
        pts[nm] = round(w * f1(n, len(G), len(P)) * (ss / n if n else 0), 1)
        notes.append(f'{nm}: 正解 {len(G)}・自作 {len(P)}・対応 {n}・文の近さ {ss / n if n else 0:.2f}')
    G, P = by(gold, 'coord', 'item_card', 'shiun_card'), by(pred, 'coord', 'item_card', 'shiun_card')
    n, _ = match(G, P, 5.0)
    pts['商品カード'] = round(10 * f1(n, len(G), len(P)), 1)
    notes.append(f'商品カード: 正解 {len(G)}・自作 {len(P)}・対応 {n}')
    sc = []
    for k in ('price', 'color', 'tsukkomi', 'vertical', 'topic'):
        G, P = by(gold, k), by(pred, k)
        if not G and not P:
            continue
        n, _ = match(G, P, 3.0)
        sc.append(f1(n, len(G), len(P)))
        notes.append(f'{k}: 正解 {len(G)}・自作 {len(P)}・対応 {n}')
    pts['そのほかのテロップ'] = round(10 * (sum(sc) / len(sc) if sc else 1), 1)
    # 効果音
    kinds = sorted({e['kind'] for e in gold + pred if e['kind'].startswith('sfx:') and e['kind'] != 'sfx:other'})
    tot_g = sum(len(by(gold, k)) for k in kinds) or 1
    s = 0.0
    for k in kinds:
        G, P = by(gold, k), by(pred, k)
        n, _ = match(G, P, 0.5)
        s += f1(n, len(G), len(P)) * max(1, len(G)) / tot_g
        notes.append(f'{k}: 正解 {len(G)}・自作 {len(P)}・対応 {n}')
    pts['効果音'] = round(12 * min(1.0, s), 1)
    pts['インサート'] = round(4 * iou(by(gold, 'insert:web'), by(pred, 'insert:web')) + 4 * iou(by(gold, 'insert:cam'), by(pred, 'insert:cam')), 1)
    total = round(sum(pts.values()), 1)
    print(json.dumps({'score': total, 'parts': pts, 'notes': notes if '--detail' in sys.argv else notes[:3]}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
