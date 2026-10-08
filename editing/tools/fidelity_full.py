"""テロップの書式を、過去データ（A19・A23）と「全部の値」で突き合わせる。

    python3 fidelity_full.py EDIT_FLAT.json REF_FLAT.json [REF_FLAT.json ...] [-v]

各テロップについて、同じ役割（roles.role）の参照テロップの中から一番近いもの（違う値が一番少ないもの）を探し、
書式（ランごとの font・fontSize・fontFace・fontColor・bold・kerning（文字間隔）・lineSpacing（行間）・baseline・
alignment・縁取り・影）とパラメータ（配置・行間・調整（縦横比）・平坦化 など。位置は別に数える）の違いを出す。
0 件なら、文字の中身と位置以外は過去データと完全に同じ。
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role, text  # noqa: E402

SKIP = {None, 'empty', 'other', 'adjustment_main', 'adjustment_other'}
STYLE_KEYS = ('font', 'fontSize', 'fontFace', 'fontColor', 'bold', 'italic', 'kerning', 'lineSpacing', 'baseline', 'alignment',
              'strokeColor', 'strokeWidth', 'shadowColor', 'shadowOffset', 'shadowBlurRadius')
POS_PARAMS = ('位置',)


def runs(i):
    """空でないランの書式の列（同じ書式が続くものはまとめる）。"""
    out = []
    for t in i['texts']:
        for x in t['runs']:
            if not x['text'].strip():
                continue
            st = i['styles'].get(x['ref'], {})
            s = tuple((k, st.get(k)) for k in STYLE_KEYS)
            if not out or out[-1] != s:
                out.append(s)
    return out


def params(i):
    return {k: v for k, v in (i.get('params') or {}).items() if k not in POS_PARAMS}


def diff(a, b):
    """a（A24）と b（参照）の違い: [(項目, A24 の値, 参照の値)]"""
    d = []
    ra, rb = runs(a), runs(b)
    if len(ra) != len(rb):
        d.append(('ランの数', len(ra), len(rb)))
    for k, (x, y) in enumerate(zip(ra, rb)):
        for (kk, vx), (_, vy) in zip(x, y):
            if vx != vy:
                d.append((f'ラン{k + 1}.{kk}', vx, vy))
    pa, pb = params(a), params(b)
    for k in sorted(set(pa) | set(pb)):
        if pa.get(k) != pb.get(k):
            d.append((f'パラメータ.{k}', pa.get(k), pb.get(k)))
    ea = (a.get('effect') or {}).get('name') if isinstance(a.get('effect'), dict) else a.get('effect')
    eb = (b.get('effect') or {}).get('name') if isinstance(b.get('effect'), dict) else b.get('effect')
    if ea != eb:
        d.append(('エフェクト', ea, eb))
    fa = sorted(f['name'] for f in a.get('filters', []))
    fb = sorted(f['name'] for f in b.get('filters', []))
    if fa != fb:
        d.append(('フィルタ', fa, fb))
    return d


def load(p):
    return [i for i in json.load(open(p)) if i['enabled'] != '0' and len(i['path']) <= 1 and i['tag'] == 'title']


def main():
    edit = load(sys.argv[1])
    refs = defaultdict(list)
    for p in [a for a in sys.argv[2:] if not a.startswith('-')]:
        for i in load(p):
            r = role(i)
            if r not in SKIP:
                refs[r].append(i)
    bad = defaultdict(list)
    keys = Counter()
    total = Counter()
    for i in edit:
        r = role(i)
        if r in SKIP:
            continue
        total[r] += 1
        if not refs[r]:
            bad[r].append((i, [('参照なし', None, None)]))
            continue
        best = min((diff(i, b) for b in refs[r]), key=len)
        if best:
            bad[r].append((i, best))
            for k, *_ in best:
                keys[k.split('.', 1)[-1] if k.startswith('ラン') else k] += 1
    n = sum(len(v) for v in bad.values())
    print(f'過去データと値が違うテロップ: {n} / {sum(total.values())}（文字の中身と位置は除く）')
    if keys:
        print('  違う項目:', dict(keys.most_common()))
    for r, xs in sorted(bad.items(), key=lambda kv: -len(kv[1])):
        print(f'== {r}: {len(xs)} / {total[r]}')
        for i, d in xs[:3 if '-v' in sys.argv else 1]:
            print('   ', round(i['t0'], 1), text(i)[:30].replace('\n', '/'), '→', d[:6])


if __name__ == '__main__':
    main()
