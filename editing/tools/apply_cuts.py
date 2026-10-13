"""粗編集の本編から、指定した区間を切り取る（ユーザーの「丸ごとカット」の指示）。

    python3 apply_cuts.py ROUGH.fcpxml PLAN.json OUT.fcpxml SUBJECT_IN.json SUBJECT_OUT.json

plan.edits.cuts: [[頭, 終わり], ...]（秒。v1（組み立て後）の時刻 = 確認動画の時刻）。
v1 の時刻は、カウントダウン（と最初の商品の頭のアイキャッチ）の後ろでは粗編集より長いので、plan.edits.v1_offsets
（[[v1 の時刻, その時刻より後ろで v1 が粗編集より長い秒数], ...]）で粗編集の時刻に直す。
切る位置はフレームに揃える。カットの途中で切るときは、そのカットを短くする（両側にかかるときは 2 つに分ける）。
SUBJECT（カットごとの人の位置）も同じように消す・分ける。
"""
import copy
import json
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fraction(int(a), int(b))
    return Fraction(s)


def S(f):
    f = Fraction(f)
    return f'{f.numerator}/{f.denominator}s' if f.denominator != 1 else f'{f.numerator}s'


def voice_map(mic):
    import subprocess
    import numpy as np
    sr, hop = 16000, 160
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', mic, '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = len(a) // hop
    db = 20 * np.log10(np.sqrt((a[:n * hop].reshape(n, -1) ** 2).mean(1)) + 1e-9)
    return db > np.percentile(db, 10) + 14


_VM = {}


def fit_to_voice(a, b, items, mic, fd):
    """カットの端を声に合わせる（粗編集の切り方: 前の終わりは言い終わりの約 0.1 秒後、次の頭は言い始めの少し前）。
    a, b は粗編集の時刻。マルチカムの start はピンマイク音声の時刻と同じ。"""
    if mic not in _VM:
        _VM[mic] = voice_map(mic)
    vm = _VM[mic]
    H = Fraction(1, 100)

    def voiced(t):
        i = int(t / H)
        return 0 <= i < len(vm) and bool(vm[i])

    def src(t):
        for e in items:
            off, du = T(e.get('offset')), T(e.get('duration'))
            if e.tag == 'mc-clip' and off <= t < off + du:
                return e, T(e.get('start')) + (t - off), off
        return None, None, None
    # 前の終わり: そこから前に戻って、6 回（60ms）以上続く無音の直前の声の終わりを探す
    e, sa, off = src(a - fd)
    if e is not None:
        sa = sa + fd
        k = sa
        while k > sa - 2 and voiced(k - H):  # 次の発言の頭が入っていたら、その頭まで戻す
            k -= H
        while k > sa - 2 and not voiced(k - H):
            k -= H
        end_voice = k
        if end_voice > T(e.get('start')):
            na = a - (sa - min(sa, end_voice + Fraction(1, 10)))
            a = round(na / fd) * fd
        else:
            # 言い終わりがこのカットより前（前のカットの中）: このカットの頭から切る（前のカットの終わりは粗編集のまま）
            a = off
    # 次の頭: 粗編集のカットの頭ちょうどならそのまま、そうでなければ言い始めの 0.08 秒前
    e, sb, off = src(b)
    if e is not None and abs(b - off) > fd:
        k = sb
        while k < sb + 2 and not voiced(k):
            k += H
        while k > sb - Fraction(1, 2) and voiced(k - H):
            k -= H
        nb = b + (k - Fraction(8, 100) - sb)
        b = max(round(nb / fd) * fd, off)
    return a, b


