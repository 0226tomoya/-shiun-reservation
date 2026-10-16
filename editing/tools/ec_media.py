"""ユニクロ・GU・shiun の公式オンラインストアから、挿し込み（インサート）の素材を集める。画像集めも編集の仕事。

    python3 ec_media.py OUTDIR uniqlo:E487257-000[:08] gu:E360398-000[:66] shiun:292 shiun:"HICOUNT WASHER" ...
    python3 ec_media.py --shiun-catalog OUT.json [--scan 1-450]   # shiun の商品一覧（番号・名前・価格）を作る

shiun（https://shiun-store.com）は商品番号（detail.php?product_id=）か、商品名の一部（一覧から探す。--scan で作った一覧があればそれも）。
  color_<色名>.jpg/png … 色ごとの商品画像（大きい方。一覧の _s を外したもの）
  detail_NN.jpg/png    … ディテールの画像
  snap_NN_<人>.jpg     … 公式の着用スナップ（manifest に着ている人・身長・サイズ。例 MATSU 160cm XS）
  manifest.json        … 名前・価格・色・説明（DETAIL）・サイズ表・推奨サイズ・素材の文・原産国も入れる（事実のテロップの材料）

商品ごとに OUTDIR/<商品番号>/ へ:
  main_<色番号>.jpg   … 色ごとの商品画像（3:4）。完成版の「色の切り替え」「商品カード」の下に敷く写真
  sub_NN_<色>.jpg     … モデルの着用・寄りの写真
  feature_N.jpg       … 公式の「特長」の画像（説明の文つき → manifest.json）
  page.png            … 商品ページの画面（1920×1080）。完成版の「公式サイトの画面」（insert:web）の静止画版
  page_scroll.mp4     … 商品ページを上から 7.6 秒かけてゆっくり下へ送る画面録画（完成版の Google Chrome の画面録画と同じ長さ）
  manifest.json       … 商品名・価格・色の一覧・各ファイルの説明
色番号を付けると、その色を選んだ状態の商品ページを撮る。
ページの撮影は Playwright＋入っている Chromium（/opt/pw-browsers）。プロキシは HTTPS_PROXY をそのまま使う。
"""
import glob
import html
import json
import os
import re
import subprocess
import sys

HOST = {'uniqlo': ('https://www.uniqlo.com/jp/api/commerce/v5/ja', 'https://www.uniqlo.com/jp/ja/products'),
        'gu': ('https://www.gu-global.com/jp/api/commerce/v5/ja', 'https://www.gu-global.com/jp/ja/products')}


