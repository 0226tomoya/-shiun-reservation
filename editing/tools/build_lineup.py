"""型（A19）に当てはめて、ラインナップ動画のテロップを作り直す。

サブコマンド:
  templates  正解の編集データから、役割ごとの型（テロップ要素）を抜き出す
      python3 build_lineup.py templates A19.fcpxml 本編 OUT_templates.fcpxml
  restyle    別の編集データの全テロップを、内容（文字・時刻・レーン）はそのままに、型の書式・位置で作り直す
      python3 build_lineup.py restyle TEMPLATES.fcpxml IN.fcpxml OUT.fcpxml [--project 本編]

位置のルール（README の型）:
  - 商品名ラベル: 同時に 2 本あれば上段/下段（変形 -9.111,5 / -9.111,-3.626、拡大 0.9）、1 本なら変形 -0.944,0
  - 中央商品名: 同時に 2 本あれば変形 ±44.444、価格ありは位置 -0.0825,43.05、なしは -0.775,8.575
  - セクションラベル: 単語ごとの x（Material 701.169 / Color 754.496 / Wash 760.77 / Silhouette 874.699 / Design・Detail 874.091）
  - 字幕: 1 行は位置 1,-483.734、2 行は 0,-440
  - ED 一覧の商品名: 横 4 列 x = 62.509 / 23.056 / -16.389 / -60.194、y = -35.556、拡大 0.6
"""
import copy
import itertools
import json
import os
import sys
import unicodedata
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role as classify, SECTION_WORDS  # noqa: E402

SECTION_X = {'Material': '701.169 -480.924', 'Color': '754.496 -480.924', 'Wash': '760.77 -480.924',
             'Silhouette': '874.699 -480.924', 'Design': '874.091 -480.924', 'Detail': '874.091 -480.924'}
ED_X = [62.5093, 23.0556, -16.3889, -60.1944]
ED_Y = -35.5556
SIZE_ORDER = ['XXS', 'XS', 'S', 'M', 'L', 'XL']
KEEP_LAYOUT = {'size_spec_value', 'size_spec_header', 'shoe_size_label', 'size_product_name'}


def T(s):
    s = (s or '0s').rstrip('s')
    return Fraction(s) if s else Fraction(0)


def norm(s):
    return unicodedata.normalize('NFC', s or '')


# ---------- タイトル要素を flatten 互換の dict にする（分類用） ----------
def title_info(el):
    styles = {}
    for tsd in el.findall('text-style-def'):
        ts = tsd.find('text-style')
        styles[tsd.get('id')] = dict(ts.attrib) if ts is not None else {}
    texts = []
    for t in el.findall('text'):
        texts.append({'runs': [{'ref': r.get('ref'), 'text': r.text or ''} for r in t.findall('text-style')]})
    params = {p.get('name'): p.get('value') for p in el.findall('param')}
    tr = el.find('adjust-transform')
    return {'tag': 'title', 'texts': texts, 'styles': styles, 'params': params,
            'adjust-transform': dict(tr.attrib) if tr is not None else None, 'lane': el.get('lane'), 'path': [],
            'effect': {'name': None}}


def slots(el):
    return [r for t in el.findall('text') for r in t.findall('text-style') if (r.text or '').strip()]


def has_price(el):
    return any('¥' in (r.text or '') for r in slots(el))


# ---------- テンプレート抽出 ----------
def project_titles(root, project):
    """プロジェクト直下のスパイン要素とその接続クリップのタイトルを (要素, 絶対時刻) で返す。"""
    out = []
    for e in project.find('sequence/spine'):
        off, st = T(e.get('offset')), T(e.get('start'))
        if e.tag == 'title':
            out.append((e, off))
        for ch in e:
            if ch.tag == 'title':
                out.append((ch, off + T(ch.get('offset')) - st))
    return out


def concurrent_groups(items):
    """同じ役割で同時刻に始まるもの（±0.05 秒）をまとめる。"""
    groups = []
    for it in sorted(items, key=lambda x: x[1]):
        if groups and abs(groups[-1][-1][1] - it[1]) < Fraction(1, 20):
            groups[-1].append(it)
        else:
            groups.append([it])
    return groups


