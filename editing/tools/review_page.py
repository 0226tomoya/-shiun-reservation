"""確認用ページ（HTML 1 枚）を作る。チャットの横に表示して、番号か分:秒で修正をやりとりする用。

    python3 review_page.py EDIT.fcpxml FLAT.json PLAN.json OUT.html 版

中身:
  - 概要（長さ・チェック結果・要確認と素材待ちの一覧）
  - タイムライン図
  - チャプターごとの出来事の一覧（#番号・分:秒・種類・中身）と、要所の画面の目安（素材は枠で代用）
"""
import base64
import io
import json
import os
import subprocess
import sys
import unicodedata
from html import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role, text  # noqa: E402
import preview_frames  # noqa: E402
import timeline_map  # noqa: F401,E402

HERE = os.path.dirname(os.path.abspath(__file__))
KIND = {'subtitle': '字幕', 'section_label': 'セクションラベル', 'product_center': '中央商品名', 'name_card': '名前カード',
        'collection_label': 'コレクション名（左上）', 'collection_center': 'コレクション名（中央）',
        'collection_label_center': 'コレクション名（ED 中央）', 'ed_product_name': 'ED 商品名',
        'release_date_center': '発売日（中央）'}


def norm(s):
    return unicodedata.normalize('NFC', s or '')


def mmss(t):
    return f'{int(t // 60)}:{t % 60:04.1f}'


def img_b64(im, w=640):
    im = im.resize((w, int(w * 9 / 16)))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=78)
    return base64.b64encode(buf.getvalue()).decode()


def run(args):
    return subprocess.run([sys.executable, '-I'] + args, capture_output=True, text=True).stdout.strip()