def main():
    rough, plan_path, out, subj_in, subj_out = sys.argv[1:6]
    mic = sys.argv[sys.argv.index('--mic') + 1] if '--mic' in sys.argv else None
    plan = json.load(open(plan_path, encoding='utf-8'))
    ed = plan['edits']
    tree = ET.parse(rough)
    root = tree.getroot()
    res = {e.get('id'): e for e in root.find('resources')}
    proj = [p for p in root.iter('project')][0]
    seq = proj.find('sequence')
    fd = T(res[seq.get('format')].get('frameDuration'))
    spine = seq.find('spine')
    subject = json.load(open(subj_in, encoding='utf-8'))

    def to_rough(t):
        t = Fraction(str(t))
        sh = 0
        for at, d in ed.get('v1_offsets', []):
            if t >= Fraction(str(at)):
                sh = Fraction(str(d))
        return round((t - sh) / fd) * fd

    cuts = sorted((to_rough(a), to_rough(b)) for a, b in ed['cuts'])
    items = list(spine)
    # 素材の時刻で指定したカット（タイムラインの時刻のずれに影響されない）: 粗編集でその素材を含むカットを探して粗編集の時刻に直す
    for sa, sb in ed.get('src_cuts', []):
        sa, sb = Fraction(str(sa)), Fraction(str(sb))
        hit = [e for e in items if e.tag == 'mc-clip' and T(e.get('start')) <= sa < T(e.get('start')) + T(e.get('duration'))]
        if len(hit) != 1:
            raise SystemExit(f'素材の時刻 {float(sa)} を含むカットが {len(hit)} 本（1 本でないと決められない）')
        e = hit[0]
        o, st, du = T(e.get('offset')), T(e.get('start')), T(e.get('duration'))
        ra = o + (sa - st)
        rb = o + (min(sb, st + du) - st)
        cuts.append((round(ra / fd) * fd, round(rb / fd) * fd))
    # 自動の仕上げカット（スキル shiun-finish-cut の「必ず切っていたもの」）: 身長別比較の直前は「〜の動画が」で止め、
    # その後の「こちらです。どうぞ。」は削る（差し込む映像がその答えになる）。--words（remap_transcript.py --src）が要る
    if '--words' in sys.argv and plan.get('subtitles'):
        import os
        import re
        W = json.load(open(sys.argv[sys.argv.index('--words') + 1], encoding='utf-8'))
        subs = json.load(open(os.path.join(os.path.dirname(os.path.abspath(plan_path)), plan['subtitles']), encoding='utf-8'))
        rows = {}
        for w in W:
            rows.setdefault(w[4], []).append(w)
        auto = []
        for ch, k in subs.get('size_compare_at', {}).items():
            k = int(k)
            r0 = next((r for r in range(k, k + 4) if '動画' in ''.join(w[3] for w in rows.get(r, []))), None)
            if r0 is None:
                continue
            ws = [w for r in range(r0, r0 + 3) for w in rows.get(r, [])]
            txt, pos = '', []
            for w in ws:
                pos.append(len(txt))
                txt += w[3]
            m = re.search(r'動画が、?(こちら(?:です)?(?:ね)?[、。]?(?:どうぞ[。、]?)?)', txt)
            if not m:
                continue
            i0 = max(i for i, p_ in enumerate(pos) if p_ <= m.start(1))
            i1 = max(i for i, p_ in enumerate(pos) if p_ < m.end(1))
            auto.append((Fraction(str(ws[i0][1])), Fraction(str(ws[i1][2])), ch, m.group(1)))
        auto_end = {}
        for sa, sb, ch, said in auto:
            for e in items:
                if e.tag != 'mc-clip':
                    continue
                st, du = T(e.get('start')), T(e.get('duration'))
                a_, b_ = max(sa, st), min(sb, st + du)
                if b_ - a_ > Fraction(1, 20):
                    o = T(e.get('offset'))
                    cuts.append((round((o + a_ - st) / fd) * fd, round((o + b_ - st) / fd) * fd))
                    auto_end[ch] = max(auto_end.get(ch, Fraction(0)), o + b_ - st)
            print('自動の仕上げカット（身長別の直前）:', ch, said, round(float(sa), 2), '〜', round(float(sb), 2))

        # ---- 中身で削る仕上げカットの候補（スキル shiun-cut-content-trim）----
        # plan.edits.content_trim が "auto" のときだけ切る。それ以外は候補を書き出すだけ（ユーザーに選んでもらう）
        def src_to_rough(t):
            for e in items:
                if e.tag == 'mc-clip':
                    st, du = T(e.get('start')), T(e.get('duration'))
                    if st <= t < st + du:
                        return T(e.get('offset')) + (t - st)
            # 語の終わりがカットの終わりを少し越える（言い終わりの後でカットしてある）ときは、そのカットの終わり
            for e in items:
                if e.tag == 'mc-clip':
                    st, du = T(e.get('start')), T(e.get('duration'))
                    if st + du <= t < st + du + Fraction(3, 10):
                        return T(e.get('offset')) + du
            return None
        chapters_r = sorted(T(e.get('offset')) + T(m.get('start')) - T(e.get('start'))
                            for e in items for m in e.findall('chapter-marker'))
        row_txt = {r: ''.join(w[3] for w in ws_) for r, ws_ in rows.items()}
        row_t = {r: (Fraction(str(ws_[0][1])), Fraction(str(ws_[-1][2]))) for r, ws_ in rows.items()}
        cand = []
        # 1) 身長別比較の後に残ったトーク（在庫・再販の念押しなど）: 差し込みの後〜次の商品（チャプター）まで。60 秒以内のときだけ
        for ch, ra in auto_end.items():
            nxt = next((c for c in chapters_r if c > ra + Fraction(1, 2)), None)
            if nxt is not None and nxt - ra <= 60:
                cand.append(('身長別の後のトーク', ch, ra, nxt))
        # 2) 価格の 2 回目: 同じ金額を後で（10 行以上後、ED でも）もう一度言うなら、先に言った方の段落（価格の行〜「幸いです」の行、45 秒以内）を削る
        def amounts(t):
            t = t.replace(',', '').replace('，', '')
            out = set(re.findall(r'(\d{3,6})円', t))
            for m_ in re.finditer(r'(\d)万(\d{0,4})円', t):
                out.add(str(int(m_.group(1)) * 10000 + (int(m_.group(2)) if m_.group(2) else 0)))
            return out
        rs = sorted(rows)
        for i_, r in enumerate(rs):
            if 'プライス' not in row_txt[r] and '価格' not in row_txt[r]:
                continue
            am = set().union(*(amounts(row_txt[q]) for q in rs[i_:i_ + 3]))
            am = {a for a in am if int(a) >= 1000}
            if not am:
                continue
            t0 = row_t[r][0]
            # 「後で」は動画の順（行番号の順。素材の時刻は撮った順なので ED が先のこともある）で 10 行以上後
            later = [q for q in rs if q >= r + 10 and amounts(row_txt[q]) & am]
            if not later:
                continue
            end_r = next((q for q in rs[i_:i_ + 20] if row_t[q][0] - t0 <= 45 and row_txt[q].rstrip('。、').endswith('幸いです')), None)
            if end_r is None:
                continue
            a_, b_ = src_to_rough(t0), src_to_rough(row_t[end_r][1] - Fraction(1, 100))
            if a_ is not None and b_ is not None and b_ > a_:
                cand.append(('価格の 2 回目（先に言った方）', ','.join(sorted(am)), a_, b_ + Fraction(1, 100)))
        # 4) 締めのまとめ: 価格を言う直前に、その商品で説明済みの特徴を並べ直すかたまり（「そんな〜、」で挟まれた 3 文以上、
        #    言葉の 5 割以上がその商品の前の発言にある）を削る。後ろの「そんな（ね）、」も一緒に（「そんな〜ローファーが」につながる）
        def bigr(t):
            t = re.sub(r'[、。\s]', '', t)
            return [t[i:i + 2] for i in range(len(t) - 1)]
        for i_, r in enumerate(rs):
            if 'プライス' not in row_txt[r] and '価格' not in row_txt[r]:
                continue
            ra_ = src_to_rough(row_t[r][0])
            if ra_ is None:
                continue
            ch0 = max([c for c in chapters_r if c <= ra_], default=Fraction(0))
            j_ = i_ - 1  # 価格の直前の「そんな」
            while j_ > i_ - 5 and j_ > 0 and not row_txt[rs[j_]].startswith('そんな'):
                j_ -= 1
            if not row_txt[rs[j_]].startswith('そんな'):
                continue
            k_ = j_ - 1  # その前の「そんな」まで戻る（最大 20 行）
            while k_ > j_ - 20 and k_ > 0 and not row_txt[rs[k_]].startswith('そんな'):
                k_ -= 1
            if not row_txt[rs[k_]].startswith('そんな') or j_ - k_ < 4:
                continue
            block = rs[k_ + 1:j_ + 1]
            n_sent = sum(row_txt[q].rstrip().endswith('。') for q in block)
            earlier = ''.join(row_txt[q] for q in rs[:k_] if (src_to_rough(row_t[q][0]) or Fraction(-1)) >= ch0)
            bg = bigr(''.join(row_txt[q] for q in block[:-1]))
            ov = sum(b in earlier for b in bg) / max(1, len(bg))
            a_, b_ = src_to_rough(row_t[block[0]][0]), src_to_rough(row_t[block[-1]][1] - Fraction(1, 100))
            if n_sent >= 3 and ov >= 0.5 and a_ is not None and b_ is not None and Fraction(8) <= b_ - a_ <= 45:
                cand.append(('締めのまとめ', f'言葉の重なり {ov:.0%}', a_, b_ + Fraction(1, 100)))
        # 3) 入らない差し込みの予告（スキル shiun-trial-event-insert / shiun-finish-cut の 3）:
        #    「この後に（短いバージョンで）差し込んでおきます」と言っていても、差し込む素材（plan.trial_event）が無いなら、
        #    予告の文（文の頭〜「ご覧ください」）と、続けて同じ話をしている文（別動画・長いバージョン・感想）を切る
        if not plan.get('trial_event'):
            for i_, r in enumerate(rs):
                if '差し込' not in row_txt[r]:
                    continue
                j0 = i_
                while j0 > 0 and i_ - j0 < 8 and not row_txt[rs[j0 - 1]].rstrip().endswith(('。', '？', '!', '！')):
                    j0 -= 1
                j1 = i_
                while j1 + 1 < len(rs) and j1 - i_ < 8 and not row_txt[rs[j1]].rstrip().endswith(('。', '？', '！')):
                    j1 += 1
                # 続けて同じ話（別動画・長いバージョン・感想）をしている文も
                while j1 + 1 < len(rs):
                    k_ = j1 + 1
                    sent = []
                    while k_ < len(rs) and k_ - j1 <= 8:
                        sent.append(rs[k_])
                        if row_txt[rs[k_]].rstrip().endswith(('。', '？', '！')):
                            break
                        k_ += 1
                    if re.search(r'別動画|バージョン|感想|差し込', ''.join(row_txt[q] for q in sent)):
                        j1 = k_
                    else:
                        break
                a_ = src_to_rough(row_t[rs[j0]][0])
                b_ = src_to_rough(row_t[rs[j1]][1] - Fraction(1, 100))
                if a_ is not None and b_ is not None and b_ > a_:
                    cand.append(('入らない差し込みの予告', ''.join(row_txt[q] for q in rs[j0:j1 + 1])[:30], a_, b_ + Fraction(1, 100)))
                    print('自動の仕上げカット（入らない差し込みの予告）:', ''.join(row_txt[q] for q in rs[j0:j1 + 1]))
        for kind, ch, a_, b_ in cand:
            print('中身で削る候補:', kind, ch, '粗編集', round(float(a_), 2), '〜', round(float(b_), 2), f'({float(b_ - a_):.1f} 秒)')
        # 入らない差し込みの予告は必ず切る（予告だけ残ると視聴者が探す）。中身で削る候補は content_trim = "auto" のとき
        cuts += [(round(a_ / fd) * fd, round(b_ / fd) * fd) for k_, _, a_, b_ in cand
                 if k_ == '入らない差し込みの予告' or ed.get('content_trim') == 'auto']
    cuts.sort()
    # 重なる・接するカットはまとめる
    merged = []
    for a, b in cuts:
        if merged and a <= merged[-1][1] + fd:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    cuts = merged
    if mic:
        cuts = [fit_to_voice(a, b, items, mic, fd) for a, b in cuts]
    for a, b in cuts:
        if b <= a:
            raise SystemExit(f'カットの頭と終わりが逆: {float(a):.3f} → {float(b):.3f}（指定の時刻を確かめる）')
    mc_index = []  # spine の各要素が subject の何番目か（mc-clip だけ）
    k = 0
    for e in items:
        mc_index.append(k if e.tag == 'mc-clip' else None)
        if e.tag == 'mc-clip':
            k += 1
    new_items, new_subj = [], []
    removed = 0
    for e, si in zip(items, mc_index):
        off, du, st = T(e.get('offset')), T(e.get('duration')), T(e.get('start'))
        pieces = [(off, off + du)]
        for a, b in cuts:
            nxt = []
            for p0, p1 in pieces:
                if b <= p0 or a >= p1:
                    nxt.append((p0, p1))
                    continue
                if p0 < a:
                    nxt.append((p0, a))
                if b < p1:
                    nxt.append((b, p1))
            pieces = nxt
        if not pieces:
            removed += 1
            continue
        for p0, p1 in pieces:
            x = copy.deepcopy(e) if len(pieces) > 1 or (p0, p1) != (off, off + du) else e
            x.set('start', S(st + (p0 - off)))
            x.set('duration', S(p1 - p0))
            # マーカー（チャプター）は残した範囲にあるものだけ
            for m in list(x):
                if m.tag in ('chapter-marker', 'marker'):
                    ms = T(m.get('start'))
                    if not (st + (p0 - off) <= ms < st + (p1 - off)):
                        x.remove(m)
            new_items.append(x)
            if si is not None:
                new_subj.append(subject[si])
    for e in list(spine):
        spine.remove(e)
    cur = Fraction(0)
    for e in new_items:
        e.set('offset', S(cur))
        spine.append(e)
        cur += T(e.get('duration'))
    seq.set('duration', S(cur))
    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))
    json.dump(new_subj, open(subj_out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('カット', [(round(float(a), 2), round(float(b), 2)) for a, b in cuts], '| 消したカット', removed,
          '| 本編', len(items), '→', len(new_items), '| 長さ', round(float(cur), 2), '秒 ->', out)


if __name__ == '__main__':
    main()
