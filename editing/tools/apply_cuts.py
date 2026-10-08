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


def main():
    rough, plan_path, out, subj_in, subj_out = sys.argv[1:6]
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
