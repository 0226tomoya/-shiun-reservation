"""longform_analyze.py の出力（完成版の部品の一覧）を、編集の「種類」ごとの出来事に分ける。再現ループの正解と採点に使う。

    python3 longform_events.py AN.json OUT.json [--print]

種類（わむうの通常の長編。A6・A8・A10・A12・A13・A15 の完成版 XML から決めた）:
  eyecatch     本線の「わむうアイキャッチ」（話の区切り）
  heading      左上の見出し（基本タイトル・位置 x −800〜−650, y 470〜490）。本編の間ずっと
  topic        見出しの下の話題の箱（座布団01_07）
  wamu         右上の WAMU（Futura）
  title_call   冒頭の題（タイプライター Klee Demibold 70）
  fact         商品の事実・要点（タイプライター Klee Demibold 30〜60、中央付近）
  opinion      わむうの感想（タイプライター hanatotyoutyo 50〜80）
  coord        コーデの一覧（背景 06 ＋ タイプライター YuGothic 30 の「Knit⏎shiun⏎…」）
  item_card    商品名・価格のカード（タイプライター YuGothic 28〜40「GU⏎3Dバレルジーンズ⏎¥2,990」）
  price        大きい価格（タイプライター Klee 150 以上「¥3,990」）
  color        色のカード（座布団01_08 か hanatotyoutyo 30「09 BLACK」）
  tsukkomi     ツッコミ（Toppan 文久見出しゴシック 150 以上・基本タイトル／タイプライター）
  shiun_card   shiun の商品名ラベル（Masqualero）
  vertical     縦書き
  channel      チャンネル紹介（ページスクロール＋Toppan 100 の基本のタイトル）
  closing      Arrivederci（Billie 01）
  sfx:<種類>   効果音（cursor・click・page・keyboard・decide・shutter・knife・scene・taiko・other）
  item_label   商品番号の箱「Item 1」（本編 クリップの複合クリップ。商品の話の間ずっと）
  insert:<種類> 映像のインサート（web＝Google Chrome の画面、cam＝撮影素材の寄り、bg＝カスタム背景、other）
  bgm          BGM（OP_bgm・BGM・ED_bgm）
  transition   本線のトランジション（ライトノイズ）
  ending       エンディングの動画
"""
import json
import re
import sys
import unicodedata


def fnt(t):
    f = t['runs'][0][1] if t['runs'] else {}
    sizes = [float(r[1].get('fontSize')) for r in t['runs'] if r[1].get('fontSize')]
    return f.get('font') or '', max(sizes) if sizes else 0


def pos(t):
    for k, v in (t.get('params') or {}).items():
        if k.startswith('位置#101'):
            try:
                x, y = map(float, v.split())
                return x, y
            except ValueError:
                pass
    return None


def title_kind(t):
    e = t['effect'] or ''
    f, sz = fnt(t)
    p = pos(t)
    if e == 'Adjustment Layer' or e.startswith('背景') and not t['text'].strip():
        return 'bg_layer' if e.startswith('背景') else None
    if f == 'Futura':
        return 'wamu'
    if e == '座布団01_07':
        # A10 は見出しを座布団で左上に出している（位置 −1581, 995・3 行）
        return 'heading' if p and p[0] < -1000 and p[1] > 900 else 'topic'
    if e == '座布団01_08' or (f == 'hanatotyoutyo' and sz <= 35):
        return 'color'
    if e == '座布団02_01':
        return 'title_bg'
    if e == 'ページスクロール':
        return None
    if e == 'Billie 01':
        return 'closing'
    if e == '縦書き':
        return 'vertical'
    if e == '基本のタイトル' and 'Toppan' in f:
        return 'channel'
    if f.startswith('Masqualero'):
        return 'shiun_card'
    if 'Toppan' in f and sz >= 150:
        return 'tsukkomi'
    if e == '基本タイトル' and p and -820 <= p[0] <= -640 and 465 <= p[1] <= 495:
        return 'heading'
    if f in ('YuGothic',) and 'Knit' in t['text'] or re.match(r'^(Knit|Pants|Shirt|Coat|Jacket|Blouson|Outer|Tops|Shoes|Inner)\n', t['text']):
        return 'coord'
    if f == 'YuGothic' and e == 'タイプライター' and sz <= 45:
        return 'item_card'
    if f == 'Klee' and sz >= 150:
        return 'price'
    if f == 'Klee' and sz >= 65 and e == 'タイプライター':
        return 'title_call'
    if f == 'Klee' and e == 'タイプライター':
        return 'fact'
    if f == 'hanatotyoutyo':
        return 'opinion'
    if 'Toppan' in f:
        return 'tsukkomi'
    return 'other_title'


