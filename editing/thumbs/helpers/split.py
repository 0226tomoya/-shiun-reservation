"""Split text layer(s) into per-character layers at their rendered positions.
python3 split.py ID i[,j...] [--words]
--words: 1 字ずつではなく空白で区切った語ごとに分ける（size 40 未満の小さい英字の行など、1 字ずつだと崩れる行）。
回転（rotate）・斜体（skew）の行も、変形をかけたまま 1 字ずつに分ける（anchor cc）。
分けた字には "grp"（元のレイヤー番号）を付ける → helpers/tune_group.py で行ごとに動かせる。
縦書き（"vertical": true）のレイヤーも 1 字ずつに分ける（縦書きのまま、anchor cc）。
"""
import json, os, re, sys
import numpy as np
TH = '/home/user/-shiun-reservation/editing/thumbs'
sys.path.insert(0, TH)
import render as R

vid = sys.argv[1]
idx = [int(v) for v in sys.argv[2].split(',')]
WORDS = '--words' in sys.argv  # 空白で区切って語ごとに分ける（小さい英字の行など）
sp = os.path.join(TH, 'specs', vid + '.json')
spec = json.load(open(sp))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args=['--allow-file-access-from-files'])
    page = b.new_page(viewport={'width': R.W, 'height': R.H})
    new_layers = []
    for i, L in enumerate(spec['layers']):
        if i not in idx or L['type'] != 'text':
            new_layers.append(L); continue
        runs = L.get('runs') or [{'text': L['text']}]
        chars = []
        ln = 0
        for r in runs:
            if WORDS:
                for w in re.split(r'([ \u3000\n])', r['text']):
                    if w:
                        chars.append(dict(r, text=w, _ln=ln))
                    if w == '\n':
                        ln += 1
                continue
            for ch in r['text']:
                chars.append(dict(r, text=ch, _ln=ln))
                if ch == '\n':
                    ln += 1
        L2 = dict(L); L2.pop('text', None); L2['runs'] = chars
        tilted = bool(L.get('rotate') or L.get('skew') or L.get('skew_y'))
        if not tilted:
            L2['rotate'] = 0
        s = {'id': vid, 'layers': [L2]}
        R.render_layers(s, page)
        rects = page.evaluate("() => Array.from(document.querySelectorAll('#L0 > div:last-child span')).map(e => {const r=e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]})")
        base = {k: v for k, v in L.items() if k not in ('runs', 'text', 'x', 'y', 'anchor', 'spacing', 'size')}
        for ch, rc in zip(chars, rects):
            if not ch['text'].strip():
                continue
            sz = L.get('size', 80) * ch.get('size_em', 1) if not ch.get('size') else ch['size']
            n = dict(base)
            if tilted:  # 回転・斜体: 変形込みで描いた字の外接矩形の中心（＝変形後の字の中心）に置き、同じ変形を 1 字ずつにかける
                n.update({'text': ch['text'], 'x': round(rc[0] + rc[2] / 2, 1), 'y': round(rc[1] + rc[3] / 2, 1), 'anchor': 'cc', 'size': round(sz, 1)})
            elif L.get('vertical'):  # 縦書き: 1 字ずつ縦書きのまま、字の中心に置く（ー・括弧の向きを保つ）
                n.update({'text': ch['text'], 'x': round(rc[0] + rc[2] / 2, 1), 'y': round(rc[1] + rc[3] / 2, 1), 'anchor': 'cc', 'size': round(sz, 1)})
            else:
                n.update({'text': ch['text'], 'x': round(rc[0], 1), 'y': round(rc[1] + rc[3] / 2, 1), 'anchor': 'lc', 'size': round(sz, 1)})
            # scale_x is baked into rect width; keep glyph scale
            n['scale_x'] = L.get('scale_x', 1)
            for k in ('color', 'fill', 'font', 'weight', 'strokes'):  # _ln は持ち込まない
                if k in ch and k != 'text':
                    n[k] = ch[k]
            n['line'] = 1.0
            n['grp'] = (L.get('grp') or f'L{i}') + (f"_{ch['_ln']}" if ch['_ln'] else '')  # 同じ行の字（tune_group.py でまとめて動かす）
            new_layers.append(n)
    b.close()
spec['layers'] = new_layers
json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
print(len(new_layers), 'layers')
