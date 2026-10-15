"""過去の shiun ショートの編集データ（fcpxml_flat の JSON）から、評価用の「正解」を取り出す。
    python3 short_gold.py FLAT.json NAME T0 T1 OUT.json
出すもの（時刻はプロジェクトの頭からの秒）:
  cuts:    本線（mc-clip・lane なし）の [頭, 長さ]
  subs:    字幕（Klee・字幕の位置）[頭, 長さ, 文]
  cards:   商品名（Masqualero）・サイズのラベル（〜cm / Size）・発売日（20xx.x.x）[頭, 長さ, 文, 種類]
  se:      効果音（決定ボタン など、lane が正の asset-clip で長さ 2 秒未満）[頭]
  inserts: インサート（lane 2 以上の video・asset-clip・ref-clip。BGM・効果音・〆を除く）[頭, 長さ, 名前]
  bgm:     [名前, 音量]
"""
import json
import re
import sys

SUBPOS = ('0 -43', '4 -4', '2 -4', '1.5 -4', '3.5 -41')


def text(x):
    return ''.join(''.join(r.get('text', '') for r in t.get('runs', [])) for t in (x.get('texts') or [])).replace('\n', '/').strip('/')


def main():
    flat, name, a, b, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
    d = [x for x in json.load(open(flat)) if a - 0.01 <= x['t0'] < b]
    g = {'name': name, 'length': round(b - a, 3), 'cuts': [], 'subs': [], 'cards': [], 'se': [], 'inserts': [], 'bgm': []}
    for x in d:
        t0, du = round(x['t0'] - a, 3), round(x['dur'], 3)
        st = json.dumps(x.get('styles'), ensure_ascii=False)
        lane = str(x.get('lane'))
        if x['tag'] == 'mc-clip' and x['lane'] is None:
            g['cuts'].append([t0, du])
        elif x['tag'] == 'title':
            tx = text(x)
            if not tx:
                continue
            pos = (x.get('params') or {}).get('位置', '')
            if re.search(r'\d{4}\.\d{1,2}\.\d{1,2}', tx):
                g['cards'].append([t0, du, tx, 'release'])
            elif 'Color :' in tx or 'Color:' in tx:
                g['cards'].append([t0, du, tx, 'price' if re.search(r'[¥￥]', tx) else 'product'])
            elif 'Klee' in st and pos.startswith(SUBPOS) and not re.match(r'^\d{3}cm\s*/', tx):
                g['subs'].append([t0, du, tx])
            elif re.match(r'^\d{3}cm', tx):
                g['cards'].append([t0, du, tx, 'height'])
            elif re.search(r'着丈|身幅|^(XS|S|M|L|XL)/\d', tx):
                g['cards'].append([t0, du, tx, 'sizetable'])
            elif 'Klee' in st and pos.startswith(SUBPOS):
                g['subs'].append([t0, du, tx])
            elif re.fullmatch(r'[A-Z ,/]+', tx):
                g['cards'].append([t0, du, tx, 'color'])
            else:
                g['cards'].append([t0, du, tx, 'other'])
        elif x['tag'] == 'asset-clip' and lane == '-1' and re.search(r'ボタン|決定|効果音', x['name']):
            g['se'].append([t0])
        elif x['tag'] == 'asset-clip' and lane == '-1':
            g['bgm'].append([x['name'], (x.get('adjust-volume') or {}).get('amount')])
        elif x['tag'] in ('asset-clip', 'video', 'ref-clip') and lane.lstrip('-').isdigit() and int(lane) >= 2 and 'ショート〆' not in x['name']:
            g['inserts'].append([t0, du, x['name']])
    for k in ('cuts', 'subs', 'cards', 'se', 'inserts'):
        g[k].sort()
    json.dump(g, open(out, 'w'), ensure_ascii=False, indent=1)
    print(name, {k: len(v) for k, v in g.items() if isinstance(v, list)})


if __name__ == '__main__':
    main()
