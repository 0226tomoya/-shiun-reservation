"""長編（ひとりで話す購入品・レビュー回）の部品の一覧（longform_events.py と同じ形の JSON）から、FCP で読み込める FCPXML を作る。

    python3 longform_build.py BASE.fcpxml EVENTS.json TEMPLATES.json OUT.fcpxml [--eyecatch-src file:///…/わむうアイキャッチ.mp4]
        [--media DIR --media-root file:///Users/…/素材/]

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
    for e in sorted(ev, key=lambda x: x['start']):
        k = e['kind']
        if k == 'eyecatch':
            continue
        a, b = o.map(e['start']), o.map(e['end'])
        if k.startswith('sfx:') and k in tpl:
            st = tpl[k]
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
            cl.set('lane', '-1')
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
                vv = ET.Element('video', {'ref': img_assets[key], 'lane': '5', 'offset': ts(local), 'name': img[1], 'start': '3600s',
                                          'duration': ts(max(o.fd, o.fr(b) - o.fr(a)))})
                ET.SubElement(vv, 'adjust-transform', {'position': '-51.3889 0'})
                kids = list(c)
                pos = next((j for j, kk in enumerate(kids) if kk.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker',
                                                                         'filter-video', 'filter-video-mask', 'filter-audio', 'metadata')), len(kids))
                c.insert(pos, vv)
                made[k] = made.get(k, 0) + 1
                continue
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
            c, local = host(o, x)
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
