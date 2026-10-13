"""自作のラインナップ動画を、完成版（編集者の修正版 XML ＝完成動画と同じ長さ・中身）と比べて 100 点で採点する。
完成動画は修正版 XML をそのまま書き出したもの（長さ 2056.254 秒まで一致）なので、XML どうしを比べれば完成動画との差になる。

    python3 score_vs_final.py OURS.fcpxml FINAL_FLAT.json [--detail]

FINAL_FLAT は fcpxml_flat.py で修正版を平らにしたもの。
項目（合計 100）:
  本線 30  … 完成で使っている本線（マルチカム）の素材の時間を、自作がどれだけ同じ所から使っているか（再現率 20）と、
             完成で使っていない所を使っていないか（適合率 10）
  編集点 15 … 完成の本線の継ぎ目（素材の時刻）に、自作の継ぎ目が 2 コマ以内であるか
  テロップ 25 … 完成のテロップ（字幕・説明・商品名など、調整レイヤー以外）の文を、自作が同じ時刻帯（素材の時刻）に同じ文で持つか
  インサート 20 … 完成のインサート（lane 2 以上の映像）が覆う時間を、自作も覆っているか（10）と、同じ素材を使っているか（10）
  長さ 10  … 全体の長さの差（10 秒ごとに 1 点引く）
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
FD = 1001 / 60000


def flat(path):
    if path.endswith('.json'):
        return json.load(open(path))
    out = tempfile.mktemp(suffix='.json')
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'fcpxml_flat.py'), path, out], check=True, capture_output=True)
    return json.load(open(out))


def main_segs(F):
    """本線（lane 0 のマルチカム）: [(tl0, tl1, src0, src1)]"""
    return sorted((x['start'], x['end'], x['src_in'], x['src_in'] + x['end'] - x['start'])
                  for x in F if x['lane'] == 0 and x['kind'] in ('mc-clip', 'asset-clip', 'clip') and x['end'] > x['start'])


def union(iv):
    iv = sorted(iv); out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def inter(A, B):
    A, B = union(A), union(B); i = j = 0; s = 0.0
    while i < len(A) and j < len(B):
        lo, hi = max(A[i][0], B[j][0]), min(A[i][1], B[j][1])
        if hi > lo:
            s += hi - lo
        if A[i][1] < B[j][1]:
            i += 1
        else:
            j += 1
    return s


def total(A):
    return sum(b - a for a, b in union(A))


def norm(t):
    t = unicodedata.normalize('NFKC', t or '')
    return re.sub(r'\s+', '', t)


def to_src(segs, t):
    for a, b, s0, s1 in segs:
        if a <= t < b:
            return s0 + (t - a)
    return None


def titles(F, segs):
    """調整レイヤー・空の文字以外のテロップ: [(素材の時刻, 文, 名前)]（本線の素材の時刻に直して比べる）"""
    out = []
    for x in F:
        if x['kind'] != 'title' or not norm(x.get('text')) or 'Adjustment' in (x.get('ref_name') or ''):
            continue
        s = to_src(segs, (x['start'] + x['end']) / 2)
        out.append((s, norm(x['text']), x.get('name') or '', x['start']))
    return out


def inserts(F):
    return [(x['start'], x['end'], (x.get('name') or x.get('ref_name') or '')) for x in F
            if x['lane'] >= 2 and x['kind'] in ('video', 'clip', 'asset-clip', 'ref-clip', 'mc-clip') and x['end'] > x['start'] >= 0]


def main():
    ours, fin = flat(sys.argv[1]), flat(sys.argv[2])
    detail = '--detail' in sys.argv
    So, Sf = main_segs(ours), main_segs(fin)
    pts, notes = {}, []
    # 本線
    srcO, srcF = [(c, d) for a, b, c, d in So], [(c, d) for a, b, c, d in Sf]
    hit = inter(srcO, srcF)
    rec, prec = hit / max(1e-9, total(srcF)), hit / max(1e-9, total(srcO))
    pts['本線'] = (round(20 * rec + 10 * prec, 1), 30)
    notes.append(f'本線: 完成の素材 {total(srcF):.0f} 秒のうち {rec:.1%} を使用・自作の素材のうち {prec:.1%} が完成にもある')
    # 編集点（素材の時刻の継ぎ目）
    cutsF = sorted({round(d, 3) for a, b, c, d in Sf} | {round(c, 3) for a, b, c, d in Sf})
    cutsO = sorted({d for a, b, c, d in So} | {c for a, b, c, d in So})
    import bisect
    def near(v, arr):
        i = bisect.bisect_left(arr, v)
        return min([abs(v - arr[k]) for k in (i - 1, i) if 0 <= k < len(arr)] or [9e9])
    ok = sum(1 for v in cutsF if near(v, cutsO) <= 2 * FD)
    pts['編集点'] = (round(15 * ok / max(1, len(cutsF)), 1), 15)
    notes.append(f'編集点: 完成の継ぎ目 {len(cutsF)} のうち {ok}（{ok / max(1, len(cutsF)):.1%}）が 2 コマ以内')
    # テロップ
    tF, tO = titles(fin, Sf), titles(ours, So)
    good = 0; miss = []
    for s, t, n, tl in tF:
        cands = [u for s2, u, n2, tl2 in tO if s is not None and s2 is not None and abs(s2 - s) < 4] or \
                [u for s2, u, n2, tl2 in tO if abs(tl2 - tl) < 4]
        r = max([SequenceMatcher(None, t, u).ratio() for u in cands] or [0])
        good += r
        if r < 0.8:
            miss.append((round(tl, 1), t[:28], round(r, 2)))
    isph = lambda t: re.search(r'追加予定|\(仮\)|（仮）', t)
    ph = [t for s, t, n, tl in tO if isph(t)]
    extra_ph = max(0, len(ph) - len([t for s, t, n, tl in tF if isph(t)]))  # 完成にもある仮置き（スナップ待ち）は引かない
    sc = 25 * good / max(1, len(tF)) - min(5, extra_ph)
    pts['テロップ'] = (round(max(0, sc), 1), 25)
    notes.append(f'テロップ: 完成 {len(tF)} 本・自作 {len(tO)} 本・文の一致 {good / max(1, len(tF)):.1%}・合わない {len(miss)}・仮置き {len(ph)}')
    # インサート
    iF, iO = inserts(fin), inserts(ours)
    cov = inter([(a, b) for a, b, n in iO], [(a, b) for a, b, n in iF]) / max(1e-9, total([(a, b) for a, b, n in iF]))
    same = 0.0
    for a, b, n in iF:
        key = re.sub(r'[_\-\s].*', '', n)[:6]
        if any(min(b, b2) - max(a, a2) > 0 and key and key in n2 for a2, b2, n2 in iO):
            same += b - a
    same /= max(1e-9, sum(b - a for a, b, n in iF))
    pts['インサート'] = (round(10 * cov + 10 * same, 1), 20)
    notes.append(f'インサート: 完成の覆う時間のうち {cov:.1%} を自作も覆う・同じ素材 {same:.1%}')
    # 長さ
    LF, LO = max(x['end'] for x in fin), max(x['end'] for x in ours)
    pts['長さ'] = (round(max(0, 10 - abs(LF - LO) / 10), 1), 10)
    notes.append(f'長さ: 完成 {LF:.1f} 秒・自作 {LO:.1f} 秒')
    score = round(sum(v[0] for v in pts.values()), 1)
    res = {'score': score, 'parts': pts, 'notes': notes}
    if detail:
        res['titles_miss'] = miss[:80]
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
