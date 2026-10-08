"""Flatten an FCPXML project timeline into absolute-time items.
Usage: python3 -I flatten.py in.fcpxml project_name out.json
Each item: abs start/end (sec), depth path, lane, tag, name, ref (effect/asset name), texts, styles,
params, transform, crop, filters, fades, blend, keyframes."""
import sys, json
from fractions import Fraction
import xml.etree.ElementTree as ET

src, proj_name, out = sys.argv[1:4]
root = ET.parse(src).getroot()
res = {e.get('id'): e for e in root.find('resources')}


def T(s, default='0s'):
    s = s or default
    s = s.rstrip('s')
    return Fraction(s) if '/' in s else Fraction(s or '0')


def params(e):
    out = {}
    for p in e.findall('param'):
        k = p.get('name')
        v = p.get('value')
        kfs = p.find('keyframeAnimation')
        if kfs is not None:
            v = {'keyframes': [(float(T(k.get('time'))), k.get('value')) for k in kfs.findall('keyframe')], 'value': v}
        sub = params(p)
        if sub:
            out[k] = {'value': v, 'sub': sub} if v is not None else sub
        else:
            out[k] = v
    return out


def kf_attrs(e):
    d = dict(e.attrib)
    pa = params(e)
    if pa:
        d['params'] = pa
    return d


def effect_name(ref):
    r = res.get(ref)
    if r is None:
        return None
    return {'id': ref, 'tag': r.tag, 'name': r.get('name'), 'uid': r.get('uid'),
            'src': (r.find('media-rep').get('src') if r.find('media-rep') is not None else None)}


items = []


def details(e):
    d = {}
    if e.tag == 'title':
        styles = {}
        for tsd in e.findall('text-style-def'):
            ts = tsd.find('text-style')
            styles[tsd.get('id')] = dict(ts.attrib) if ts is not None else {}
        texts = []
        for t in e.findall('text'):
            runs = []
            for ts in t.findall('text-style'):
                runs.append({'ref': ts.get('ref'), 'text': ts.text or ''})
            texts.append({'roll-up': t.get('roll-up'), 'runs': runs})
        d['texts'] = texts
        d['styles'] = styles
        d['params'] = params(e)
    for tag in ('adjust-transform', 'adjust-crop', 'adjust-blend', 'adjust-stabilization', 'adjust-volume', 'conform-rate', 'adjust-conform'):
        x = e.find(tag)
        if x is not None:
            v = kf_attrs(x)
            for sub in x:
                if sub.tag != 'param':
                    v.setdefault('children', []).append({'tag': sub.tag, **sub.attrib})
            d[tag] = v
    fl = []
    for f in e.findall('filter-video'):
        fl.append({'ref': effect_name(f.get('ref')), 'name': f.get('name'), 'enabled': f.get('enabled'), 'params': params(f)})
    if fl:
        d['filters'] = fl
    if e.tag in ('video', 'asset-clip', 'audio'):
        d['asset'] = effect_name(e.get('ref'))
        d['start_attr'] = e.get('start')
        a_ = res.get(e.get('ref'))
        if a_ is not None and a_.find('media-rep') is not None:
            import unicodedata, urllib.parse
            d['src'] = unicodedata.normalize('NFC', urllib.parse.unquote(a_.find('media-rep').get('src')))
    if e.tag in ('title', 'video') and res.get(e.get('ref')) is not None and res[e.get('ref')].tag == 'effect':
        d['effect'] = effect_name(e.get('ref'))
    if e.tag == 'mc-clip':
        d['mc'] = [dict(s.attrib) for s in e.findall('mc-source')]
    for tag in ('marker', 'chapter-marker'):
        for m in e.findall(tag):
            d.setdefault('markers', []).append({'tag': tag, 'start': m.get('start'), 'value': m.get('value')})
    return d


CLIP_TAGS = {'clip', 'asset-clip', 'video', 'audio', 'title', 'ref-clip', 'mc-clip', 'gap', 'sync-clip', 'spine'}


def walk(e, abs_start, local_start, path, lane, expand_refs=True, win=None):
    """e placed so that local time `local_start` corresponds to absolute `abs_start`."""
    off = T(e.get('offset'))
    st = T(e.get('start'))
    dur = T(e.get('duration'))
    a0 = abs_start + (off - local_start)
    v0, v1 = a0, a0 + dur
    if win is not None:
        v0, v1 = max(v0, win[0]), min(v1, win[1])
        if v1 <= v0:
            return
    rec = {'t0': float(v0), 't1': float(v1), 'src_t0': float(a0), 'dur': float(v1 - v0), 'tag': e.tag, 'name': e.get('name'),
           'lane': lane, 'path': path, 'enabled': e.get('enabled', '1')}
    rec.update(details(e))
    items.append(rec)
    child_abs = a0
    child_local = st
    if e.tag == 'clip':
        inner = [c for c in e if c.tag in ('video', 'asset-clip') and c.get('lane') is None]
        if inner:
            rec['asset'] = effect_name(inner[0].get('ref'))
    for ch in e:
        if e.tag == 'clip' and ch.get('lane') is None:
            continue
        if ch.tag in CLIP_TAGS:
            if ch.tag == 'spine':
                # embedded storyline: children's offsets are in parent local time
                for c2 in ch:
                    if c2.tag in CLIP_TAGS:
                        walk(c2, child_abs + (T(ch.get('offset')) - child_local), T(ch.get('start')) if ch.get('start') else Fraction(0),
                             path + [e.get('name')], ch.get('lane'), win=(v0, v1))
            else:
                walk(ch, child_abs, child_local, path + [e.get('name')], ch.get('lane'), win=(v0, v1) if path or win else None)
    if e.tag == 'ref-clip' and expand_refs:
        m = res.get(e.get('ref'))
        seq = m.find('sequence') if m is not None else None
        if seq is not None and m.get('name') != 'BGM':
            sp = seq.find('spine')
            for c2 in sp:
                if c2.tag in CLIP_TAGS:
                    # clip visible window [a0, a0+dur] ; inner local time st maps to a0
                    walk(c2, a0, st, path + [e.get('name')], 'in:' + (lane or '0'), win=(v0, v1))


import unicodedata
norm = lambda x: unicodedata.normalize('NFC', x or '')
proj = [p for p in root.iter('project') if norm(p.get('name')) == norm(proj_name)][0]
spine = proj.find('sequence/spine')
for e in spine:
    walk(e, Fraction(0), Fraction(0), [], None)

# clip items to their visible window of parents is not done; mark nested ref-expanded items
json.dump(items, open(out, 'w'), ensure_ascii=False, indent=0)
print(len(items))
