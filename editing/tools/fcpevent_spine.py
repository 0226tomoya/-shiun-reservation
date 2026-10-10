"""FCP のライブラリ（.fcpbundle の中の CurrentVersion.fcpevent。SQLite＋NSKeyedArchiver）から、プロジェクトのスパインの並びを取り出す。

    python3 fcpevent_spine.py CurrentVersion.fcpevent OUT.json

出力: [{"kind": "angle"|"gap"|..., "src_start": 秒, "dur": 秒, "name": ...}, ...]（タイムラインの順）
FFAnchoredAngle の clippedRange = {(素材の頭),(長さ)}（マルチカムの時刻＝ピンマイク音声の時刻）。
"""
import json
import plistlib
import re
import sqlite3
import sys
from fractions import Fraction


def unarchive(data):
    p = plistlib.loads(data)
    objs = p['$objects']

    def dec(u, depth=0):
        if depth > 60:
            return None
        o = objs[u.data] if isinstance(u, plistlib.UID) else u
        if isinstance(o, plistlib.UID):
            return dec(o, depth + 1)
        if isinstance(o, dict):
            if 'NS.keys' in o:
                return {str(dec(k, depth + 1)): dec(v, depth + 1) for k, v in zip(o['NS.keys'], o['NS.objects'])}
            if 'NS.objects' in o:
                return [dec(v, depth + 1) for v in o['NS.objects']]
            if 'NS.string' in o:
                return o['NS.string']
            return {k: dec(v, depth + 1) for k, v in o.items() if k != '$class'}
        return None if o == '$null' else o
    return dec(p['$top']['root'])


def frac(s):
    a, b = s.split('/')
    return Fraction(int(a), int(b))


def main():
    db, out = sys.argv[1:3]
    c = sqlite3.connect(db)
    md = {}
    for pk, d in c.execute('select ZCOLLECTION, ZDICTIONARYDATA from ZCOLLECTIONMD'):
        try:
            md[pk] = unarchive(d)
        except Exception:
            pass
    rows = {pk: (typ, name, ident) for pk, typ, name, ident in c.execute('select Z_PK, ZTYPE, ZNAME, ZIDENTIFIER from ZCOLLECTION')}
    kids = {}
    for par, ch in c.execute('select Z_3PARENTCOLLECTIONS, Z_3CHILDCOLLECTIONS from Z_3CHILDCOLLECTIONS'):
        kids.setdefault(par, []).append(ch)
    by_ident = {v[2]: k for k, v in rows.items() if v[2]}
    proj = [k for k, v in rows.items() if v[0] == 'FFAnchoredCollection' and (md.get(k) or {}).get('isProject') in (True, 'True')]
    res = []
    for pj in proj:
        ci = [k for k in kids.get(pj, []) if rows[k][1] == 'containedItems'][0]
        order = (md.get(ci) or {}).get('$order') or []
        for ident in order:
            k = by_ident.get(ident)
            if k is None:
                continue
            typ, _, _ = rows[k]
            m = md.get(k) or {}
            cr = m.get('clippedRange')
            if cr:
                a, b = re.findall(r'\(([-0-9]+/[0-9]+)\)', cr)
                res.append({'kind': typ, 'src_start': float(frac(a)), 'dur': float(frac(b)), 'name': m.get('displayName')})
            else:
                res.append({'kind': typ, 'name': m.get('displayName'), 'keys': sorted(m)[:12]})
        break
    json.dump(res, open(out, 'w'), ensure_ascii=False, indent=0)
    t = sum(x.get('dur', 0) for x in res)
    from collections import Counter
    print(len(res), '要素', round(t, 2), '秒', Counter(x['kind'] for x in res))


if __name__ == '__main__':
    main()
