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
    cuts.sort()
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
