"""完成版の FCPXML（長編）を、タイムラインの時刻つきの部品の一覧にする。テロップは書式（フォント・大きさ・色・縁・影・位置）まで取る。

    python3 longform_analyze.py FINAL.fcpxml OUT.json

OUT.json: {"duration", "fd", "spine": [{start, end, name, kind, src_in}],
           "titles": [{start, end, lane, effect, name, text, runs: [[文字, {書式}]], params: {名前: 値}, transform}],
           "clips": [{start, end, lane, kind, name, ref_name, src_in}],   # 本線以外の映像・音（インサート・効果音・BGM）
           "markers": [{at, value}]}
時刻は、つないだ要素は親の時刻（offset − 親の start ＋ 親のタイムライン上の頭）で直す。複合クリップ（ref-clip）の中は開かない（名前で数える）。
"""
import json
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fr(int(a), int(b))
    return Fr(s)


def main():
    src, out = sys.argv[1:3]
    root = ET.parse(src).getroot()
    res = {e.get('id'): e for e in root.find('resources')}
    # 複数のプロジェクトがあるときは「本編」、無ければ一番長いもの
    projs = root.findall('.//project')
    pj = next((p for p in projs if p.get('name') == '本編'), None)
    if pj is None:
        pj = max(projs, key=lambda p: T(p.find('sequence').get('duration')))
    seq = pj.find('sequence')
    fd = T(res[seq.get('format')].get('frameDuration'))
    spine = seq.find('spine')
    R = {'duration': float(T(seq.get('duration'))), 'fd': float(fd), 'spine': [], 'titles': [], 'clips': [], 'markers': []}

    def styles(t):
        defs = {}
        for d in t.iter('text-style-def'):
            s = d.find('text-style')
            if s is not None:
                defs[d.get('id')] = dict(s.attrib)
        runs = []
        tx = t.find('text')
        if tx is not None:
            for r in tx.iter('text-style'):
                runs.append([r.text or '', defs.get(r.get('ref'), {})])
        return runs

    def walk(el, base_tl, base_start, lane0):
        """el の子（つないだ要素）を、親のタイムラインの頭 base_tl・親の start base_start で直して集める"""
        for c in el:
            tag = c.tag
            if tag in ('title', 'video', 'audio', 'asset-clip', 'clip', 'ref-clip', 'mc-clip', 'sync-clip', 'gap'):
                if c.get('lane') is None and el is not spine:
                    continue
                st = base_tl + T(c.get('offset')) - base_start
                du = T(c.get('duration'))
                lane = int(c.get('lane') or 0)
                if tag == 'title':
                    eff = res.get(c.get('ref'))
                    R['titles'].append({'start': float(st), 'end': float(st + du), 'lane': lane,
                                        'effect': eff.get('name') if eff is not None else None,
                                        'uid': eff.get('uid') if eff is not None else None,
                                        'name': c.get('name'), 'text': ''.join(x[0] for x in styles(c)), 'runs': styles(c),
                                        'params': {p.get('name') + '#' + (p.get('key') or '').split('/')[-1]: p.get('value') for p in c.findall('param')},
                                        'transform': dict(c.find('adjust-transform').attrib) if c.find('adjust-transform') is not None else None})
                else:
                    ref = res.get(c.get('ref'))
                    R['clips'].append({'start': float(st), 'end': float(st + du), 'lane': lane, 'kind': tag, 'name': c.get('name'),
                                       'ref_name': ref.get('name') if ref is not None else None, 'src_in': float(T(c.get('start')))})
                # つないだ要素の中（さらにつないだ要素）
                walk(c, st, T(c.get('start')), lane)
            elif tag == 'marker' or tag == 'chapter-marker':
                R['markers'].append({'at': float(base_tl + T(c.get('start')) - base_start), 'value': c.get('value'), 'kind': tag})
            elif tag == 'spine' and el is not spine:
                # つないだストーリーライン
                walk(c, base_tl + T(c.get('offset')) - base_start, T(c.get('start') or '0s'), lane0)

    for c in spine:
        st = T(c.get('offset'))
        du = T(c.get('duration'))
        R['spine'].append({'start': float(st), 'end': float(st + du), 'name': c.get('name'), 'kind': c.tag, 'src_in': float(T(c.get('start')))})
        if c.tag == 'title':
            eff = res.get(c.get('ref'))
            R['titles'].append({'start': float(st), 'end': float(st + du), 'lane': 0, 'effect': eff.get('name') if eff is not None else None,
                                'uid': eff.get('uid') if eff is not None else None, 'name': c.get('name'), 'text': ''.join(x[0] for x in styles(c)),
                                'runs': styles(c), 'params': {}, 'transform': None})
        walk(c, st, T(c.get('start')), 0)
    json.dump(R, open(out, 'w'), ensure_ascii=False, indent=0)
    print(f"{src.split('/')[-2]}: 長さ {R['duration']:.1f} 秒・本線 {len(R['spine'])}・テロップ {len(R['titles'])}・本線以外 {len(R['clips'])}・マーカー {len(R['markers'])}")


if __name__ == '__main__':
    main()