def variant_key(r, el, group_size):
    if r == 'product_label':
        return f"{'price' if has_price(el) else 'plain'}"
    if r == 'product_center':
        return f"{'price' if has_price(el) else 'plain'}"
    if r == 'subtitle':
        return 'one'
    if r == 'size_spec_header':
        first = ''.join(x.text or '' for x in slots(el)).strip().split('\n')[0]
        return 'kitake' if first.startswith('着丈') else 'other'
    if r == 'section_label':
        return 'any'
    return 'any'


def cmd_templates(src, proj_name, out):
    root = ET.parse(src).getroot()
    res = {e.get('id'): e for e in root.find('resources')}
    project = [p for p in root.iter('project') if norm(p.get('name')) == norm(proj_name)][0]
    eff_name = {k: v.get('name') for k, v in res.items() if v.tag == 'effect'}
    buckets = {}
    for el, t in project_titles(root, project):
        if el.get('enabled') == '0':
            continue
        info = title_info(el)
        info['effect']['name'] = eff_name.get(el.get('ref'))
        r = classify(info)
        if r in (None, 'empty', 'other', 'adjustment_main', 'adjustment_other'):
            continue
        key = (r, variant_key(r, el, 1))
        buckets.setdefault(key, []).append(el)
    # 各バケットで最も多い書式（フォント・サイズ・位置・変形）を代表にする
    chosen = {}
    for key, els in buckets.items():
        def sig(e):
            i = title_info(e)
            st = [i['styles'][r['ref']] for t in i['texts'] for r in t['runs'] if r['text'].strip()]
            return (json.dumps(st[:1], sort_keys=True), i['params'].get('位置'), json.dumps(i['adjust-transform'], sort_keys=True))
        best = max(itertools.groupby(sorted(els, key=sig), key=sig), key=lambda g: len(list(copy.copy(g[1]))))
        rep = [e for e in els if sig(e) == best[0]][0]
        chosen[key] = rep
    # 出力
    new_root = ET.Element('fcpxml', version=root.get('version'))
    nres = ET.SubElement(new_root, 'resources')
    used = set()
    for el in chosen.values():
        used.add(el.get('ref'))
    fmt = project.find('sequence').get('format')
    used.add(fmt)
    for e in root.find('resources'):
        if e.get('id') in used:
            nres.append(copy.deepcopy(e))
    lib = ET.SubElement(new_root, 'library')
    ev = ET.SubElement(lib, 'event', name='shiun 型')
    pr = ET.SubElement(ev, 'project', name='型_テロップ')
    total = Fraction(10) * len(chosen)
    sq = ET.SubElement(pr, 'sequence', format=fmt, duration=f'{total}s', tcStart='0s', tcFormat='NDF', audioLayout='stereo', audioRate='48k')
    sp = ET.SubElement(sq, 'spine')
    gap = ET.SubElement(sp, 'gap', name='型', offset='0s', start='0s', duration=f'{total.numerator}/{total.denominator}s')
    for k, ((r, v), el) in enumerate(sorted(chosen.items())):
        e = copy.deepcopy(el)
        e.set('lane', '1')
        e.set('offset', f'{k * 10}s')
        e.set('duration', '9s')
        e.set('name', f'{r}:{v}')
        for ch in list(e):
            if ch.tag in ('marker', 'chapter-marker'):
                e.remove(ch)
        gap.append(e)
    ET.indent(new_root)
    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(new_root, encoding='utf-8'))
    for (r, v), el in sorted(chosen.items()):
        print(f'{r}:{v}  <- {el.get("name")[:50]}')


# ---------- 型の適用 ----------
class Templates:
    def __init__(self, path):
        root = ET.parse(path).getroot()
        self.res = {e.get('id'): e for e in root.find('resources')}
        self.by = {}
        for el in root.iter('title'):
            nm = el.get('name') or ''
            if ':' in nm:
                r, v = nm.split(':', 1)
                self.by[(r, v)] = el

    def get(self, r, v):
        if (r, v) == ('size_spec_header', 'other') and (r, v) not in self.by:
            # 着丈以外の項目名（ウエスト等）は数値と同じ Basic Title / Hiragino W3 20 / olive
            r, v = 'size_spec_value', 'any'
        for key in ((r, v), (r, 'plain'), (r, 'any')):
            if key in self.by:
                return self.by[key]
        return next((e for (rr, _), e in self.by.items() if rr == r), None)


_uid = itertools.count(1)


