"""長編（ひとりで話す購入品・レビュー回）の部品の一覧（longform_events.py と同じ形の JSON）から、FCP で読み込める FCPXML を作る。

    python3 longform_build.py BASE.fcpxml EVENTS.json TEMPLATES.json OUT.fcpxml [--eyecatch-src file:///…/わむうアイキャッチ.mp4]

- BASE: カット済みの XML（本線だけ。完成版と同じ 1 本のプロジェクト）
- EVENTS: {"events": [{"kind", "start", "end", "text"}]}（時刻はアイキャッチを入れる前のタイムラインの秒）
- TEMPLATES: longform_templates.py の出力（完成版のテロップの型）。書体・大きさ・位置・字間・フェードは型のまま、文と時刻だけ差し替える
- アイキャッチ（eyecatch）は本線に 1.4 秒の「わむうアイキャッチ」を差し込む（talk_overlay.py と同じ）。見出し・WAMU はアイキャッチの上に出さない
- 影は apply_telop_shadow.py と同じ（縁取り 0.25 → ぼかした影、見出し → ドロップシャドウのフィルタ）
- 型の無い部品（効果音・インサート・BGM・商品番号の箱・冒頭プロフィール・エンディング）は、その時刻にマーカー「要素材: …」を打つ
"""
import copy
import json
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from talk_overlay import Overlay, T, ts, new_id  # noqa: E402
import apply_telop_shadow  # noqa: E402

LANES = {'heading': 3, 'wamu': 2, 'topic': 5, 'fact': 4, 'opinion': 4, 'vertical': 5, 'price': 6, 'tsukkomi': 6, 'color': 6,
         'item_card': 5, 'coord': 5, 'shiun_card': 6, 'title_call': 4, 'channel': 4, 'closing': 4}
NO_EYE = {'heading', 'wamu', 'topic'}  # アイキャッチの上には出さない


def lines_of(runs):
    """型の text-style の並び [(文字, style id)] を、行ごとの style に分ける"""
    rows = [[]]
    nl = None
    for s, sid in runs:
        parts = s.split('\n')
        for j, p in enumerate(parts):
            if j > 0:
                nl = nl or sid
                rows.append([])
            if p.strip() or p:
                rows[-1].append((p, sid))
    return rows, nl


def fill(title, text, uniq):
    """title の文を text に差し替える（行ごとに型の同じ行の style。行末 1 字だけ別 style の型＝タイプライターはそれも再現）"""
    tx = title.find('text')
    runs = [(r.text or '', r.get('ref')) for r in tx.findall('text-style')]
    rows, nl = lines_of(runs)
    rows = [r for r in rows if any(p.strip() for p, _ in r)] or [[('', runs[0][1])]]
    new = []
    for i, line in enumerate(text.split('\n')):
        tr = rows[min(i, len(rows) - 1)]
        if i > 0:
            new.append(('\n', nl or tr[0][1]))
        first, last = tr[0][1], tr[-1][1]
        tail1 = len(tr) >= 2 and len(tr[-1][0].strip()) == 1 and last != first
        if tail1 and len(line) > 1:
            new += [(line[:-1], first), (line[-1], last)]
        else:
            new.append((line, first))
    for r in list(tx):
        tx.remove(r)
    ren = {}
    for s, sid in new:
        if sid not in ren:
            ren[sid] = f'lf{uniq()}'
        r = ET.SubElement(tx, 'text-style', {'ref': ren[sid]})
        r.text = s
    for d in list(title.findall('text-style-def')):
        if d.get('id') in ren:
            d.set('id', ren[d.get('id')])
        else:
            title.remove(d)


def main():
    base, evp, tpp, out = sys.argv[1:5]
    eye_src = sys.argv[sys.argv.index('--eyecatch-src') + 1] if '--eyecatch-src' in sys.argv else 'file:///Users/modantaimusu/Downloads/わむうアイキャッチ.mp4'
    head = open(base, encoding='utf-8').read(400)
    tree = ET.parse(base)
    o = Overlay(tree.getroot())
    ev = json.load(open(evp))['events']
    tpl = json.load(open(tpp))
    # 型の effect を resources へ（uid が同じものがあれば使う）
    eff_map = {}
    for k, t in tpl.items():
        for rid, x in t['effects'].items():
            e = ET.fromstring(x)
            have = next((r for r in o.res.findall('effect') if r.get('uid') == e.get('uid')), None)
            if have is None:
                e.set('id', new_id(o.res, 'r'))
                o.res.append(e)
                have = e
            eff_map[(k, rid)] = have.get('id')
    o.insert_eyecatch([e['start'] for e in ev if e['kind'] == 'eyecatch'], eye_src)
    total = sum(du for _, du, _ in o.items)
    n = [0]

    def uniq():
        n[0] += 1
        return n[0]
    made, marks = {}, {}
    for e in sorted(ev, key=lambda x: x['start']):
        k = e['kind']
        if k == 'eyecatch':
            continue
        a, b = o.map(e['start']), o.map(e['end'])
        if k not in tpl:
            if not k.startswith('sfx:') and k != 'bgm':
                o.marker(a, f'要素材 {k}: {e.get("text", "")[:40]}')
                marks[k] = marks.get(k, 0) + 1
            continue
        spans = o.split_eye(a, min(b, total)) if k in NO_EYE else [(a, b)]
        for x, y in spans:
            t = ET.fromstring(tpl[k]['title'])
            t.set('ref', eff_map[(k, t.get('ref'))])
            for f in t.iter('filter-video'):
                if (k, f.get('ref')) in eff_map:
                    f.set('ref', eff_map[(k, f.get('ref'))])
            fill(t, e.get('text', ''), uniq)
            c, local = o.host(x)
            t.set('lane', str(LANES.get(k, 4)))
            t.set('offset', ts(local))
            t.set('duration', ts(max(o.fd, o.fr(y) - o.fr(x))))
            t.set('name', (e.get('text', '').split('\n')[0][:24] or k) + ' - ' + k)
            kids = list(c)
            pos = next((j for j, kk in enumerate(kids) if kk.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker',
                                                                     'filter-video', 'filter-video-mask', 'filter-audio', 'metadata')), len(kids))
            c.insert(pos, t)
            made[k] = made.get(k, 0) + 1
    sh = apply_telop_shadow.apply(tree.getroot())
    tree.write(out, encoding='UTF-8', xml_declaration=True)
    body = open(out, encoding='utf-8').read()
    m = re.search(r'<!DOCTYPE[^>]*>', head)
    body = body.replace("<?xml version='1.0' encoding='UTF-8'?>", '<?xml version="1.0" encoding="UTF-8"?>\n' + (m.group(0) if m else '<!DOCTYPE fcpxml>'), 1)
    open(out, 'w', encoding='utf-8').write(body)
    print('テロップ', made, '・アイキャッチ', len(o.eyes), '・要素材のマーカー', marks, '・影', sh)


if __name__ == '__main__':
    main()
