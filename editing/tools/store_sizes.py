"""shiun ONLINE STORE（shiun-store.com）の全商品のサイズ表を集める。
    python3 store_sizes.py 取り出し先フォルダ [最初のID] [最後のID] [--parse-only]
    python3 store_sizes.py 取り出し先フォルダ --md 一覧.md   … 集めた JSON から一覧の Markdown を作る
商品ページ（/products/detail.php?product_id=N）を 1 秒おきに取り、名前・価格・カテゴリ・品番・サイズ表・推奨サイズ・素材を JSON に書く。
ページは html/ に残すので、読み取り直しはネットにつながずにできる（--parse-only）"""
import sys, os, re, json, time, html, urllib.request

BASE = 'https://shiun-store.com/products/detail.php?product_id='
UA = {'User-Agent': 'Mozilla/5.0 (shiun editing team size-table collector)'}


def text(s):
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'[ \t　]+', ' ', html.unescape(s)).strip()


def parse(pid, s):
    if 'size_table' not in s and 'detail_tit' not in s:
        return None
    h1 = re.search(r'<h1 class="fontL">(.*?)</h1>', s, re.S)
    name = text(h1.group(1)) if h1 else ''
    d = {'product_id': pid, 'name': name, 'url': BASE + str(pid)}
    m = re.search(r'img\.shiun-store\.com/product/([a-z0-9]+)/', s)
    d['code'] = m.group(1) if m else ''
    # 価格（税込の表記を拾う）
    m = re.search(r'<ul id="detail_price">(.*?)</ul>', s, re.S)
    d['price_text'] = text(m.group(1)) if m else ''   # 例「¥ 5,940 - tax in」。SALE は元の価格も並ぶことがある
    nums = re.findall(r'[0-9][0-9,]+', d['price_text'])
    d['price'] = int(nums[-1].replace(',', '')) if nums else None
    # パンくず（カテゴリ）
    # サイズ表
    st = re.search(r'<div class="size_table">(.*?)</div>', s, re.S)
    if st:
        rows = [[text(li) for li in re.findall(r'<li[^>]*>(.*?)</li>', ul, re.S)] for ul in re.findall(r'<ul[^>]*>(.*?)</ul>', st.group(1), re.S)]
        head = rows[0][1:] if rows else []
        d['size_items'] = head
        d['sizes'] = {r[0]: dict(zip(head, r[1:])) for r in rows[1:] if r}
    else:
        d['size_items'], d['sizes'] = [], {}
    # 推奨サイズ・着用の情報
    m = re.search(r'推奨サイズ</b>(.*?)</p>', s, re.S)
    d['recommend'] = [t for t in text(m.group(1)).split('\n') if t.strip()] if m else []
    # 素材・原産国
    m = re.search(r'MATERIAL.*?</h2>(.*?)</div>', s, re.S) or re.search(r'MATERIAL(.*?)COUNTRY', s, re.S)
    d['material'] = text(m.group(1))[:400] if m else ''
    m = re.search(r'COUNTRY OF ORIGIN.*?</h2>(.*?)</div>', s, re.S)
    d['origin'] = text(m.group(1))[:60] if m else ''
    # 色
    d['colors'] = sorted(set(text(x) for x in re.findall(r'<div class="cart_item_photo">.*?<p>(.*?)</p>', s, re.S)))
    d['sold_out_all'] = 'ADD TO CART' not in s
    return d


CATS = {40: ('OUTER', 'JACKET'), 12: ('OUTER', 'BLOUSON'), 1: ('OUTER', ''), 9: ('SHIRT', 'SHIRT'), 39: ('TOPS', 'CUT&SEW'), 16: ('TOPS', 'KNIT'), 3: ('TOPS', ''),
        38: ('BOTTOMS', 'DENIM'), 19: ('BOTTOMS', 'SLACKS'), 4: ('BOTTOMS', ''), 28: ('SHOES', 'SHOES'), 45: ('ACCESSORY', 'BELT'), 42: ('ACCESSORY', '')}


def categories(out, parse_only):
    """一覧ページ（今ストアに出ている商品）から、商品 ID → (大分類, 小分類) を作る。細かい分類を優先する"""
    cat = {}
    for cid in sorted(CATS, key=lambda c: CATS[c][1] == ''):  # 小分類のある方を先に
        for page in range(1, 20):
            fn = f'{out}/html/list_{cid}_{page}.html'
            if not os.path.exists(fn) and not parse_only:
                try:
                    req = urllib.request.Request(f'https://shiun-store.com/products/list.php?category_id={cid}&pageno={page}', headers=UA)
                    with urllib.request.urlopen(req, timeout=30) as r: body = r.read().decode('utf-8', 'replace')
                except Exception as e:
                    body = ''
                open(fn, 'w').write(body); time.sleep(1.0)
            body = open(fn).read() if os.path.exists(fn) else ''
            ids = set(int(x) for x in re.findall(r'detail\.php\?product_id=(\d+)', body.split('id="left_culmn"')[0]))
            new = ids - set(k for k, v in cat.items() if v[2] == (cid, page))
            for i in ids: cat.setdefault(i, CATS[cid] + ((cid, page),))
            if not ids or f'pageno={page + 1}' not in body: break
    return {k: v[:2] for k, v in cat.items()}