def apply_template(tpl_el, actual_el, tpl_res, doc_res, doc_resources_el, r, ctx):
    """actual_el を、型の書式・位置にした要素で置き換える（文字・時刻・レーンは actual のまま）。"""
    new = copy.deepcopy(tpl_el)
    for k in ('offset', 'duration', 'lane', 'enabled'):
        if actual_el.get(k) is not None:
            new.set(k, actual_el.get(k))
        elif k in new.attrib and k != 'enabled':
            del new.attrib[k]
    new.set('name', actual_el.get('name') or new.get('name'))
    # エフェクト参照を文書側の ID に合わせる
    tdef = tpl_res[tpl_el.get('ref')]
    match = next((e for e in doc_res.values() if e.tag == 'effect' and e.get('uid') == tdef.get('uid')), None)
    if match is None:
        nid = f'rsim{next(_uid)}'
        d = copy.deepcopy(tdef)
        d.set('id', nid)
        doc_resources_el.append(d)
        doc_res[nid] = d
        match = d
    new.set('ref', match.get('id'))
    # text-style-def の ID を一意にする
    pref = f'sim{next(_uid)}_'
    for tsd in new.findall('text-style-def'):
        tsd.set('id', pref + tsd.get('id'))
    for ts in new.iter('text-style'):
        if ts.get('ref'):
            ts.set('ref', pref + ts.get('ref'))
    # 文字を差し込む（空白でないランに順番に）
    src = [x.text for x in slots(actual_el)]
    dst = slots(new)
    for k, run in enumerate(dst):
        run.text = src[k] if k < len(src) else ''
    if len(src) > len(dst) and dst:
        dst[-1].text = (dst[-1].text or '') + ''.join(src[len(dst):])
    # 型に改行だけのランがある場合、差し込んだ行末の改行と重なって空行にならないようにする
    runs = list(new.iter('text-style'))
    for a, b in zip(runs, runs[1:]):
        if (a.text or '').endswith('\n') and (b.text or '').startswith('\n'):
            a.text = a.text[:-1]
    # 子要素（マーカー・キーワード）は actual のものを残す
    for ch in list(new):
        if ch.tag in ('marker', 'chapter-marker', 'keyword'):
            new.remove(ch)
    for ch in actual_el:
        if ch.tag in ('marker', 'chapter-marker', 'keyword'):
            new.append(copy.deepcopy(ch))
    if r == 'subtitle' and SUBTITLE_SIZE:
        for ts in new.iter('text-style'):
            if ts.get('fontSize'):
                ts.set('fontSize', str(SUBTITLE_SIZE))
    # 位置のルール
    if r in KEEP_LAYOUT:
        # 表の行数・列数で位置が決まるものは、元データの位置を使う（書式だけ型を当てる）
        for name in ('位置',):
            v = next((p.get('value') for p in actual_el.findall('param') if p.get('name') == name), None)
            if v is not None:
                set_param(new, name, v)
        atr = actual_el.find('adjust-transform')
        set_transform(new, atr.get('position') if atr is not None else None, atr.get('scale') if atr is not None else None)
    else:
        set_rule_position(new, r, ctx)
    return new


def set_param(el, name, value):
    p = next((p for p in el.findall('param') if p.get('name') == name), None)
    if p is not None:
        p.set('value', value)


def set_transform(el, position=None, scale=None):
    tr = el.find('adjust-transform')
    if position is None and scale is None:
        if tr is not None:
            el.remove(tr)
        return
    if tr is None:
        # adjust-transform は text/text-style-def より後、filter より前に置く
        idx = max([k for k, ch in enumerate(el) if ch.tag in ('param', 'text', 'text-style-def')] + [-1]) + 1
        tr = ET.Element('adjust-transform')
        el.insert(idx, tr)
    for k in list(tr.attrib):
        del tr.attrib[k]
    if position:
        tr.set('position', position)
    if scale:
        tr.set('scale', scale)


