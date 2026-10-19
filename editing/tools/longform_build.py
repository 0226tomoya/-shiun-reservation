"""長編（ひとりで話す購入品・レビュー回）の部品の一覧（longform_events.py と同じ形の JSON）から、FCP で読み込める FCPXML を作る。

    python3 longform_build.py BASE.fcpxml EVENTS.json TEMPLATES.json OUT.fcpxml [--eyecatch-src file:///…/わむうアイキャッチ.mp4]
        [--media DIR --media-root file:///Users/…/素材/] [--shiun-catalog editing/plans/shiun_catalog.json]

- BASE: カット済みの XML（本線だけ。完成版と同じ 1 本のプロジェクト）
- EVENTS: {"events": [{"kind", "start", "end", "text"}]}（時刻はアイキャッチを入れる前のタイムラインの秒）
- TEMPLATES: longform_templates.py の出力（完成版のテロップの型）。書体・大きさ・位置・字間・フェードは型のまま、文と時刻だけ差し替える
- アイキャッチ（eyecatch）は本線に 1.4 秒の「わむうアイキャッチ」を差し込む（talk_overlay.py と同じ）。見出し・WAMU はアイキャッチの上に出さない
- 影は apply_telop_shadow.py と同じ（縁取り 0.25 → ぼかした影、見出し → ドロップシャドウのフィルタ）
- 効果音（sfx:*）は完成版と同じ素材（ユーザーの Downloads/エフェクト/SE など、完成版の asset のパスそのまま）を lane -1 に置く
- 公式サイトの画面（insert:web）は、ec_media.py で集めた商品画像（縦 3:4）を左半分に置く（完成版 A6 と同じ: lane 5・位置 −51.3889, 0）。
  画像は直前の商品カード（item_card）の商品、色のカード（color）と同じ時刻ならその色のモデル写真、無ければ全色を並べた写真。
  --media は ec_media.py の出力（商品ごとのフォルダと manifest.json）、--media-root はユーザーの Mac でその中身を置く場所（file:// の URL）
- 型の無い部品（撮影素材の寄り・BGM・商品番号の箱・冒頭プロフィール・エンディング）は、その時刻にマーカー「要素材: …」を打つ
"""
import copy
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from talk_overlay import Overlay, T, ts, new_id  # noqa: E402
import apply_telop_shadow  # noqa: E402

# 重なり順（下から）。同じ時刻に同じレーンが埋まっていれば上の空いたレーンへ
LANES = {'wamu': 2, 'heading': 3, 'op_profile': 3, 'coord_bg': 4, 'insert:web': 5, 'item_label': 6, 'item_card': 6, 'coord': 7,
         'fact': 7, 'opinion': 7, 'vertical': 7, 'title_call': 7, 'channel': 7, 'closing': 7, 'topic': 7,
         'color': 8, 'shiun_card': 8, 'price': 9, 'tsukkomi': 9}
OCC = {}


def lane_block(k, rels, x, y):
    """主の部品のレーン L と、L+rel の全部が [x, y) で空いている L を選んで埋める"""
    ln = max(LANES.get(k, 7), 1 - min(rels + [0]))
    free = lambda l: not any(a < y and x < b for a, b in OCC.get(l, []))
    while not all(free(ln + r) for r in rels + [0]):
        ln += 1
    for r in rels + [0]:
        OCC.setdefault(ln + r, []).append((x, y))
    return ln


def lane_for(k, x, y):
    ln = LANES.get(k, 7)
    while any(a < y and x < b for a, b in OCC.get(ln, [])):
        ln += 1
    OCC.setdefault(ln, []).append((x, y))
    return ln
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
        if len(tr) >= 2 and not tr[0][0].strip():  # 行頭の空白だけの run（商品番号の箱の「   Item 1」）は別に残す
            new.append((tr[0][0], tr[0][1]))
            line = line.lstrip(' ')
            tr = tr[1:]
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