def guess_category(d):
    """一覧に無い商品（売り切れ・過去の商品）は、サイズ表の項目と名前から推す"""
    items, n = set(d['size_items']), d['name'].upper()
    if {'股上', '股下'} & items or 'ワタリ' in items: return ('BOTTOMS', 'DENIM' if 'DENIM' in n else 'SLACKS' if 'SLACKS' in n or 'TROUSERS' in n else '')
    if any(k in n for k in ('SHOES', 'LOAFER', 'DERBY', 'BOOTS', 'SNEAKER', 'MULE')): return ('SHOES', 'SHOES')
    if 'BELT' in n: return ('ACCESSORY', 'BELT')
    if any(k in n for k in ('JACKET', 'COAT', 'BLOUSON', 'VEST', 'GILET')): return ('OUTER', 'JACKET' if 'JACKET' in n else 'BLOUSON' if 'BLOUSON' in n else '')
    if 'SHIRT' in n and 'T-SHIRT' not in n: return ('SHIRT', 'SHIRT')
    if any(k in n for k in ('KNIT', 'CARDIGAN', 'SWEATER')): return ('TOPS', 'KNIT')
    if any(k in n for k in ('TEE', 'POLO', 'SWEAT', 'HOODIE', 'PARKA')): return ('TOPS', 'CUT&SEW')
    return ('', '')


def main():
    out = sys.argv[1]; os.makedirs(f'{out}/html', exist_ok=True)
    a = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
    b = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 420
    parse_only = '--parse-only' in sys.argv
    items = []
    for pid in range(a, b + 1):
        fn = f'{out}/html/{pid}.html'
        if not os.path.exists(fn) and not parse_only:
            try:
                req = urllib.request.Request(BASE + str(pid), headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r:
                    body = r.read().decode('utf-8', 'replace')
                    if 'sorry' in r.geturl():
                        body = ''
            except Exception as e:
                body = ''; print(pid, 'ERR', e, flush=True)
            open(fn, 'w').write(body); time.sleep(1.0)
        s = open(fn).read() if os.path.exists(fn) else ''
        d = parse(pid, s) if s else None
        if d and d['name']:
            items.append(d); print(pid, d['name'], len(d['sizes']), 'sizes', flush=True)
    cat = categories(out, parse_only)
    for d in items:
        if d['product_id'] in cat:
            d['category'], d['subcategory'] = cat[d['product_id']]; d['on_list'] = True
        else:
            d['category'], d['subcategory'] = guess_category(d); d['on_list'] = False
    json.dump(items, open(f'{out}/store_sizes.json', 'w'), ensure_ascii=False, indent=1)
    print('done', len(items))


if __name__ == '__main__' and '--md' not in sys.argv:
    main()


def write_md(items, path, fetched):
    """サイズ表の一覧（分類ごと）を Markdown にする"""
    order = ['OUTER', 'SHIRT', 'TOPS', 'BOTTOMS', 'SHOES', 'ACCESSORY', '']
    L = [f'# shiun ONLINE STORE のサイズ表（全 {len(items)} 商品・{fetched} に取得）', '',
         '元: https://shiun-store.com/ の各商品ページの SIZING。取り直しは `python3 editing/tools/store_sizes.py 作業フォルダ` → この表と `store_sizes.json` を作り直す。',
         '価格は税込。ウエストはストアの表のまま（周囲の長さ。イージーパンツはゴムの伸びの幅「72 - 80cm」）。靴の「cm」は足の大きさの目安。', '']
    for cat in order:
        xs = sorted([x for x in items if x['category'] == cat], key=lambda x: (x['subcategory'], x['product_id']))
        if not xs: continue
        L += [f'## {cat or "分類なし"}（{len(xs)}）', '']
        for x in xs:
            L += [f"### {x['name']}（{x['subcategory']}・¥{x['price']:,}・ID {x['product_id']}・品番 {x['code']}）", '']
            head = x['size_items']
            L += ['| サイズ | ' + ' | '.join(head) + ' |', '|' + '---|' * (len(head) + 1)]
            for sz, row in x['sizes'].items():
                L.append(f'| {sz} | ' + ' | '.join(row.get(h, '').replace('cm', '') for h in head) + ' |')
            rec = [r for r in x['recommend'] if r.startswith('サイズ')]; wear = [r for r in x['recommend'] if not r.startswith('サイズ')]
            if rec: L.append('\n推奨: ' + ' / '.join(r.replace('サイズ', '') for r in rec))
            if wear: L.append('着用: ' + ' / '.join(wear))
            L += [f"色: {', '.join(x['colors'])}　素材: {x['material'].splitlines()[0] if x['material'] else ''}　{x['url']}", '']
    open(path, 'w').write('\n'.join(L))


if __name__ == '__main__' and '--md' in sys.argv:
    out = sys.argv[1]
    write_md(json.load(open(f'{out}/store_sizes.json')), sys.argv[sys.argv.index('--md') + 1], time.strftime('%Y-%m-%d'))
