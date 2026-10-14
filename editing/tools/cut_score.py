"""自動のカット（EDL）を、ユーザー（編集者）が直したカット（EDL）と比べて点を付ける。カットの評価ループに使う。
    python3 cut_score.py OURS.json USER.json [--detail]

比べるのは本線（マイクのある clip）だけ。時刻はマイクの時刻（in/out + offset）で比べる。
- 残した時間の一致: 適合率（こちらが残した中でユーザーも残した割合）・再現率（ユーザーが残した中でこちらも残した割合）・F1
- 編集点の位置: ユーザーの編集点（カットの頭・尾）ごとに、0.25 秒以内にあるこちらの同じ側の編集点との差（中央値）と、見つかった割合
- 長さ: こちら ÷ ユーザー
点（100 点満点）= F1×50 + 編集点が見つかった割合×20 + 編集点の差（0 秒で 15 点、0.06 秒以上で 0 点）+ 長さ（1.0 で 15 点、±30% で 0 点）
"""
import json
import sys

import numpy as np

R = 0.005  # 5ms の格子で比べる


def mask(edl):
    m = {}
    edges = {'head': [], 'tail': []}
    for s in edl['segments']:
        c = edl['clips'][s['clip']]
        if not c.get('mic'):
            continue
        a, b = s['in'] + c['offset'], s['out'] + c['offset']
        arr = m.setdefault(c['mic'], np.zeros(int(2000 / R), bool))
        arr[int(a / R):int(b / R)] = True
        edges['head'].append((c['mic'], a))
        edges['tail'].append((c['mic'], b))
    return m, edges


def score(ours, user, detail=False):
    mo, eo = mask(ours)
    mu, eu = mask(user)
    tp = sum(int((mo.get(k, 0) & v).sum()) for k, v in mu.items()) * R
    ko = sum(int(v.sum()) for v in mo.values()) * R
    ku = sum(int(v.sum()) for v in mu.values()) * R
    P, Rc = tp / max(ko, 1e-9), tp / max(ku, 1e-9)
    F = 2 * P * Rc / max(P + Rc, 1e-9)
    errs, found = [], 0
    for side in ('head', 'tail'):
        for k, t in eu[side]:
            cand = [abs(t - t2) for k2, t2 in eo[side] if k2 == k and abs(t - t2) <= 0.25]
            if cand:
                found += 1
                errs.append(min(cand))
    n = len(eu['head']) + len(eu['tail'])
    fr = found / max(n, 1)
    med = float(np.median(errs)) if errs else 0.25
    ratio = ko / max(ku, 1e-9)
    pts = F * 50 + fr * 20 + max(0, 1 - med / 0.06) * 15 + max(0, 1 - abs(ratio - 1) / 0.3) * 15
    out = {'点': round(pts, 1), '適合率': round(P, 3), '再現率': round(Rc, 3), 'F1': round(F, 3), '編集点が見つかった割合': round(fr, 3),
           '編集点の差の中央値': round(med, 3), '長さ': f'{ko:.1f} / {ku:.1f} 秒', 'カット数': f"{len(eo['head'])} / {len(eu['head'])}"}
    if detail:
        # ユーザーが削ったのにこちらが残した区間（0.3 秒以上）
        extra = []
        for k, v in mo.items():
            d = v & ~mu.get(k, np.zeros_like(v))
            idx = np.flatnonzero(np.diff(np.r_[0, d.astype(int), 0]))
            for a, b in zip(idx[::2], idx[1::2]):
                if (b - a) * R >= 0.3:
                    extra.append((k, round(a * R, 2), round(b * R, 2)))
        out['残しすぎ'] = extra
    return out


if __name__ == '__main__':
    print(json.dumps(score(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), '--detail' in sys.argv), ensure_ascii=False))