def import_res(o, xml, idmap, uid_key='uid'):
    """型の resource（format・asset・media）を resources へ入れる。同じ uid（format は name＋frameDuration）が既にあればそれを使う。
    idmap: 型の id → 入れた先の id"""
    e = ET.fromstring(xml)
    old = e.get('id')
    if old in idmap:
        return idmap[old]
    if e.tag == 'format':
        have = next((f for f in o.res.findall('format') if f.get('name') == e.get('name') and f.get('frameDuration') == e.get('frameDuration')
                     and f.get('width') == e.get('width')), None)
    else:
        have = next((r for r in o.res.findall(e.tag) if r.get(uid_key) and r.get(uid_key) == e.get(uid_key)), None)
    if have is not None:
        idmap[old] = have.get('id')
        return have.get('id')
    for x in e.iter():
        for at in ('ref', 'format'):
            if x is not e and x.get(at) in idmap:
                x.set(at, idmap[x.get(at)])
        if x is e and e.get('format') in idmap:
            e.set('format', idmap[e.get('format')])
    nid = new_id(o.res, 'r')
    e.set('id', nid)
    o.res.append(e)
    idmap[old] = nid
    return nid


def host(o, t):
    """t（挿入後の時刻）を含む本線のクリップと、その中の時刻。アイキャッチの上もそのまま付ける（talk_overlay の host はアイキャッチを飛ばす）"""
    t = o.fr(t)
    for off, du, c in o.items:
        if off <= t < off + du:
            return c, T(c.get('start')) + (t - off)
    off, du, c = o.items[-1]
    return c, T(c.get('start')) + min(t - off, du - o.fd)


def place_compound(o, k, st, a, b, eff_map, text=None, uniq=None, fresh_uid=False):
    """複合クリップの部品（商品番号の箱・冒頭プロフィール）を置く。text があれば中の最初のタイトルの文を差し替える"""
    import uuid
    idm = {}
    for f in st.get('formats', []):
        import_res(o, f, idm)
    for x in st.get('assets', []):
        import_res(o, x, idm)
    for rid, x in st.get('effects', {}).items():
        e = ET.fromstring(x)
        have = next((r for r in o.res.findall('effect') if r.get('uid') == e.get('uid')), None)
        if have is None:
            e.set('id', new_id(o.res, 'r'))
            o.res.append(e)
            have = e
        idm[rid] = have.get('id')
    m = ET.fromstring(st['media'])
    for x in m.iter():
        for at in ('ref', 'format'):
            if x.get(at) in idm:
                x.set(at, idm[x.get(at)])
    dur = max(o.fd, o.fr(b) - o.fr(a))
    # 中の text-style-def の id を付け直す（同じ型を何度も入れても id がぶつからないように）
    if uniq:
        ren = {}
        for d in m.iter('text-style-def'):
            ren[d.get('id')] = f'lf{uniq()}'
            d.set('id', ren[d.get('id')])
        for r in m.iter('text-style'):
            if r.get('ref') in ren:
                r.set('ref', ren[r.get('ref')])
    if text is not None:
        t = next(m.iter('title'), None)
        if t is not None:
            fill(t, text, uniq)
        seq = m.find('sequence')
        seq.set('duration', ts(dur))
        for c in seq.find('spine'):
            c.set('duration', ts(dur))
    if fresh_uid or text is not None or not any(r.get('uid') == m.get('uid') for r in o.res.findall('media')):
        if fresh_uid or text is not None:
            m.set('uid', uuid.uuid4().hex[:22])
            m.set('name', (m.get('name') or k) + (' ' + str(uniq()) if uniq else ''))
        m.set('id', new_id(o.res, 'r'))
        o.res.append(m)
        mid = m.get('id')
    else:
        mid = next(r for r in o.res.findall('media') if r.get('uid') == m.get('uid')).get('id')
    cl = ET.fromstring(st['clip'])
    cl.set('ref', mid)
    for f in cl.iter('filter-video'):
        if f.get('ref') in idm:
            f.set('ref', idm[f.get('ref')])
    seq_d = T(m.find('sequence').get('duration'))
    c, local = host(o, a)
    cl.set('offset', ts(local))
    cl.set('duration', ts(min(dur, seq_d)))
    cl.set('lane', str(lane_for(k, a, a + min(dur, seq_d))))
    cl.set('name', m.get('name'))
    kids = list(c)
    pos = next((j for j, kk in enumerate(kids) if kk.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker',
                                                             'filter-video', 'filter-video-mask', 'filter-audio', 'metadata')), len(kids))
    c.insert(pos, cl)
    return cl


