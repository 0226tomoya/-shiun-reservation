"""ユニクロ・GU の公式オンラインストアから、挿し込み（インサート）の素材を集める。画像集めも編集の仕事。

    python3 ec_media.py OUTDIR uniqlo:E487257-000[:08] gu:E360398-000[:66] ...

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
import json
import os
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


def main():
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    for spec in sys.argv[2:]:
        brand, rest = spec.split(':', 1)
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
