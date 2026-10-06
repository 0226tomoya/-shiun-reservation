"""粗編集（トークのジャンプカット＋チャプターマーカー）に、ラインナップの型を組み付ける。

    python3 assemble_lineup.py ROUGH.fcpxml PLAN.json OUT.fcpxml

PLAN.json の例は editing/plans/A24_plan.json。やること:
  1. メインカメラの各カットに lane 1 の調整レイヤー（A19 のカラー調整＋区間ごとの構図プリセット）を付ける
  2. OP: 名前カード（0 秒〜）、左上のコレクション名（トーク中）
  3. 各商品区間: 頭にアイキャッチ（スパインに挿入）、中央商品名（紹介イン）、左上の商品名ラベル（カットごと）
  4. BGM（A19 と同じ複合クリップ、-17dB ループ）、ED の最後にエンディング動画
素材（アイキャッチ、BGM、エンディング、カウントダウン）とカラー調整は A19 の編集データからそのままコピーする。
"""
import copy
import json
import os
import sys
import unicodedata
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_lineup import Templates, apply_template, set_param, set_transform  # noqa: E402

FRAMING = {  # A19（4K 単カメ・立ち）の構図プリセット
    'op_tight': ('-7.46296 -29.4719', '1.92 1.92'),
    'tight': ('17.037 -24.7161', '1.82 1.82'),
    'mid': ('9.44444 1.85185', '1.21 1.21'),
    'wide': ('-0.0555556 -2.53704', '1.05 1.05'),
}


def T(s):
    s = (s or '0s').rstrip('s')
    return Fraction(s) if s else Fraction(0)


def S(fr):
    fr = Fraction(fr).limit_denominator(240000)
    return f'{fr.numerator}s' if fr.denominator == 1 else f'{fr.numerator}/{fr.denominator}s'


def norm(s):
    return unicodedata.normalize('NFC', s or '')


class Donor:
    """A19 など、部品を借りてくる編集データ。リソース ID は接頭辞を付けて取り込む。"""

    def __init__(self, path, prefix, doc_resources):
        self.root = ET.parse(path).getroot()
        self.res = {e.get('id'): e for e in self.root.find('resources')}
        self.prefix = prefix
        self.doc_resources = doc_resources
        self.imported = {}

    def rid(self, old):
        return self.prefix + old

    def import_resource(self, rid):
        if rid in self.imported or rid not in self.res:
            return
        self.imported[rid] = True
        el = copy.deepcopy(self.res[rid])
        self._remap(el)
        for x in self.res[rid].iter():
            for k in ('ref', 'format'):
                if x.get(k) and x.get(k) in self.res:
                    self.import_resource(x.get(k))
        self.doc_resources.append(el)

    def _remap(self, el):
        for x in el.iter():
            for k in ('id', 'ref', 'format'):
                if x.get(k) and x.get(k) in self.res:
                    x.set(k, self.rid(x.get(k)))

    def element(self, el):
        """部品要素をコピーして、参照するリソースを取り込む。"""
        e = copy.deepcopy(el)
        for x in el.iter():
            for k in ('ref', 'format'):
                if x.get(k) and x.get(k) in self.res:
                    self.import_resource(x.get(k))
        self._remap(e)
        return e

    def find_resource(self, tag, name):
        return next((e for e in self.res.values() if e.tag == tag and norm(e.get('name')) == norm(name)), None)

    def find_in_project(self, project, pred):
        p = [p for p in self.root.iter('project') if norm(p.get('name')) == norm(project)][0]
        for e in p.iter():
            if pred(e):
                return e
        return None