def sfx_kind(n):
    for k, pats in (('cursor', ('カーソル',)), ('click', ('クリック',)), ('page', ('ページめくり', 'Book, Directory')), ('keyboard', ('Keyboard', 'キーボード')),
                    ('decide', ('決定ボタン',)), ('shutter', ('シャッター',)), ('knife', ('ナイフ',)), ('scene', ('シーン切り替え',)), ('taiko', ('太鼓',))):
        if any(p in n for p in pats):
            return k
    return 'other'


def main():
    R = json.load(open(sys.argv[1]))
    ev = []
    for t in R['titles']:
        t['text'] = unicodedata.normalize('NFC', t['text'])
        k = title_kind(t)
        if k:
            ev.append({'kind': k, 'start': round(t['start'], 3), 'end': round(t['end'], 3), 'text': t['text'], 'lane': t['lane']})
    for c in R['clips']:
        n = unicodedata.normalize('NFC', c['ref_name'] or c['name'] or '')
        if re.search(r'BGM|bgm', n):
            k = 'bgm'
        elif (c['kind'] in ('asset-clip', 'ref-clip', 'audio') and c['lane'] < 0) or (sfx_kind(n) != 'other' and c['kind'] != 'video'):
            k = 'sfx:' + sfx_kind(n)
        elif n.startswith('本編 クリップ') and c['kind'] == 'ref-clip':
            k = 'item_label'  # 「Item 1」の箱（座布団）を入れた複合クリップ。商品ごとに本編の間ずっと
        elif 'クリップ' in n and c['kind'] == 'ref-clip':
            k = 'insert:other'
        elif 'Google Chrome' in n or 'fullpage' in n or 'thumbnail' in n:
            k = 'insert:web'
        elif re.match(r'^\d{8}_[A-Za-z]\d+', n):
            k = 'insert:cam'
        elif n == 'カスタム':
            k = 'insert:bg'
        elif '冒頭プロフィール' in n or 'OPスナップ' in n:
            k = 'op_profile'
        else:
            k = 'insert:other'
        ev.append({'kind': k, 'start': round(c['start'], 3), 'end': round(c['end'], 3), 'text': n, 'lane': c['lane']})
    for x in R['spine']:
        if 'アイキャッチ' in (x['name'] or ''):
            ev.append({'kind': 'eyecatch', 'start': round(x['start'], 3), 'end': round(x['end'], 3), 'text': x['name'], 'lane': 0})
        elif x['kind'] == 'transition':
            ev.append({'kind': 'transition', 'start': round(x['start'], 3), 'end': round(x['end'], 3), 'text': x['name'], 'lane': 0})
        elif x['name'] == 'エンディング':
            ev.append({'kind': 'ending', 'start': round(x['start'], 3), 'end': round(x['end'], 3), 'text': x['name'], 'lane': 0})
    # 同じ文の見出し・WAMU は、本線のカットごとに切れているので 1 本につなぐ
    merged = []
    for e in sorted(ev, key=lambda e: (e['kind'], e['start'])):
        if merged and e['kind'] in ('heading', 'wamu', 'topic', 'bgm', 'item_label') and merged[-1]['kind'] == e['kind'] and merged[-1]['text'] == e['text'] \
                and e['start'] - merged[-1]['end'] < 2.0:
            merged[-1]['end'] = max(merged[-1]['end'], e['end'])
            continue
        merged.append(dict(e))
    merged.sort(key=lambda e: e['start'])
    json.dump({'duration': R['duration'], 'events': merged}, open(sys.argv[2], 'w'), ensure_ascii=False, indent=0)
    if '--print' in sys.argv:
        for e in merged:
            print(f"{e['start']:7.1f}-{e['end']:7.1f} {e['kind']:14s} {e['text'][:50]!r}")
    from collections import Counter
    print(dict(Counter(e['kind'] for e in merged)))


if __name__ == '__main__':
    main()