def item_text(ev, k_ev, n_item):
    """商品番号の箱の文: 「   Item N⏎ブランド⏎商品名⏎¥価格 | Color : 色」（その区間の最初の商品カード・色のカードから）"""
    a, b = k_ev['start'] - 1, k_ev['end']
    card = next((e for e in ev if e['kind'] == 'item_card' and a <= e['start'] < b), None)
    col = next((e for e in ev if e['kind'] == 'color' and a <= e['start'] < b), None)
    lines = (card.get('text', '') if card else '').split('\n')
    brand = lines[0] if lines else ''
    name = lines[1] if len(lines) > 1 else ''
    price = next((l for l in lines if '¥' in l), '')
    tail = price + (f' | Color : {col["text"]}' if col else '')
    return f'   Item {n_item}\n{brand}\n{name}\n{tail}'.rstrip()


def load_media(d):
    import glob
    import os
    out = []
    for m in sorted(glob.glob(os.path.join(d, '*', 'manifest.json'))):
        man = json.load(open(m))
        man['dir'] = os.path.basename(os.path.dirname(m))
        out.append(man)
    return out


def pick_image(media, t, ev):
    """時刻 t の公式サイトの画面に使う画像 (商品フォルダ, ファイル名) を選ぶ"""
    from difflib import SequenceMatcher
    if not media:
        return None
    cards = [e for e in ev if e['kind'] == 'item_card' and e['start'] <= t + 1]
    man = media[0]
    if cards:
        txt = cards[-1].get('text', '')
        man = max(media, key=lambda m: SequenceMatcher(None, m.get('name') or '', txt).ratio())
    col = next((e for e in ev if e['kind'] == 'color' and abs(e['start'] - t) < 1.5), None)
    files = man['files']
    if col:
        code = (col.get('text') or '').split(' ')[0]
        f = next((f for f in files if f['kind'] in ('main', 'color') and f['color'].startswith(code)), None) \
            or next((f for f in files if f['kind'] == 'sub' and f.get('color') == code), None)
        if f:
            return man['dir'], f['file']
    # 色の話でない所は、全色を並べた写真 → ほかの色なしの写真 → 色ごとの写真の順に、同じ商品で前に使っていないものを使う
    order = [f for f in files if f['kind'] == 'sub' and not f.get('color')] + [f for f in files if f['kind'] in ('main', 'color', 'detail')]
    used = USED.setdefault(man['dir'], set())
    f = next((f for f in order if f['file'] not in used), order[0] if order else None)
    if f:
        used.add(f['file'])
    return (man['dir'], f['file']) if f else None


USED = {}


def shiun_issues(text, catalog):
    """カードの文の「shiun」の次の行（商品名）と値段を、shiun の商品一覧（ec_media.py --shiun-catalog）と比べる。
    完成版は名前の「(+6cm)」などの括弧を外して書くので、括弧を外して比べる。返り値: 気になる点の一覧"""
    names = {re.sub(r'\s*\(.*?\)\s*$', '', v['name']).upper(): v['price'] for v in catalog.values()}
    lines = [x.strip() for x in text.split('\n')]
    out = []
    for i, x in enumerate(lines[:-1]):
        if x.lower() != 'shiun' or lines[i + 1].startswith('※'):
            continue
        nm = re.sub(r'\s*\(.*?\)\s*$', '', lines[i + 1]).upper()
        if nm not in names:
            out.append(f'shiun の一覧に無い名前「{lines[i + 1]}」')
            continue
        m = next((re.search(r'¥\s*([\d,]+)', y) for y in lines[i + 1:i + 4] if '¥' in y), None)
        if m and int(m.group(1).replace(',', '')) != names[nm]:
            out.append(f'「{lines[i + 1]}」の値段 ¥{m.group(1)} が一覧（¥{names[nm]:,}）と違う')
    return out


