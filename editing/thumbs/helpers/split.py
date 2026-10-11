"""Split text layer(s) into per-character layers at their rendered positions.
python3 split.py ID i[,j...]
"""
import json, os, sys
import numpy as np
TH = '/home/user/-shiun-reservation/editing/thumbs'
sys.path.insert(0, TH)
import render as R

vid = sys.argv[1]
idx = [int(v) for v in sys.argv[2].split(',')]
sp = os.path.join(TH, 'specs', vid + '.json')
spec = json.load(open(sp))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args=['--allow-file-access-from-files'])
    page = b.new_page(viewport={'width': R.W, 'height': R.H})
    new_layers = []
    for i, L in enumerate(spec['layers']):
        if i not in idx or L['type'] != 'text' or L.get('vertical'):
            new_layers.append(L); continue
        runs = L.get('runs') or [{'text': L['text']}]
        chars = []
        for r in runs:
            for ch in r['text']:
                chars.append(dict(r, text=ch))
        L2 = dict(L); L2.pop('text', None); L2['runs'] = chars; L2['rotate'] = 0
        s = {'id': vid, 'layers': [L2]}
        R.render_layers(s, page)
        rects = page.evaluate("() => Array.from(document.querySelectorAll('#L0 > div:last-child span')).map(e => {const r=e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]})")
        base = {k: v for k, v in L.items() if k not in ('runs', 'text', 'x', 'y', 'anchor', 'spacing', 'size')}
        for ch, rc in zip(chars, rects):
            if not ch['text'].strip():
                continue
            sz = L.get('size', 80) * ch.get('size_em', 1) if not ch.get('size') else ch['size']
            n = dict(base)
            n.update({'text': ch['text'], 'x': round(rc[0], 1), 'y': round(rc[1] + rc[3] / 2, 1), 'anchor': 'lc', 'size': round(sz, 1), 'scale_x': 1.0 if True else L.get('scale_x', 1)})
            # scale_x is baked into rect width; keep glyph scale
            n['scale_x'] = L.get('scale_x', 1)
            for k in ('color', 'fill', 'font', 'weight', 'strokes'):
                if k in ch and k != 'text':
                    n[k] = ch[k]
            n['line'] = 1.0
            new_layers.append(n)
    b.close()
spec['layers'] = new_layers
json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
print(len(new_layers), 'layers')
