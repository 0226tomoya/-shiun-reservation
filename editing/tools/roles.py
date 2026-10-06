"""shiun ラインナップ動画のテロップを「役割」に分類する。

fcpxml_flatten.py の出力（items の dict）を受け取り、role 名を返す。
役割は README の型（名前カード、コレクション名、商品名ラベル、字幕、セクションラベル、
身長別比較の各パーツ、ED 一覧など）に対応する。
"""
import re

SECTION_WORDS = {'Material', 'Design', 'Silhouette', 'Detail', 'Wash', 'Color'}


def text(i):
    return ''.join(r['text'] for t in i.get('texts', []) for r in t['runs'])


def first_style(i):
    for t in i.get('texts', []):
        for r in t['runs']:
            if r['text'].strip():
                return i.get('styles', {}).get(r['ref'], {})
    st = list(i.get('styles', {}).values())
    return st[0] if st else {}


def pos(i):
    p = i.get('params', {}).get('位置')
    return tuple(float(x) for x in p.split()) if p else (0.0, 0.0)


def tr(i):
    t = i.get('adjust-transform') or {}
    p = tuple(float(x) for x in t.get('position', '0 0').split())
    s = float(t.get('scale', '1 1').split()[0])
    return p, s


def role(i):
    if i['tag'] != 'title':
        return None
    eff = (i.get('effect') or {}).get('name')
    if eff == 'Adjustment Layer':
        return 'adjustment_main' if i.get('lane') == '1' and len(i.get('path', [])) <= 1 else 'adjustment_other'
    t = text(i).strip()
    if not t:
        return 'empty'
    st = first_style(i)
    font, size = st.get('font'), float(st.get('fontSize', 0) or 0)
    color = st.get('fontColor', '1 1 1 1')
    olive = color.startswith('0.32')
    x, y = pos(i)
    (tx, ty), sc = tr(i)
    first = t.split('\n')[0].strip()
    if first == 'WAMU':
        return 'name_card'
    if t == 'SOLD OUT':
        return 'sold_out'
    if first in SECTION_WORDS:
        return 'section_label'
    if font == 'Klee':
        if t.startswith('色味は'):
            return 'size_note'
        if size >= 45 or (y > -300 and abs(x) < 50):
            return 'emphasis'
        return 'subtitle'
    if font == 'Hiragino Mincho ProN':
        if re.match(r'^\d\d \(', first):
            return 'shoe_size_label'
        return 'size_spec_value' if re.match(r'^(XXS|XS|S|M|L)$', first) else 'size_spec_header'
    if re.match(r'^\d{3}cm \d+kg$', first):
        return 'size_height_label'
    if olive and re.match(r'^(XXS|XS|S|M|L|XL)$', first):
        return 'size_letter'
    if olive:
        return 'size_product_name'
    if re.match(r'^\d{4}\.\d', first):
        return 'release_date_center'
    if first.startswith('shiun') and 'Collection' in t:
        if '\n' in t and re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)', t):
            if x < -600:
                return 'collection_label'
            return 'collection_label_center'
        return 'collection_center'
    if font == 'Masqualero':
        if abs(sc - 0.6) < 0.05:
            return 'ed_product_name'
        if x < -600 and y > 150:
            return 'product_label'
        if x < -600 and y < -150:
            return 'product_label_bottom'
        return 'product_center'
    return 'other'


ROLE_JA = {
    'name_card': '名前カード', 'collection_label': 'コレクション名（左上）', 'collection_label_center': 'コレクション名（中央・上）',
    'collection_center': 'コレクション名（ティーザー中央）', 'release_date_center': '発売日（中央）', 'product_label': '商品名ラベル（左上）',
    'product_label_bottom': '商品名ラベル（左下）', 'product_center': '中央商品名', 'ed_product_name': 'ED 一覧の商品名',
    'section_label': 'セクションラベル', 'subtitle': '字幕', 'emphasis': '強調', 'sold_out': 'SOLD OUT',
    'size_height_label': '身長体重', 'size_letter': 'サイズ記号', 'size_spec_value': 'サイズ表の数値', 'size_spec_header': 'サイズ表の項目名',
    'size_product_name': 'サイズ比較の商品名', 'size_note': '色味の注意書き', 'shoe_size_label': '靴サイズ', 'adjustment_main': '調整レイヤー（メイン）',
    'adjustment_other': '調整レイヤー（その他）', 'empty': '空', 'other': 'その他',
}
