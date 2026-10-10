"""FCP のライブラリのプロジェクト（CurrentVersion.fcpevent）から、テロップを 1 つずつ取り出す。

    python3 fcpevent_titles.py CurrentVersion.fcpevent OUT.json

1 行 = タイトルの中の 1 テキスト: 型（基本タイトル・カスタムなど）・レーン・長さ・文言・フォント・サイズ・色・
位置（Motion の 情報/変形/位置）・字間・行間・縁取り/影/グローの有無・クリップ側の変形（FFHeXForm3DEffect）。
文言と書式は FFMotionEffectValue の ozml（Motion の書き出し）に入っている。FCPXML の
key="9999/…/1/100/101"（位置）と同じ場所。
"""
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from fcpevent_spine import unarchive  # noqa: E402


def frac(s):
    a, b = s.split('/')
    return Fraction(int(a), int(b))


def pair(s):
    v = re.findall(r'\(([-0-9]+/[0-9]+)\)', s or '')
    return [float(frac(x)) for x in v]


def sub(p, i):
    for c in p.findall('parameter'):
        if c.get('id') == str(i):
            return c
    return None


def cval(p):
    if p is None:
        return None
    if p.get('value') is not None:
        return float(p.get('value'))
    c = p.find('curve')
    return float(c.get('value')) if c is not None and c.get('value') is not None else None


def enabled(p):
    # flags の最下位ビットが 1 ＝ 有効（Motion の ozml）
    f = p.get('flags') or (p.findtext('flags') or '0')
    return bool(int(f) & 1)


def parse_text(xml):
    root = ET.fromstring(re.sub(r'<!DOCTYPE[^>]*>', '', xml))
    out = []
    for node in root.iter('scenenode'):
        t = node.find('.//text')
        if t is None:
            continue
        r = {'node': node.get('name'), 'text': t.text or ''}
        styles = []
        for st in node.findall('style'):
            s = {}
            f = st.find("parameter[@id='83']")
            if f is not None:
                s['font'] = f.findtext('font')
            s['size'] = cval(st.find("parameter[@id='3']"))
            face = st.find("parameter[@id='14']")
            col = sub(face, 16) if face is not None else None
            if col is not None:
                s['color'] = [round(cval(sub(col, k)) or 0, 4) for k in (1, 2, 3)]
            for nm, i in (('shadow', 21), ('outline', 30), ('glow', 38)):
                p = st.find(f"parameter[@id='{i}']")
                if p is not None:
                    s[nm] = enabled(p)
            ol = st.find("parameter[@id='30']")
            if ol is not None and enabled(ol):
                w = sub(ol, 33)
                s['outline_width'] = cval(w)
                oc = sub(ol, 31)
                if oc is not None:
                    s['outline_color'] = [round(cval(sub(oc, k)) or 0, 4) for k in (1, 2, 3)]
            tr = st.find("parameter[@id='5']")  # 字間（トラッキング）
            if tr is not None:
                s['tracking'] = cval(tr)
            styles.append(s)
        r['styles'] = styles
        info = sub(node, 1)
        xf = sub(info, 100) if info is not None else None
        pos = sub(xf, 101) if xf is not None else None
        if pos is not None:
            r['pos'] = [cval(sub(pos, 1)), cval(sub(pos, 2))]
        sc = sub(xf, 105) if xf is not None else None
        if sc is not None:
            r['scale'] = [cval(sub(sc, 1)), cval(sub(sc, 2))]
        ls = [cval(p) for p in node.iter('parameter') if p.get('id') == '404']
        if ls:
            r['line_spacing'] = ls[0]
        al = [cval(p) for p in node.iter('parameter') if p.get('id') == '401']
        if al:
            r['align'] = al[0]
        out.append(r)
    return out


def main():
    db, outp = sys.argv[1:3]
    c = sqlite3.connect(db)
    typ = {pk: (t, ident) for pk, t, ident in c.execute('select Z_PK, ZTYPE, ZIDENTIFIER from ZCOLLECTION')}
    parent = {}
    for par, ch in c.execute('select Z_3PARENTCOLLECTIONS, Z_3CHILDCOLLECTIONS from Z_3CHILDCOLLECTIONS'):
        parent.setdefault(ch, par)
    md_cache = {}

    def md(pk):
        if pk not in md_cache:
            d = c.execute('select ZDICTIONARYDATA from ZCOLLECTIONMD where ZCOLLECTION=?', (pk,)).fetchone()
            try:
                md_cache[pk] = unarchive(d[0]) if d and d[0] else {}
            except Exception:
                md_cache[pk] = {}
        return md_cache[pk]

    def up(pk, want):
        seen = 0
        while pk in parent and seen < 30:
            pk = parent[pk]
            seen += 1
            if typ[pk][0] in want:
                return pk
        return None

    # クリップ側の変形（FFHeXForm3DEffect）: 生成物ごとに
    xform = {}
    for pk, (t, _) in typ.items():
        if t == 'FFHeXForm3DEffect':
            g = up(pk, ('FFAnchoredGeneratorComponent',))
            if g:
                xform[g] = {k: v for k, v in md(pk).items() if not isinstance(v, (bytes, dict, list))}
    res = []
    for pk, (t, _) in typ.items():
        if t != 'FFMotionEffectValue':
            continue
        m = md(pk)
        data = m.get('data')
        if not isinstance(data, bytes) or b'<text>' not in data:
            continue
        try:
            texts = parse_text(data.decode('utf8', 'replace'))
        except ET.ParseError:
            continue
        eff = up(pk, ('FFMotionEffect',))
        gen = up(pk, ('FFAnchoredGeneratorComponent',))
        em = md(eff) if eff else {}
        gm = md(gen) if gen else {}
        cr = pair(gm.get('clippedRange'))
        for tx in texts:
            tx.update({
                'gen': typ[gen][1] if gen else None,
                'template': em.get('displayName'),
                'effectID': (em.get('effectID') or '').split('/')[-1],
                'name': gm.get('displayName'),
                'lane': gm.get('anchoredLane'),
                'anchor': pair(gm.get('anchorPair')),
                'dur': cr[1] if len(cr) > 1 else None,
                'key': m.get('key'),
                'xform': xform.get(gen),
            })
            res.append(tx)
    json.dump(res, open(outp, 'w'), ensure_ascii=False, indent=0)
    print(len(res), 'テキスト')


if __name__ == '__main__':
    main()
