"""FCPXML の本編を、タイムライン上の「もの」の一覧に平らにする（2 つの XML を比べるため）。
python3 fcpxml_flat.py Info.fcpxml [out.json]
1 行 = {kind, lane, start, end, name, ref_name, src_in, text, effects, volume, transform, crop, markers, parent}
start/end はタイムラインの秒。lane は親からの段（本線=0）。text は title の文字。effects は filter-video/filter-audio の名前。
"""
import sys, json, xml.etree.ElementTree as ET
from fractions import Fraction as Fr


def t(s):
    if not s:
        return Fr(0)
    s = s.rstrip('s')
    if '/' in s:
        a, b = s.split('/'); return Fr(int(a), int(b))
    return Fr(s)


ITEM = {'asset-clip', 'mc-clip', 'clip', 'title', 'video', 'ref-clip', 'gap', 'transition', 'sync-clip', 'audio'}


def flatten(path):
    root = ET.parse(path).getroot()
    res = {e.get('id'): e for e in root.find('resources')}
    rname = lambda i: (res[i].get('name') or res[i].tag) if i in res else None
    seq = root.find('.//project/sequence')
    out = []

    def walk(e, to_tl, lane_abs, parent):
        # e のローカル時刻 → タイムライン時刻 は to_tl(x)
        for c in e:
            if c.tag == 'spine':
                off = t(c.get('offset'))
                walk(c, (lambda f, o: (lambda x: f(o + x)))(to_tl, off), lane_abs + int(c.get('lane', 0)), parent)
                continue
            if c.tag not in ITEM:
                continue
            off, st, du = t(c.get('offset')), t(c.get('start')), t(c.get('duration'))
            s_tl = to_tl(off)
            lane = lane_abs + int(c.get('lane', 0))
            item = {'kind': c.tag, 'lane': lane, 'start': round(float(s_tl), 3), 'end': round(float(s_tl + du), 3),
                    'name': c.get('name'), 'ref_name': rname(c.get('ref')), 'src_in': round(float(st), 3), 'parent': parent}
            if c.tag == 'title':
                item['text'] = ''.join((x.text or '') for x in c.iter('text-style'))
                ps = {p.get('name'): p.get('value') for p in c.findall('param')}
                item['params'] = {k: v for k, v in ps.items() if k in ('位置', 'Position', 'Alignment', 'Size', 'Opacity', 'Layout Method')}
                tsd = c.find('.//text-style-def/text-style')
                if tsd is not None:
                    item['style'] = {k: tsd.get(k) for k in ('font', 'fontSize', 'fontFace', 'fontColor', 'strokeColor', 'strokeWidth', 'shadowColor', 'alignment', 'lineSpacing', 'kerning', 'bold')}
            item['effects'] = [rname(f.get('ref')) or f.get('name') for f in c.findall('filter-video')] + \
                              ['A:' + (rname(f.get('ref')) or f.get('name') or '') for f in c.findall('filter-audio')]
            av = c.find('adjust-volume')
            if av is not None:
                item['volume'] = av.get('amount')
            tr = c.find('adjust-transform')
            if tr is not None:
                item['transform'] = {k: tr.get(k) for k in ('position', 'scale', 'rotation', 'anchor') if tr.get(k)}
            cr = c.find('adjust-crop')
            if cr is not None:
                item['crop'] = cr.get('mode')
            ac = c.find('audio-channel-source')
            if c.get('audioRole') or c.get('role'):
                item['role'] = c.get('audioRole') or c.get('role')
            mk = [(x.tag, x.get('value')) for x in c if x.tag in ('marker', 'chapter-marker')]
            if mk:
                item['markers'] = [(k, v, round(float(to_tl(off) + t(x.get('start')) - st), 3)) for (k, v), x in zip(mk, [x for x in c if x.tag in ('marker', 'chapter-marker')])]
            if c.tag == 'mc-clip':
                item['angles'] = [(a.get('angleID', '')[-6:], a.get('srcEnable')) for a in c.findall('mc-source')]
            out.append(item)
            # 子（つながったクリップ）: ローカル時刻 x → タイムライン s_tl + (x - st)
            walk(c, (lambda base, s0: (lambda x: base + (x - s0)))(s_tl, st), lane, len(out) - 1)

    walk(seq, lambda x: x, 0, None)
    return out


if __name__ == '__main__':
    items = flatten(sys.argv[1])
    if len(sys.argv) > 2:
        json.dump(items, open(sys.argv[2], 'w'), ensure_ascii=False, indent=0)
    import collections
    print(len(items), collections.Counter((i['kind'], i['lane']) for i in items).most_common(25))