def main():
    rough, plan_path, out = sys.argv[1:4]
    plan = json.load(open(plan_path, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(plan_path))
    tree = ET.parse(rough)
    root = tree.getroot()
    resources = root.find('resources')
    doc_res = {e.get('id'): e for e in resources}
    project = [p for p in root.iter('project') if norm(p.get('name')) == norm(plan.get('project', '本編'))][0]
    seq = project.find('sequence')
    spine = seq.find('spine')

    donor = Donor(os.path.join(base, plan['donor']['fcpxml']), 'a19_', resources)
    tpl = Templates(os.path.join(base, plan['templates']))

    # ---- 部品 ----
    grade_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'title' and e.get('lane') == '1'
                                      and e.get('name') == 'Adjustment Layer' and e.find('filter-video') is not None)
    eyecatch_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'ref-clip' and norm(e.get('name')) == 'アイキャッチ')
    ending_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'asset-clip' and norm(e.get('name')) == 'エンディング')
    countdown_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'asset-clip' and e.get('name') == '7')
    bgm_src = donor.find_in_project(plan['donor']['project'], lambda e: e.tag == 'ref-clip' and norm(e.get('name')) == 'BGM')

    # ---- チャプターから区間を作る ----
    items = list(spine)
    pos = Fraction(0)
    chapters = []
    for e in items:
        for m in e.findall('chapter-marker'):
            chapters.append((T(e.get('offset')) + T(m.get('start')) - T(e.get('start')), m.get('value')))
    chapters = sorted(set(chapters))
    seen, ch = set(), []
    for t, v in chapters:
        if v not in seen:
            seen.add(v)
            ch.append((t, v))
    chapters = ch
    total = T(seq.get('duration'))
    bounds = [(Fraction(0), 'OP')] + chapters + [(total, 'END')]
    sections = []
    for (t0, name), (t1, _) in zip(bounds, bounds[1:]):
        sections.append({'t0': t0, 't1': t1, 'chapter': name})
    prod_plan = {p['chapter']: p for p in plan['products']}
    k = 0
    for s in sections:
        if s['chapter'] in prod_plan:
            s['product'] = prod_plan[s['chapter']]
            s['framing'] = plan['framing']['products'][k % len(plan['framing']['products'])]
            k += 1
        elif s['chapter'] == 'OP':
            s['framing'] = plan['framing']['op']
        else:
            s['framing'] = plan['framing'].get('ed', 'mid')

    def section_at(t):
        return next(s for s in sections if s['t0'] <= t < s['t1'] or s is sections[-1])

    # ---- テロップ生成のヘルパー ----
    def make_title(role, variant, texts, lane, offset, duration, ctx=None, start=None):
        tp = tpl.get(role, variant)
        fake = ET.Element('title', lane=str(lane), offset=S(offset), duration=S(duration))
        t = ET.SubElement(fake, 'text')
        for n, line in enumerate(texts):
            r = ET.SubElement(t, 'text-style')
            r.text = line + ('\n' if n < len(texts) - 1 and not line.endswith('\n') else '')
        new = apply_template(tp, fake, tpl.res, doc_res, resources, role, ctx or {})
        if start is not None:
            new.set('start', S(start))
        return new

    # ---- 1. メインカメラの各カット ----
    log = {'adjustment': 0, 'product_label': 0, 'collection_label': 0}
    for e in items:
        if e.tag != 'mc-clip':
            continue
        off, st, du = T(e.get('offset')), T(e.get('start')), T(e.get('duration'))
        sec = section_at(off)
        g = donor.element(grade_src)
        g.set('lane', '1')
        g.set('offset', S(st))
        g.set('duration', S(du))
        p, sc = FRAMING[sec['framing']]
        set_transform(g, p, sc)
        e.append(g)
        log['adjustment'] += 1
        # OP: コレクション名（名前カードの後〜OP の終わり）
        if sec['chapter'] == 'OP' and off >= Fraction(47, 10):
            e.append(make_title('collection_label', 'any', [plan['collection'], plan['release_line']], 2, st, du))
            log['collection_label'] += 1
        # 商品区間: 紹介インの後は左上に商品名ラベル
        if 'product' in sec and off >= sec['t0'] + Fraction(str(plan.get('label_delay', 6))):
            pr = sec['product']
            e.append(make_title('product_label', 'plain', [pr['name'], f"Color : {pr['color']} | Size : {pr['sizes']}"], 2, st, du))
            log['product_label'] += 1

    # ---- 2. OP の名前カード ----
    first = next(e for e in items if e.tag == 'mc-clip')
    first.append(make_title('name_card', 'any', ['WAMU', '/Fashion YouTuber\n/shiun Director'], 2, T(first.get('start')), Fraction(47, 10)))

    # ---- 3. 中央商品名（各商品区間の頭 4.6 秒）----
    for s in sections:
        if 'product' not in s:
            continue
        host = next(e for e in items if e.tag == 'mc-clip' and T(e.get('offset')) >= s['t0'])
        pr = s['product']
        host.append(make_title('product_center', 'plain', [pr['name'], f"Color : {pr['color']} | Size : {pr['sizes']}"], 3,
                               T(host.get('start')) + (s['t0'] - T(host.get('offset'))) if T(host.get('offset')) < s['t0'] else T(host.get('start')),
                               Fraction(46, 10)))

    # ---- 4. BGM（先頭のカットにつなぐ）----
    if bgm_src is not None:
        b = donor.element(bgm_src)
        b.set('lane', '-1')
        b.set('offset', first.get('start') or '0s')
        b.set('duration', S(total))
        for kf in list(b):
            if kf.tag == 'adjust-volume':
                b.remove(kf)
        first.append(b)

    # ---- 5. スパインへの挿入（アイキャッチ・カウントダウン・エンディング）----
    new_items = []
    inserts = []
    for s in sections:
        if 'product' in s and eyecatch_src is not None:
            inserts.append((s['t0'], 'eyecatch'))
    if plan.get('countdown') and countdown_src is not None:
        first_prod = next(s for s in sections if 'product' in s)
        inserts.append((first_prod['t0'] - Fraction(1, 1000), 'countdown'))
    inserts.sort()
    ins_i = 0
    for e in items:
        off = T(e.get('offset'))
        while ins_i < len(inserts) and inserts[ins_i][0] <= off:
            kind = inserts[ins_i][1]
            src = eyecatch_src if kind == 'eyecatch' else countdown_src
            x = donor.element(src)
            for ch in list(x):
                if ch.get('lane') is not None:
                    x.remove(ch)
            new_items.append(x)
            ins_i += 1
        new_items.append(e)
    if ending_src is not None:
        x = donor.element(ending_src)
        for ch in list(x):
            if ch.get('lane') is not None:
                x.remove(ch)
        new_items.append(x)
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
    print(f"sections: {[(s['chapter'], round(float(s['t0']), 1)) for s in sections]}")
    print(f'log: {log}  inserts: {len(inserts)}  duration: {float(cur):.1f}s -> {out}')


if __name__ == '__main__':
    main()
