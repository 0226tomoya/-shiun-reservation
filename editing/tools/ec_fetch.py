"""ユニクロ・GU の公式オンラインストアから、商品ページの文（説明・素材・仕様・洗濯）を取る。テロップの「事実」の材料。

    python3 ec_fetch.py OUT.md uniqlo:ブラッシュドジャージーワイドパンツ gu:ストレートジーンズ ...

完成版 6 本の事実のテロップは、商品ページの文を短くしたものが多い（A6「素材：ポリエステル48%・綿38%・レーヨン14%」＝素材の欄、
「ツータック入っていて上品な印象もある」＝説明「ツータックで…上品で洗練された印象」）。
同じ名前の商品が何代もあるので、候補を 3 つまで並べる（発言の価格・色で選ぶ）。無印良品のサイトはこの環境から開けない。
"""
import json
import re
import subprocess
import sys
import urllib.parse

HOST = {'uniqlo': 'https://www.uniqlo.com/jp/api/commerce/v5/ja', 'gu': 'https://www.gu-global.com/jp/api/commerce/v5/ja'}


def get(url):
    for _ in range(3):
        r = subprocess.run(['curl', '-sS', '-m', '20', '-A', 'Mozilla/5.0', url], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.startswith('{'):
            return json.loads(r.stdout)
    return None


def clean(s):
    s = re.sub(r'<br\s*/?>', '\n', s or '')
    return re.sub(r'<[^>]+>', '', s).strip()


def main():
    out = sys.argv[1]
    lines = []
    for spec in sys.argv[2:]:
        brand, q = spec.split(':', 1)
        base = HOST[brand]
        d = get(f'{base}/products?q={urllib.parse.quote(q)}&limit=20')
        items = (d or {}).get('result', {}).get('items', []) if d else []
        from difflib import SequenceMatcher
        # 名前の近い順・色の多い順に 3 つまで（どれが紹介した商品かは、発言の価格・色で選ぶ）
        cand = sorted(items, key=lambda x: (-SequenceMatcher(None, q, x['name']).ratio(), -len(x.get('colors') or []), x['productId']))[:3]
        if not cand:
            lines.append(f'## {brand.upper()} {q}\n（見つからない）\n')
            continue
        lines.append(f'## 「{q}」の候補（{brand.upper()}）\n')
        for it in cand:
            det = get(f"{base}/products/{it['productId']}/price-groups/{it.get('priceGroup', '00')}/details?includeModelSize=false&httpFailure=true")
            r = (det or {}).get('result', {})
            price = it.get('prices', {}).get('base', {}).get('value')
            cols = ', '.join(f"{c['displayCode']} {c['name']}" for c in r.get('colors', []))
            lines.append(f"### {r.get('name') or it['name']}（{it['productId']}・¥{price:,}）" if price else f"### {it['name']}")
            lines.append(f'- 色: {cols}')
            for k, nm in (('shortDescription', '短い説明'), ('longDescription', '説明'), ('designDetail', '仕様'), ('composition', '素材'),
                          ('washingInformation', '洗濯'), ('freeInformation', 'お知らせ')):
                if r.get(k):
                    lines.append(f'- {nm}: ' + clean(r[k]).replace('\n', ' / '))
            lines.append('')
    open(out, 'w').write('# 商品ページの文（公式オンラインストア）\n\n' + '\n'.join(lines))
    print(open(out).read()[:3000])


if __name__ == '__main__':
    main()