def main():
    base, evp, tpp, out = sys.argv[1:5]
    cat_p = sys.argv[sys.argv.index('--shiun-catalog') + 1] if '--shiun-catalog' in sys.argv else __file__.rsplit('/', 2)[0] + '/plans/shiun_catalog.json'
    catalog = json.load(open(cat_p)) if os.path.exists(cat_p) else {}
    eye_src = sys.argv[sys.argv.index('--eyecatch-src') + 1] if '--eyecatch-src' in sys.argv else 'file:///Users/modantaimusu/Downloads/わむうアイキャッチ.mp4'
    head = open(base, encoding='utf-8').read(400)
    tree = ET.parse(base)
    o = Overlay(tree.getroot())
    ev = json.load(open(evp))['events']
    tpl = json.load(open(tpp))
    # 型の effect を resources へ（uid が同じものがあれば使う）
    eff_map = {}
    for k, t in tpl.items():
        for rid, x in t.get('effects', {}).items():
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
    media_dir = sys.argv[sys.argv.index('--media') + 1] if '--media' in sys.argv else None
    media_root = sys.argv[sys.argv.index('--media-root') + 1] if '--media-root' in sys.argv else 'file:///Users/modantaimusu/Downloads/素材/'
    media = load_media(media_dir) if media_dir else []
    img_assets = {}
    n_item, seen_items = [0], set()
    for e in sorted(ev, key=lambda x: x['start']):
        k = e['kind']
        if k == 'eyecatch':
            continue
        a, b = o.map(e['start']), o.map(e['end'])
        for msg in (shiun_issues(e.get('text', ''), catalog) if catalog and k in ('shiun_card', 'coord', 'item_card') else []):
            o.marker(a, '要確認 ' + msg)
            print('要確認', round(e['start'], 1), msg)
        kk = k
        if k == 'bgm':
            kk = 'bgm:' + (e.get('text') or '') if 'bgm:' + (e.get('text') or '') in tpl else next((x for x in tpl if x.startswith('bgm:')), None)
        if kk and (kk.startswith('sfx:') or kk.startswith('bgm:') or kk == 'ending') and kk in tpl:
            st = tpl[kk]
            idm = {}
            for f in ([st['format']] if st.get('format') else []) + st.get('formats', []):
                import_res(o, f, idm)
            for a_ in ([st['asset']] if st.get('asset') else []) + st.get('assets', []):
                import_res(o, a_, idm)
            if st.get('media'):
                import_res(o, st['media'], idm)
            cl = ET.fromstring(st['clip'])
            cl.set('ref', idm.get(cl.get('ref'), cl.get('ref')))
            if cl.get('format') in idm:
                cl.set('format', idm[cl.get('format')])
            c, local = host(o, a)
            if k in ('bgm', 'ending'):
                full = T(cl.get('duration'))
                if k == 'bgm':
                    a_el = next((x for x in o.res if x.get('id') == cl.get('ref')), None)
                    if a_el is not None and a_el.get('duration') and T(a_el.get('duration')) > 0:
                        full = T(a_el.get('duration')) - T(cl.get('start') or '0s')
                cl.set('duration', ts(min(max(o.fd, o.fr(b) - o.fr(a)), full)))
            cl.set('lane', '-2' if k == 'bgm' else ('1' if k == 'ending' else '-1'))
            cl.set('offset', ts(local))
            kids = list(c)
            pos = next((j for j, kk in enumerate(kids) if kk.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker',
                                                                     'filter-video', 'filter-video-mask', 'filter-audio', 'metadata')), len(kids))
            c.insert(pos, cl)
            made[k] = made.get(k, 0) + 1
            continue
        if k == 'insert:web' and media:
            img = pick_image(media, e['start'], ev)
            if img:
                import os
                from PIL import Image
                from urllib.parse import quote
                w, h = Image.open(os.path.join(media_dir, *img)).size
                key = '/'.join(img)
                if key not in img_assets:
                    fid = new_id(o.res, 'r')
                    ET.SubElement(o.res, 'format', {'id': fid, 'name': 'FFVideoFormatRateUndefined', 'width': str(w), 'height': str(h), 'colorSpace': '1-13-1'})
                    aid = new_id(o.res, 'r')
                    a_ = ET.SubElement(o.res, 'asset', {'id': aid, 'name': img[1].rsplit('.', 1)[0], 'start': '0s', 'duration': '0s', 'hasVideo': '1',
                                                        'format': fid, 'videoSources': '1'})
                    ET.SubElement(a_, 'media-rep', {'kind': 'original-media', 'src': media_root.rstrip('/') + '/' + quote(img[0]) + '/' + quote(img[1])})
                    img_assets[key] = aid
                c, local = host(o, a)
                vv = ET.Element('video', {'ref': img_assets[key], 'lane': str(lane_for(k, a, b)), 'offset': ts(local), 'name': img[1], 'start': '3600s',
                                          'duration': ts(max(o.fd, o.fr(b) - o.fr(a)))})
                ET.SubElement(vv, 'adjust-transform', {'position': '-51.3889 0'})
                kids = list(c)
                pos = next((j for j, kk in enumerate(kids) if kk.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker',
                                                                         'filter-video', 'filter-video-mask', 'filter-audio', 'metadata')), len(kids))
                c.insert(pos, vv)
                made[k] = made.get(k, 0) + 1
                continue
        if k in ('item_label', 'op_profile') and k in tpl:
            if k == 'item_label':
                n_item[0] += 0 if (e.get('text') or '').strip() in seen_items else 1
                seen_items.add((e.get('text') or '').strip())
                m_ = re.search(r'(\d+)', e.get('text') or '')
                num = int(m_.group(1)) if m_ else n_item[0]
                for x, y in o.split_eye(a, min(b, total)):
                    place_compound(o, k, tpl[k], x, y, eff_map, text=item_text(ev, e, num), uniq=uniq)
            else:
                place_compound(o, k, tpl[k], a, b, eff_map, uniq=uniq)
            made[k] = made.get(k, 0) + 1
            continue
        if k not in tpl:
            if not k.startswith('sfx:') and k != 'bgm':
                o.marker(a, f'要素材 {k}: {e.get("text", "")[:40]}')
                marks[k] = marks.get(k, 0) + 1
            continue
        if k == 'coord' and 'coord_bg' in tpl:
            bg = ET.fromstring(tpl['coord_bg']['title'])
            bg.set('ref', eff_map[('coord_bg', bg.get('ref'))])
            for f in bg.iter('filter-video'):
                if ('coord_bg', f.get('ref')) in eff_map:
                    f.set('ref', eff_map[('coord_bg', f.get('ref'))])
            for d in bg.findall('text-style-def'):  # 背景には文が無いので id だけ付け直す
                nid = f'lf{uniq()}'
                for r in bg.iter('text-style'):
                    if r.get('ref') == d.get('id'):
                        r.set('ref', nid)
                d.set('id', nid)
            c, local = host(o, a)
            bg.set('lane', str(lane_for('coord_bg', a, b)))
            bg.set('offset', ts(local))
            bg.set('duration', ts(max(o.fd, o.fr(b) - o.fr(a))))
            bg.set('name', '背景 06 - coord')
            kids = list(c)
            pos = next((j for j, kk in enumerate(kids) if kk.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker',
                                                                     'filter-video', 'filter-video-mask', 'filter-audio', 'metadata')), len(kids))
            c.insert(pos, bg)
        if k == 'channel' and 'shiun' in (e.get('text') or '') and 'channel:shiun' in tpl:
            k = 'channel:shiun'
        spans = o.split_eye(a, min(b, total)) if k in NO_EYE else [(a, b)]
        for x, y in spans:
            t = ET.fromstring(tpl[k]['title'])
            t.set('ref', eff_map[(k, t.get('ref'))])
            for f in t.iter('filter-video'):
                if (k, f.get('ref')) in eff_map:
                    f.set('ref', eff_map[(k, f.get('ref'))])
            fill(t, e.get('text', ''), uniq)
            c, local = host(o, x)
            withs = tpl[k].get('with', [])
            ln = lane_block(k.split(':')[0], [w['rel'] for w in withs], x, y) if withs else lane_for(k, x, y)
            t.set('lane', str(ln))
            for w in withs:
                idm = {}
                for f in w.get('formats', []):
                    import_res(o, f, idm)
                for x_ in w.get('assets', []):
                    import_res(o, x_, idm)
                for rid, ex in w.get('effects', {}).items():
                    ee = ET.fromstring(ex)
                    have = next((r for r in o.res.findall('effect') if r.get('uid') == ee.get('uid')), None)
                    if have is None:
                        ee.set('id', new_id(o.res, 'r'))
                        o.res.append(ee)
                        have = ee
                    idm[rid] = have.get('id')
                el = ET.fromstring(w['xml'])
                for z in el.iter():
                    for at in ('ref', 'format'):
                        if z.get(at) in idm:
                            z.set(at, idm[z.get(at)])
                for d in el.iter('text-style-def'):
                    nid = f'lf{uniq()}'
                    for r in el.iter('text-style'):
                        if r.get('ref') == d.get('id'):
                            r.set('ref', nid)
                    d.set('id', nid)
                el.set('lane', str(ln + w['rel']))
                el.set('offset', ts(local))
                el.set('duration', ts(max(o.fd, o.fr(y) - o.fr(x))))
                kids = list(c)
                pos = next((j for j, kk in enumerate(kids) if kk.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker',
                                                                         'filter-video', 'filter-video-mask', 'filter-audio', 'metadata')), len(kids))
                c.insert(pos, el)
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