def main():
    edit, flat, plan_path, out, ver = sys.argv[1:6]
    plan = json.load(open(plan_path, encoding='utf-8'))
    items = [i for i in json.load(open(flat)) if i['enabled'] != '0' and len(i['path']) <= 1]
    total = max(i['t1'] for i in items)

    # チャプター（アイキャッチがあればその頭から）
    chs = []
    for i in items:
        for m in i.get('markers', []):
            if m['tag'] == 'chapter-marker':
                t = i['t0']  # チャプターマーカーは区間の最初のカットに付いている
                if m['value'] not in [c[1] for c in chs]:
                    chs.append((t, m['value']))
    eyes = [i['t0'] for i in items if i['lane'] is None and norm(i['name']) == 'アイキャッチ']
    bounds = [(0.0, 'OP')]
    for t, v in sorted(chs):
        e = max((x for x in eyes if t - 6 <= x <= t), default=t)
        bounds.append((e, v))
    bounds.append((total, 'END'))

    # 出来事
    ev = []
    for i in items:
        r = role(i) if i['tag'] == 'title' else None
        if i['tag'] == 'title' and r in KIND:
            ev.append((i['t0'], i['t1'], KIND[r], text(i).strip().replace('\n', ' / ')))
        elif i['lane'] is None and i['tag'] in ('ref-clip', 'asset-clip') and i['name'] != 'BGM':
            ev.append((i['t0'], i['t1'], '挿入（スパイン）', norm(i['name'])))
        elif norm(i['name']) == 'BGM':
            ev.append((i['t0'], i['t1'], 'BGM', ''))
    # インサートはかたまりにまとめる
    ins = sorted([i for i in items if i['tag'] in ('video', 'clip', 'asset-clip', 'ref-clip')
                  and i['lane'] not in (None, '-1') and not str(i['lane']).startswith('in') and int(i['lane']) >= 3],
                 key=lambda i: i['t0'])
    blocks = []
    for i in ins:
        if blocks and i['t0'] <= blocks[-1][1] + 0.01:
            blocks[-1][1] = max(blocks[-1][1], i['t1'])
            blocks[-1][2].append(i)
        else:
            blocks.append([i['t0'], i['t1'], [i]])
    for a, b, parts in blocks:
        base = [p for p in parts if p['lane'] == '3'] or parts
        names = ' → '.join(f"{norm(p['name'])}（{p['dur']:.1f}s）" for p in base[:12])
        ev.append((a, b, 'インサート', f'{len(base)} カット: {names}' + (' …' if len(base) > 12 else '')))
    ev.sort(key=lambda x: (x[0], x[2]))

    # 要確認・素材待ち
    todo = []
    for p in plan['products']:
        if p.get('_note'):
            todo.append(f"{p['chapter']}: {p['_note']}")
    for k in ('release_line', 'release_date'):
        if '要確認' in plan.get(k, ''):
            todo.append(f"発売日の表記（仮）: {plan[k]}")
    for line in plan.get('closing_lines', []):
        if '要確認' in line:
            todo.append(f'締めの字幕（仮）: {line}')
    todo += plan.get('pending', [])

    checks = run([os.path.join(HERE, 'qa_timing.py'), edit, plan.get('project', '本編')])
    score = run([os.path.join(HERE, 'evaluate_lineup.py'), flat]).split('\n')[0]
    qa = run([os.path.join(HERE, 'qa_lineup.py'), flat])

    tl = os.path.join(os.path.dirname(out), 'A24_latest_timeline.png')
    run([os.path.join(HERE, 'timeline_map.py'), flat, tl])
    tl_b64 = base64.b64encode(open(tl, 'rb').read()).decode() if os.path.exists(tl) else ''

    css = """
:root{--bg:#f6f5f2;--fg:#1d1d1f;--mut:#6b6b70;--card:#fff;--line:#e3e1dc;--acc:#8a5a2b;--sub:#c0504d;--ins:#2f6f8f;--warn:#b42318}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17181a;--fg:#ececec;--mut:#9a9aa0;--card:#202124;--line:#33343a;--acc:#d9a86c;--sub:#ff8a80;--ins:#7cc4e4;--warn:#ff8a7a}}
:root[data-theme="dark"]{--bg:#17181a;--fg:#ececec;--mut:#9a9aa0;--card:#202124;--line:#33343a;--acc:#d9a86c;--sub:#ff8a80;--ins:#7cc4e4;--warn:#ff8a7a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}
main{max-width:1100px;margin:0 auto;padding:20px 16px 60px}h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px;border-bottom:2px solid var(--fg);padding-bottom:4px}
.mut{color:var(--mut)}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
pre{white-space:pre-wrap;margin:0;font:12px/1.5 ui-monospace,Menlo,monospace}ul{margin:4px 0;padding-left:20px}.warn{color:var(--warn)}
img{max-width:100%;height:auto;border-radius:6px;display:block}.thumbs{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px;margin:8px 0}
.thumbs figure{margin:0}.thumbs figcaption{font-size:12px;color:var(--mut)}table{width:100%;border-collapse:collapse;font-size:13px}
td{border-top:1px solid var(--line);padding:4px 6px;vertical-align:top}td.n{color:var(--mut);white-space:nowrap;width:44px}td.t{white-space:nowrap;width:110px;font-variant-numeric:tabular-nums}
td.k{white-space:nowrap;width:130px}.k-字幕{color:var(--sub)}.k-インサート{color:var(--ins)}.wrap{overflow-x:auto}
.how{border-left:4px solid var(--acc)}
"""
    h = [f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
         f'<title>A24 編集確認</title><style>{css}</style></head><body><main>']
    h.append(f'<h1>A24 shiun 26 Winter 1st 編集確認（v{escape(ver)}）</h1>')
    h.append(f'<div class="mut">長さ {mmss(total)}・{escape(score)}・ファイル: editing/output/A24_latest.fcpxml</div>')
    h.append('<div class="card how"><b>修正の送り方</b>: チャットに「#番号」か「分:秒」と一言（理由があればルールにして全体に反映します）。'
             '例: 「#42 もう少し長く」「12:17 この字幕は 2 行に」。まとめて送っても大丈夫です。'
             '<div class="mut">画面の画像はテロップの位置・大きさの目安です（写真・動画は枠で代用）。</div></div>')
    h.append('<h2>要確認・素材待ち</h2><div class="card"><ul>' + ''.join(f'<li class="warn">{escape(x)}</li>' for x in todo) + '</ul></div>')
    h.append(f'<h2>チェック結果</h2><div class="card"><pre>{escape(checks)}\n\n{escape(qa)}</pre></div>')
    if tl_b64:
        h.append(f'<h2>タイムライン</h2><div class="card wrap"><img alt="タイムライン" src="data:image/png;base64,{tl_b64}"></div>')

    n = 0
    for (a, name), (b, _) in zip(bounds, bounds[1:]):
        evs = [e for e in ev if a <= e[0] < b]
        h.append(f'<h2>{escape(name)}　<span class="mut">{mmss(a)}〜{mmss(b)}</span></h2>')
        # 要所の画面: 紹介イン・最初の字幕・価格（OP/ED は数か所）
        shots = []
        subs = [e for e in evs if e[2] == '字幕']
        centers = [e for e in evs if e[2] == '中央商品名']
        if name == 'OP':
            shots = [(2.0, '名前カード'), (7.0, 'ティーザー'), (30.0, 'LOOK モンタージュ')]
        elif name == 'ED':
            shots = [(e[0] + 1, e[2]) for e in evs if e[2] in ('コレクション名（ED 中央）', '発売日（中央）', 'ED 商品名')][:3]
            if subs:
                shots.append((subs[0][0] + 1, '締めの字幕'))
        else:
            if centers:
                shots.append((centers[0][0] + 1.5, '紹介イン'))
            if subs:
                shots.append(((subs[0][0] + subs[0][1]) / 2, '最初の字幕'))
            if len(centers) > 1:
                shots.append((centers[-1][0] + 1.5, '価格'))
        if shots:
            h.append('<div class="thumbs">')
            for t, cap in shots:
                im = preview_frames.render(items, t)
                h.append(f'<figure><img alt="{escape(cap)}" src="data:image/jpeg;base64,{img_b64(im)}"><figcaption>{mmss(t)} {escape(cap)}</figcaption></figure>')
            h.append('</div>')
        h.append('<div class="card wrap"><table>')
        for e in evs:
            n += 1
            h.append(f'<tr><td class="n">#{n}</td><td class="t">{mmss(e[0])}–{mmss(e[1])}</td>'
                     f'<td class="k k-{escape(e[2])}">{escape(e[2])}</td><td>{escape(e[3])}</td></tr>')
        h.append('</table></div>')
    h.append('</main></body></html>')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(''.join(h))
    print('events', n, '->', out, f'{os.path.getsize(out) / 1e6:.1f}MB')


if __name__ == '__main__':
    main()