def set_rule_position(el, r, ctx):
    n, k = ctx.get('group_size', 1), ctx.get('index', 0)
    if r == 'product_label':
        if n >= 2:
            set_param(el, '位置', '-849.551 443.956')
            set_transform(el, '-9.11111 5' if k == 0 else '-9.11111 -3.6263', '0.9 0.9')
        else:
            set_param(el, '位置', '-849.551 443.956')
            set_transform(el, '-0.944444 0')
    elif r == 'product_center':
        price = has_price(el)
        if n >= 2:
            # 2 商品の同時紹介: 左右の写真それぞれの中央
            set_param(el, '位置', '-0.0825 43.0501' if price else '-0.0825 1.57505')
            set_transform(el, ('-44.4444 0' if k == 0 else '44.4444 0'))
        else:
            # 単品: 価格なし（紹介イン）は 0,8.6、価格あり（比較前・区間末）は 0,43.1
            set_param(el, '位置', '-0.0825 43.0501' if price else '-0.775 8.57505')
            set_transform(el, None)
    elif r == 'section_label':
        word = ''.join(x.text or '' for x in slots(el)).strip()
        set_param(el, '位置', SECTION_X.get(word, '874.091 -480.924'))
        set_transform(el, '-1.34295 84.7222')
        if not SECTION_X.get(word, '874').startswith('874'):
            # A19 の Material / Color / Wash は中央揃えで x を詰めて、右端を他のラベルに揃えている
            for ts in el.iter('text-style'):
                ts.attrib.pop('alignment', None)
    elif r == 'subtitle':
        lines = ''.join(x.text or '' for x in slots(el)).count('\n') + 1
        set_param(el, '位置', '1 -483.734' if lines == 1 else '0 -440')
    elif r == 'size_letter':
        # 小さいサイズを左、大きいサイズを右
        set_param(el, '位置', '-292.796 404.571' if k == 0 else '312.47 406.474')
        set_transform(el, '-2.26635 2.40741')
    elif r == 'ed_product_name':
        set_transform(el, f'{ED_X[k % 4]} {ED_Y}', '0.6 0.6')


SUBTITLE_SIZE = None  # --subtitle-size で上書き（標準は型どおり 32。旧設定の動画と比べるときだけ 35）


def cmd_restyle(tpl_path, src, out, proj_name='本編'):
    tpl = Templates(tpl_path)
    tree = ET.parse(src)
    root = tree.getroot()
    resources_el = root.find('resources')
    doc_res = {e.get('id'): e for e in resources_el}
    eff_name = {k: v.get('name') for k, v in doc_res.items() if v.tag == 'effect'}
    project = [p for p in root.iter('project') if norm(p.get('name')) == norm(proj_name)][0]
    titles = []
    for el, t in project_titles(root, project):
        info = title_info(el)
        info['effect']['name'] = eff_name.get(el.get('ref'))
        r = classify(info)
        if r in (None, 'empty', 'other', 'adjustment_main', 'adjustment_other'):
            continue
        titles.append((el, t, r))
    # 同時刻の同じ役割をまとめて、上段/下段・左右・ED の列を決める
    parent = {c: p for p in root.iter() for c in p}
    stats = {}
    by_role = {}
    for el, t, r in titles:
        by_role.setdefault(r, []).append((el, t))
    for r, items in by_role.items():
        for g in concurrent_groups(items):
            g = sorted(g, key=lambda x: -int(x[0].get('lane') or 0)) if r == 'product_label' else g
            if r == 'ed_product_name':
                g = sorted(g, key=lambda x: int(x[0].get('lane') or 0))
            if r == 'size_letter':
                g = sorted(g, key=lambda x: SIZE_ORDER.index(''.join(y.text or '' for y in slots(x[0])).strip())
                           if ''.join(y.text or '' for y in slots(x[0])).strip() in SIZE_ORDER else 0)
            for k, (el, t) in enumerate(g):
                v = variant_key(r, el, len(g))
                tp = tpl.get(r, v)
                if tp is None:
                    stats[r] = stats.get(r, 0)
                    continue
                new = apply_template(tp, el, tpl.res, doc_res, resources_el, r, {'group_size': len(g), 'index': k})
                p = parent[el]
                idx = list(p).index(el)
                p.remove(el)
                p.insert(idx, new)
                stats[r] = stats.get(r, 0) + 1
    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))
    print('restyled', sum(stats.values()), stats)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'templates':
        cmd_templates(*sys.argv[2:5])
    elif cmd == 'restyle':
        args = sys.argv[2:]
        proj = '本編'
        if '--subtitle-size' in args:
            i = args.index('--subtitle-size')
            SUBTITLE_SIZE = args[i + 1]
            args = args[:i] + args[i + 2:]
        if '--project' in args:
            i = args.index('--project')
            proj = args[i + 1]
            args = args[:i] + args[i + 2:]
        cmd_restyle(args[0], args[1], args[2], proj)
    else:
        raise SystemExit(__doc__)
