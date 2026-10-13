"""自作のラインナップ動画を、完成版（編集者の修正版 XML ＝完成動画と同じ長さ・中身）と比べて 100 点で採点する。
完成動画は修正版 XML をそのまま書き出したもの（長さ 2056.254 秒まで一致）なので、XML どうしを比べれば完成動画との差になる。

    python3 score_vs_final.py OURS.fcpxml FINAL_FLAT.json [--detail] [--exclude 開始-終了 ...]

--exclude: 完成のタイムラインで「ユーザーが入れないと決めた区間」（秒）。何度でも指定できる。
  完成側からその区間を除き（本線・編集点・テロップ・インサート・長さ）、自作側からは同じ素材（同じマルチカム・同じ素材の時刻）の所を除く。
  回ごとの秒数は採点器に書かず、呼ぶ側が渡す。

FINAL_FLAT は fcpxml_flat.py で修正版を平らにしたもの。
項目（合計 100）:
  本線 30  … 完成で使っている本線（マルチカム）の素材の時間を、自作がどれだけ同じ所から使っているか（再現率 20）と、
             完成で使っていない所を使っていないか（適合率 10）
  編集点 15 … 完成の本線の継ぎ目（素材の時刻）に、自作の継ぎ目が 2 コマ以内であるか
  テロップ 25 … 完成のテロップ（字幕・説明・商品名など、調整レイヤー以外）の文を、自作が同じ時刻帯（素材の時刻）に同じ文で持つか
  インサート 20 … 完成のインサート（lane 2 以上の映像）が覆う時間を、自作も覆っているか（10）と、同じ素材を使っているか（10）
  長さ 10  … 全体の長さの差（10 秒ごとに 1 点引く）

テロップ・インサートの時刻は、本線（いちばん長く使っているマルチカム）の素材の時刻に直して比べる（10/13 改め）。
本線の外（身長別ブロック・試着会など）は「直前の本線のカットの素材の終わり＋そこからの秒数」で表す。
こうしないと、片方にだけある区間（素材の無い試着会など）より後ろが全部ずれて、連鎖的に失点する。
テロップは、同じ文のテロップがその時刻を覆っていても一致とする（完成のラベルは本線のカットごとに分かれているため）。
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


class Mapper:
    """タイムラインの時刻 ⇔ 本線の素材の時刻（本線の外は、直前の本線のカットの素材の終わり＋秒数）。"""

    def __init__(self, F):
        from collections import Counter
        c = Counter()
        for x in F:
            if x['lane'] == 0 and x['kind'] == 'mc-clip':
                c[x.get('ref_name') or x.get('name')] += x['end'] - x['start']
        main = c.most_common(1)[0][0] if c else None
        self.segs = sorted((x['start'], x['end'], x['src_in'], x['src_in'] + x['end'] - x['start']) for x in F
                           if x['lane'] == 0 and x['kind'] == 'mc-clip' and (x.get('ref_name') or x.get('name')) == main and x['end'] > x['start'])
        import bisect
        self.bis = bisect
        self.t0s = [a for a, b, c_, d in self.segs]

    def key(self, t):
        i = self.bis.bisect_right(self.t0s, t) - 1
        if i >= 0:
            a, b, s0, s1 = self.segs[i]
            if t < b:
                return ('m', s0 + (t - a))
            return ('g', s1, t - b)
        return ('g', None, t)

    def to_tl(self, k, hint):
        if k[0] == 'm':
            c = [a + (k[1] - s0) for a, b, s0, s1 in self.segs if s0 - 1e-6 <= k[1] < s1]
        elif k[1] is None:
            return k[2]
        else:
            near = [abs(s1 - k[1]) for a, b, s0, s1 in self.segs if abs(s1 - k[1]) <= 1.0]
            if not near:
                return None
            m = min(near)
            c = [b + k[2] for a, b, s0, s1 in self.segs if abs(abs(s1 - k[1]) - m) < 0.05]
        return min(c, key=lambda v: abs(v - hint)) if c else None


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


def named_segs(F):
    return sorted((x['start'], x['end'], x['src_in'], x['src_in'] + x['end'] - x['start'], x.get('ref_name') or x.get('name') or '')
                  for x in F if x['lane'] == 0 and x['kind'] in ('mc-clip', 'asset-clip', 'clip') and x['end'] > x['start'])


def minus(segs, cut):
    """[(tl0, tl1, s0, s1, name)] から、cut(tl0, tl1, s0, s1, name) が返す素材の区間 [(a, b)] を除いた残り"""
    out = []
    for a, b, s0, s1, n in segs:
        pieces = [(s0, s1)]
        for c0, c1 in cut(a, b, s0, s1, n):
            nxt = []
            for p0, p1 in pieces:
                if c1 <= p0 or c0 >= p1:
                    nxt.append((p0, p1))
                    continue
                if p0 < c0:
                    nxt.append((p0, c0))
                if c1 < p1:
                    nxt.append((c1, p1))
            pieces = nxt
        for p0, p1 in pieces:
            if p1 - p0 > 1e-6:
                out.append((a + (p0 - s0), a + (p1 - s0), p0, p1, n))
    return out


def main():
    ours, fin = flat(sys.argv[1]), flat(sys.argv[2])
    detail = '--detail' in sys.argv
    EX = []
    for k, v in enumerate(sys.argv):
        if v == '--exclude':
            a, b = sys.argv[k + 1].split('-')
            EX.append((float(a), float(b)))
    in_ex = lambda t: any(a < t < b for a, b in EX)
    NF, NO = named_segs(fin), named_segs(ours)
    # 完成の除く区間の素材（マルチカムの名前・素材の時刻）
    ex_src = [(n, s0 + max(0, a - t0), s0 + min(t1, b) - t0) for t0, t1, s0, s1, n in NF for a, b in EX if t0 < b and a < t1]
    NFk = minus(NF, lambda t0, t1, s0, s1, n: [(s0 + max(0, a - t0), s0 + min(t1, b) - t0) for a, b in EX if t0 < b and a < t1])
    NOk = minus(NO, lambda t0, t1, s0, s1, n: [(c0, c1) for m, c0, c1 in ex_src if m == n])
    ex_ours_len = sum(t1 - t0 for t0, t1, s0, s1, n in NO) - sum(t1 - t0 for t0, t1, s0, s1, n in NOk)
    So, Sf = main_segs(ours), main_segs(fin)
    pts, notes = {}, []
    # 本線
    srcO, srcF = [(c, d) for a, b, c, d, n in NOk], [(c, d) for a, b, c, d, n in NFk]
    hit = inter(srcO, srcF)
    rec, prec = hit / max(1e-9, total(srcF)), hit / max(1e-9, total(srcO))
    pts['本線'] = (round(20 * rec + 10 * prec, 1), 30)
    notes.append(f'本線: 完成の素材 {total(srcF):.0f} 秒のうち {rec:.1%} を使用・自作の素材のうち {prec:.1%} が完成にもある')
    # 編集点（素材の時刻の継ぎ目）
    cutsF = sorted({round(d, 3) for a, b, c, d in Sf if not in_ex(b)} | {round(c, 3) for a, b, c, d in Sf if not in_ex(a)})
    cutsO = sorted({d for a, b, c, d in So} | {c for a, b, c, d in So})
    import bisect
    def near(v, arr):
        i = bisect.bisect_left(arr, v)
        return min([abs(v - arr[k]) for k in (i - 1, i) if 0 <= k < len(arr)] or [9e9])
    ok = sum(1 for v in cutsF if near(v, cutsO) <= 2 * FD)
    pts['編集点'] = (round(15 * ok / max(1, len(cutsF)), 1), 15)
    notes.append(f'編集点: 完成の継ぎ目 {len(cutsF)} のうち {ok}（{ok / max(1, len(cutsF)):.1%}）が 2 コマ以内')
    # テロップ
    MF, MO = Mapper(fin), Mapper(ours)
    tF, tO = titles(fin, Sf), titles(ours, So)
    spO = [(x['start'], x['end'], norm(x['text'])) for x in ours
           if x['kind'] == 'title' and norm(x.get('text')) and 'Adjustment' not in (x.get('ref_name') or '')]
    good = 0; miss = []
    tF = [x for x in tF if not in_ex(x[3])]
    for s_, t, n, tl in tF:
        T_ = MO.to_tl(MF.key(tl), tl)
        if T_ is None:
            cands = [u for s2, u, n2, tl2 in tO if s_ is not None and s2 is not None and abs(s2 - s_) < 4]
        else:
            cands = [u for a2, b2, u in spO if abs((a2 + b2) / 2 - T_) < 4 or a2 - 0.05 <= T_ <= b2 + 0.05]
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
    # 完成のインサートを 0.1 秒ごとに、本線の素材の時刻を通して自作のタイムラインの時刻に移して比べる
    uO = union([(a, b) for a, b, n in iO])
    import bisect
    u0 = [a for a, b in uO]
    def covered(T_):
        i = bisect.bisect_right(u0, T_) - 1
        return i >= 0 and T_ < uO[i][1]
    iO_s = sorted(iO)
    o0 = [a for a, b, n in iO_s]
    def names_at(T_):
        i = bisect.bisect_right(o0, T_)
        return [n2 for a2, b2, n2 in iO_s[max(0, i - 60):i] if a2 <= T_ < b2]
    step = 0.1
    tot_c = hit_c = 0.0
    for a, b in union([(a, b) for a, b, n in iF]):
        t = a + step / 2
        while t < b:
            if in_ex(t):
                t += step
                continue
            tot_c += step
            T_ = MO.to_tl(MF.key(t), t)
            if T_ is not None and covered(T_):
                hit_c += step
            t += step
    cov = hit_c / max(1e-9, tot_c)
    same = 0.0
    for a, b, n in iF:
        key = re.sub(r'[_\-\s].*', '', n)[:6]
        t = a + step / 2
        while t < b:
            if in_ex(t):
                t += step
                continue
            T_ = MO.to_tl(MF.key(t), t)
            if T_ is not None and key and any(key in n2 for n2 in names_at(T_)):
                same += step
            t += step
    same /= max(1e-9, sum(b - a for a, b, n in iF) - sum(max(0, min(b, y) - max(a, x)) for a, b, n in iF for x, y in EX))
    pts['インサート'] = (round(10 * cov + 10 * same, 1), 20)
    notes.append(f'インサート: 完成の覆う時間のうち {cov:.1%} を自作も覆う・同じ素材 {same:.1%}')
    # 長さ
    LF, LO = max(x['end'] for x in fin), max(x['end'] for x in ours)
    LF -= total([(max(0, a), min(LF, b)) for a, b in EX if b > a])
    LO -= ex_ours_len
    pts['長さ'] = (round(max(0, 10 - abs(LF - LO) / 10), 1), 10)
    notes.append(f'長さ: 完成 {LF:.1f} 秒・自作 {LO:.1f} 秒' + (f'（除いた区間 {len(EX)} か所を引いた長さ）' if EX else ''))
    score = round(sum(v[0] for v in pts.values()), 1)
    res = {'score': score, 'parts': pts, 'notes': notes}
    if detail:
        res['titles_miss'] = miss[:80]
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