def get_json(url):
    for _ in range(3):
        r = subprocess.run(['curl', '-sS', '-m', '20', '-A', 'Mozilla/5.0', url], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.startswith('{'):
            return json.loads(r.stdout)
    return None


def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True
    r = subprocess.run(['curl', '-sS', '-m', '30', '-A', 'Mozilla/5.0', '-o', path, url])
    return r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 1000


SHIUN = 'https://shiun-store.com'


def get_text(url):
    for _ in range(3):
        r = subprocess.run(['curl', '-sS', '-m', '30', '-A', 'Mozilla/5.0', url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode('utf-8', 'replace')
    return ''


def strip(h):
    h = re.sub(r'<br\s*/?>', '\n', h)
    return html.unescape(re.sub(r'<[^>]+>', '', h)).strip()


def shiun_catalog(scan=None):
    """一覧ページ（pageno=1,2,…）と、指定があれば番号の総当たりから、番号・名前・価格の一覧を作る"""
    cat = {}
    for n in range(1, 30):
        x = get_text(f'{SHIUN}/products/list.php?pageno={n}')
        got = re.findall(r'href="/products/detail\.php\?product_id=(\d+)".*?<p class="mg_t10">(.*?)<br><span class="font_gray">&yen;\s*([\d,]+)', x, re.S)
        if not got:
            break
        for pid, nm, pr in got:
            cat[pid] = {'name': strip(nm), 'price': int(pr.replace(',', ''))}
    if scan:
        a, b = map(int, scan.split('-'))
        for pid in range(a, b + 1):
            if str(pid) in cat:
                continue
            x = get_text(f'{SHIUN}/products/detail.php?product_id={pid}')
            m = re.search(r'<title>[^<]*?ONLINE STORE\s*/\s*([^<]+)</title>', x)
            if m and 'detail_item_info' in x:
                pr = re.search(r'&yen;\s*</?[^>]*>?\s*([\d,]+)|¥\s*([\d,]+)', x)
                cat[str(pid)] = {'name': html.unescape(m.group(1)).strip(), 'price': int((pr.group(1) or pr.group(2)).replace(',', '')) if pr else None}
    return cat


def shiun_find(q):
    """商品名の一部から番号を探す（一覧に無ければ None）"""
    if q.isdigit():
        return q
    cat = shiun_catalog()
    ql = q.lower()
    hit = [pid for pid, v in cat.items() if ql in v['name'].lower()]
    return hit[0] if hit else None


def shiun_detail(pid):
    x = get_text(f'{SHIUN}/products/detail.php?product_id={pid}')
    if 'detail_item_info' not in x:
        return None
    big = lambda u: re.sub(r'_s(\.\w+)$', r'\1', u.split('?')[0])
    r = {'name': html.unescape(re.search(r'<title>[^<]*?ONLINE STORE\s*/\s*([^<]+)</title>', x).group(1)).strip()}
    t = strip(re.sub(r'<script.*?</script>|<style.*?</style>', '', x, flags=re.S))
    pm = re.search(r'¥\s*([\d,]+)', t)
    r['price'] = int(pm.group(1).replace(',', '')) if pm else None
    ci = x.find('COLOR IMAGE')
    r['colors'] = [(big(u), c.strip()) for u, c in re.findall(r'data-src="([^"]+)"[^>]*>\s*<p class="item_photo_color">([^<]*)</p>', x[ci:ci + 6000])]
    di = x.find('DETAIL IMAGE')
    de = x.find('</ul>', di)
    r['details'] = [big(u) for u in re.findall(r'data-src="(https://img\.shiun-store\.com/product/[^"]+)"', x[di:de])]
    r['snaps'] = []
    for u, who, info in re.findall(r'<div class="swiper-slide">\s*<a href="/contents/coordinate_detail\.php\?cid=\d+"[^>]*><img [^>]*data-src="([^"]+)"[^>]*><p class="mg_t10">([^<]*)<br><span class="font_gray">(.*?)</span>', x, re.S):
        r['snaps'].append({'url': big(u), 'who': who.strip(), 'info': strip(info).replace('\n', ' ')})
    for key, tit in (('detail', 'DETAIL'), ('sizing', 'SIZING'), ('material', 'MATERIAL'), ('origin', 'COUNTRY OF ORIGIN')):
        m = re.search(r'<h2 class="detail_tit">%s</h2>\s*<div class="item_info_hidden">(.*?)</div>\s*</div>' % tit, x, re.S)
        if not m:
            continue
        blk = m.group(1)
        if key == 'sizing':
            rows = [[strip(li) for li in re.findall(r'<li>(.*?)</li>', ul, re.S)] for ul in re.findall(r'<ul[^>]*>(.*?)</ul>', blk, re.S)]
            r['size_table'] = rows
            rec = re.search(r'<b>推奨サイズ</b>(.*?)</p>', blk, re.S)
            r['size_note'] = strip(rec.group(1)) if rec else ''
        else:  # 「*画像はサンプル…」などの注意書きの行は落とす
            r[key] = '\n'.join(l for l in re.sub(r'\n\s*\n+', '\n', strip(blk)).split('\n') if not l.startswith('*'))
    return r


def chromium():
    c = glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')
    return c[0] if c else None


def shoot(url, out_png, out_mp4, secs=7.6):
    """商品ページの静止画と、ゆっくり下へ送る画面録画を撮る"""
    from playwright.sync_api import sync_playwright
    px = os.environ.get('HTTPS_PROXY')
    vdir = os.path.join(os.path.dirname(out_mp4), '_video')
    os.makedirs(vdir, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chromium(), proxy={'server': px} if px else None, args=['--ignore-certificate-errors'])
        ctx = b.new_context(viewport={'width': 1920, 'height': 1080}, locale='ja-JP', ignore_https_errors=True,
                            record_video_dir=vdir, record_video_size={'width': 1920, 'height': 1080})
        pg = ctx.new_page()
        pg.goto(url, timeout=60000, wait_until='domcontentloaded')
        pg.wait_for_timeout(7000)
        for sel in ('button[aria-label="閉じる"]', 'button:has-text("閉じる")', '[class*="close"]'):
            try:
                pg.locator(sel).first.click(timeout=800)
            except Exception:
                pass
        pg.keyboard.press('Escape')
        pg.wait_for_timeout(800)
        pg.screenshot(path=out_png)
        t0 = pg.evaluate('performance.now()')
        steps = int(secs * 30)
        for i in range(steps):  # 7.6 秒で 1 画面ぶん弱（900px）送る
            pg.evaluate(f'window.scrollTo(0, {900 * (i + 1) / steps})')
            pg.wait_for_timeout(1000 / 30)
        pg.wait_for_timeout(300)
        lead = t0 / 1000.0
        vid = pg.video.path()
        ctx.close()
        b.close()
    # 頭の読み込み待ちを切り落として、静止画の所から 7.6 秒
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{max(0, lead - 0.2):.2f}', '-i', vid, '-t', f'{secs}',
                    '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-y', out_mp4], check=True)
    os.remove(vid)
    try:
        os.rmdir(vdir)
    except OSError:
        pass


def do_shiun(outdir, q):
    pid = shiun_find(q)
    r = shiun_detail(pid) if pid else None
    if not r:
        print('shiun', q, '見つからない（--shiun-catalog --scan で一覧を作って番号で指定）')
        return
    od = os.path.join(outdir, f'shiun_{pid}')
    os.makedirs(od, exist_ok=True)
    man = {'brand': 'shiun', 'productId': pid, 'url': f'{SHIUN}/products/detail.php?product_id={pid}',
           **{k: v for k, v in r.items() if k not in ('colors', 'details', 'snaps')}, 'colors': [c for _, c in r['colors']], 'files': []}
    for u, c in r['colors']:
        f = f'color_{re.sub(r"[^A-Za-z0-9]+", "_", c) or "x"}{os.path.splitext(u)[1]}'
        if download(u, os.path.join(od, f)):
            man['files'].append({'file': f, 'kind': 'color', 'color': c})
    for i, u in enumerate(r['details']):
        f = f'detail_{i:02d}{os.path.splitext(u)[1]}'
        if download(u, os.path.join(od, f)):
            man['files'].append({'file': f, 'kind': 'detail'})
    for i, sn in enumerate(r['snaps']):
        f = f'snap_{i:02d}_{re.sub(r"[^A-Za-z0-9]+", "", sn["who"])}{os.path.splitext(sn["url"])[1]}'
        if download(sn['url'], os.path.join(od, f)):
            man['files'].append({'file': f, 'kind': 'snap', 'who': sn['who'], 'info': sn['info']})
    try:
        shoot(man['url'], os.path.join(od, 'page.png'), os.path.join(od, 'page_scroll.mp4'))
        man['files'] += [{'file': 'page.png', 'kind': 'page'}, {'file': 'page_scroll.mp4', 'kind': 'page_scroll'}]
    except Exception as e:  # noqa: BLE001
        print('shiun', q, 'ページの撮影に失敗:', e)
    json.dump(man, open(os.path.join(od, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
    print(f"shiun:{q}: {man['name']} ¥{man['price']} 色 {len(man['colors'])}・ファイル {len(man['files'])}")


def main():
    if sys.argv[1] == '--shiun-catalog':
        scan = sys.argv[sys.argv.index('--scan') + 1] if '--scan' in sys.argv else None
        cat = shiun_catalog(scan)
        json.dump(cat, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
        print(len(cat), '点')
        return
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    for spec in sys.argv[2:]:
        brand, rest = spec.split(':', 1)
        if brand == 'shiun':
            do_shiun(outdir, rest)
            continue
        pid, _, color = rest.partition(':')
        api, page = HOST[brand]
        d = get_json(f'{api}/products/{pid}/price-groups/00/details?includeModelSize=false&httpFailure=true')
        r = (d or {}).get('result') or {}
        if not r:
            print(spec, '見つからない')
            continue
        od = os.path.join(outdir, pid)
        os.makedirs(od, exist_ok=True)
        cols = {c['displayCode']: c['name'] for c in r.get('colors', [])}
        man = {'brand': brand.upper(), 'productId': pid, 'name': r.get('name'), 'colors': cols,
               'price': ((r.get('prices') or {}).get('base') or {}).get('value'), 'files': []}
        im = r.get('images') or {}
        for code, v in (im.get('main') or {}).items():
            p_ = os.path.join(od, f'main_{code}.jpg')
            if download(v['image'], p_):
                man['files'].append({'file': os.path.basename(p_), 'kind': 'main', 'color': f'{code} {cols.get(code, "")}'.strip()})
        for i, v in enumerate(im.get('sub') or []):
            code = v.get('colorCode', '')
            p_ = os.path.join(od, f'sub_{i:02d}_{code}.jpg')
            if download(v['image'], p_):
                man['files'].append({'file': os.path.basename(p_), 'kind': 'sub', 'color': code,
                                     'model': (v.get('model') or [{}])[0].get('modelGender')})
        for i, v in enumerate(im.get('features') or []):
            p_ = os.path.join(od, f'feature_{i + 1}.jpg')
            if download(v['imageUrl'], p_):
                man['files'].append({'file': os.path.basename(p_), 'kind': 'feature', 'text': v.get('text')})
        url = f'{page}/{pid}/00' + (f'?colorDisplayCode={color}' if color else '')
        try:
            shoot(url, os.path.join(od, 'page.png'), os.path.join(od, 'page_scroll.mp4'))
            man['files'] += [{'file': 'page.png', 'kind': 'page', 'url': url}, {'file': 'page_scroll.mp4', 'kind': 'page_scroll', 'url': url}]
        except Exception as e:  # noqa: BLE001
            print(spec, 'ページの撮影に失敗:', e)
        json.dump(man, open(os.path.join(od, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
        print(f"{spec}: {man['name']} ¥{man['price']} 色 {len(cols)}・ファイル {len(man['files'])}")


if __name__ == '__main__':
    main()
