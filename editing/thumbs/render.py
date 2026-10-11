"""サムネの再現: 仕様（JSON）→ 1280x720 の画像、元のサムネとの採点。

    python3 render.py SPEC.json [--orig ORIG.jpg] [--out OUT_DIR]

仕様:
{
  "id": "動画ID",
  "erase": [[x, y, w, h], ...],        # 元の文字・図形がある範囲（背景を作るときに消す。漏れなく全部）
  "layers": [ ... 下から順 ... ]
}
レイヤー:
  text:  {"type":"text","text":"絶対\\n買い","x":40,"y":60,           # 左上（anchor で変更可）
          "anchor":"lt|ct|rt|lb|cb|rb|cc", "font":"Noto Sans JP","weight":900,"size":150,
          "color":"#fff" または "fill":"linear-gradient(180deg,#fff7c2,#d4a020)",
          "strokes":[[12,"#000"],[22,"#fff"]],   # 内側から外側へ（太さ px, 色）
          "shadow":"6px 6px 0 rgba(0,0,0,.6)", "spacing":0.0(em), "line":1.1, "rotate":0, "skew":0,
          "scale_x":1.0, "vertical":false, "italic":false, "align":"left", "opacity":1,
          "runs":[{"text":"低身長","color":"#ff0","size":120}, ...]  # 部分ごとに色・大きさを変えるとき（text の代わり）
         }
  rect:  {"type":"rect","x":..,"y":..,"w":..,"h":..,"fill":"#000","opacity":0.6,"radius":0,"rotate":0,
          "border":[4,"#fff"], "skew":0}
  image: {"type":"image","src":"assets/logos/uniqlo.png","x":..,"y":..,"w":..,"h":..,"rotate":0,"opacity":1}
  line:  {"type":"line","x1":..,"y1":..,"x2":..,"y2":..,"width":6,"color":"#f00"}
  "hollow": true で中を塗らない縁だけの文字（strokes の 1 つ目の太さ・色が線）
  erase の要素 {"rect":[..],"by":"layers"} は、色ではなく描いた文字の形で消す（白文字の範囲の白い服を守る。ただし形がずれると元の文字が残る）
  （runs の各要素は size_em で行の size に対する倍率も書ける）
"front": [[[x,y],...], ...]   # 文字より前にある人物などの多角形。中は元の画素をそのまま上に戻す
背景 = 元のサムネから erase の範囲と描いたレイヤーの範囲を消して埋めたもの（cv2.inpaint）。人物・写真は元のまま。
採点 = 消した範囲（＝文字・図形の部分）での一致度（SSIM と色の差）。100 点満点。
"""
import base64
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get('THUMB_FONTS', os.path.expanduser('~/.fonts'))
W, H = 1280, 720


_FONT_CACHE = {}


def font_css(families):
    """使うファミリーだけ、全ウェイトを data URI で埋め込む（file:// は読まれないため）。"""
    out = []
    have = {}
    for fn in sorted(os.listdir(FONT_DIR)):
        if fn.endswith('.ttf'):
            name, w = fn[:-4].rsplit('-', 1)
            have.setdefault(name, []).append(int(w))
    want = set()
    for name, w in families:
        ws = have.get(name)
        if ws:  # その太さが無ければ一番近い太さ
            want.add(f"{name}-{min(ws, key=lambda x: abs(x - w))}.ttf")
    for fn in sorted(want):
        name, w = fn[:-4].rsplit('-', 1)
        if fn not in _FONT_CACHE:
            _FONT_CACHE[fn] = base64.b64encode(open(os.path.join(FONT_DIR, fn), 'rb').read()).decode()
        out.append(f"@font-face{{font-family:'{name}';font-weight:{w};src:url(data:font/ttf;base64,{_FONT_CACHE[fn]}) format('truetype');}}")
    return '\n'.join(out)


def families_of(spec):
    """使う (ファミリー, 太さ) だけ（全ウェイトを埋め込むとブラウザが落ちることがある）。"""
    f = set()
    for L in spec.get('layers', []):
        if L.get('type') == 'text':
            fam_ = L.get('font', 'Noto Sans JP').replace(' ', '')
            w = int(L.get('weight', 900))
            f.add((fam_, w))
            for r in L.get('runs') or []:
                f.add(((r.get('font') or fam_).replace(' ', ''), int(r.get('weight', w))))
    return f


def available_fonts():
    return sorted({fn[:-4].rsplit('-', 1)[0] for fn in os.listdir(FONT_DIR) if fn.endswith('.ttf')})


def fam(f):
    return "'" + f.replace(' ', '') + "'"


def text_html(L, i):
    sw = L.get('strokes') or []
    size = L.get('size', 80)
    base = (f"font-family:{fam(L.get('font', 'Noto Sans JP'))},'Noto Sans CJK JP';font-weight:{L.get('weight', 900)};"
            f"font-size:{size}px;line-height:{L.get('line', 1.1)};letter-spacing:{L.get('spacing', 0)}em;"
            f"white-space:pre;text-align:{L.get('align', 'left')};"
            + ("font-style:italic;" if L.get('italic') else '')
            + ("writing-mode:vertical-rl;text-orientation:upright;" if L.get('vertical') else ''))

    def content(color_css):
        if L.get('runs'):
            s = ''
            for k_, r in enumerate(L['runs']):
                st = ''
                if r.get('size_em'):
                    st += f"font-size:{r['size_em']}em;"
                elif r.get('size'):
                    st += f"font-size:{r['size']}px;"
                if r.get('font'):
                    st += f"font-family:{fam(r['font'])};"
                if r.get('weight'):
                    st += f"font-weight:{r['weight']};"
                if color_css is None:
                    if r.get('fill') or (L.get('fill') and not r.get('color')):
                        r = dict(r, fill=r.get('fill') or L.get('fill'))
                        st += f"background:{r['fill']};-webkit-background-clip:text;color:transparent;"
                    else:
                        st += f"color:{r.get('color', L.get('color', '#fff'))};"
                s += f"<span data-k=\"{k_}\" style=\"{st}\">{esc(r['text'])}</span>"
            return s
        return esc(L.get('text', ''))

    tf = []
    if L.get('rotate'):
        tf.append(f"rotate({L['rotate']}deg)")
    if L.get('skew'):
        tf.append(f"skewX({L['skew']}deg)")
    if L.get('scale_x', 1) != 1 or L.get('scale_y', 1) != 1:
        tf.append(f"scale({L.get('scale_x', 1)},{L.get('scale_y', 1)})")
    anc = L.get('anchor', 'lt')
    ox = {'l': '0', 'c': '-50%', 'r': '-100%'}[anc[0]]
    oy = {'t': '0', 'c': '-50%', 'b': '-100%'}[anc[1]]
    origin = {'l': 'left', 'c': 'center', 'r': 'right'}[anc[0]] + ' ' + {'t': 'top', 'c': 'center', 'b': 'bottom'}[anc[1]]
    wrap = (f"position:absolute;left:{L['x']}px;top:{L['y']}px;transform:translate({ox},{oy}) {' '.join(tf)};"
            f"transform-origin:{origin};opacity:{L.get('opacity', 1)};")
    layers = ''
    # 外側の縁取りから順に重ねる（paint-order で文字の外側だけに出す）
    acc = 0
    widths = []
    for w, c in sw:
        acc += w
        widths.append((acc, c))
    hollow = L.get('hollow')
    for w, c in reversed(widths):
        if hollow:  # 中を塗らない縁だけの文字（「？」の線画など）: 縁の太さ w をそのまま線の太さに
            layers += (f"<div style=\"{base}position:absolute;left:0;top:0;color:transparent;-webkit-text-stroke:{w}px {c};\">{content('transparent')}</div>")
            continue
        layers += (f"<div style=\"{base}position:absolute;left:0;top:0;color:{c};-webkit-text-stroke:{2 * w}px {c};"
                   f"paint-order:stroke fill;\">{content(c)}</div>")
    if L.get('shadow') and not sw:
        sh = f"text-shadow:{L['shadow']};"
    else:
        sh = ''
    if L.get('shadow') and sw:
        # 影は一番外側の縁取りに付ける
        layers = layers.replace('paint-order:stroke fill;', f"paint-order:stroke fill;filter:drop-shadow({L['shadow']});", 1)
    fill = L.get('fill')
    if hollow:
        top = f"<div style=\"{base}position:relative;color:transparent;\">{content('transparent')}</div>"
    elif fill and not L.get('runs'):
        under = (f"<div style=\"{base}position:absolute;left:0;top:0;color:transparent;{sh}\">{content('transparent')}</div>" if sh else '')
        top = under + f"<div style=\"{base}position:relative;background:{fill};-webkit-background-clip:text;color:transparent;\">{content(None)}</div>"
    else:
        top = f"<div style=\"{base}position:relative;color:{L.get('color', '#fff')};{sh}\">{content(None)}</div>"
    return f"<div id=\"L{i}\" style=\"{wrap}\">{layers}{top}</div>"


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def layer_html(L, i):
    t = L['type']
    rot = f"transform:rotate({L.get('rotate', 0)}deg) skewX({L.get('skew', 0)}deg);"
    if t == 'text':
        return text_html(L, i)
    if t == 'rect':
        b = L.get('border')
        bs = f"border:{b[0]}px solid {b[1]};box-sizing:border-box;" if b else ''
        return (f"<div id=\"L{i}\" style=\"position:absolute;left:{L['x']}px;top:{L['y']}px;width:{L['w']}px;height:{L['h']}px;"
                f"background:{L.get('fill', 'transparent')};opacity:{L.get('opacity', 1)};border-radius:{L.get('radius', 0)}px;{bs}{rot}\"></div>")
    if t == 'image':
        p = L['src'] if os.path.isabs(L['src']) else os.path.join(HERE, L['src'])
        mime = 'image/png' if p.lower().endswith('.png') else 'image/jpeg'
        uri = f"data:{mime};base64," + base64.b64encode(open(p, 'rb').read()).decode()
        return (f"<img id=\"L{i}\" src=\"{uri}\" style=\"position:absolute;left:{L['x']}px;top:{L['y']}px;width:{L['w']}px;"
                f"height:{L.get('h', 'auto') if isinstance(L.get('h'), str) else str(L.get('h')) + 'px'};opacity:{L.get('opacity', 1)};{rot}\">")
    if t == 'line':
        x1, y1, x2, y2 = L['x1'], L['y1'], L['x2'], L['y2']
        ln = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5
        ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        return (f"<div id=\"L{i}\" style=\"position:absolute;left:{x1}px;top:{y1 - L.get('width', 6) / 2}px;width:{ln}px;height:{L.get('width', 6)}px;"
                f"background:{L.get('color', '#f00')};transform:rotate({ang}deg);transform-origin:0 50%;\"></div>")
    raise ValueError(t)


_LOADED = {}


def render_layers(spec, page, clip=None):
    """ページにはフォントを一度だけ読み込み、以後は中身だけ差し替える（毎回フォントを埋め込むと遅い）。"""
    fams = families_of(spec)
    st = _LOADED.setdefault(id(page), {'fams': set(), 'ready': False})
    if not st['ready']:
        page.set_content(f"<html><head><style>html,body{{margin:0;width:{W}px;height:{H}px;"
                         f"overflow:hidden;background:transparent;}}</style></head><body><div id=root></div></body></html>")
        st['ready'] = True
    new = fams - st['fams']
    if new:
        page.evaluate("css => { const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s); }",
                      font_css(new))
        st['fams'] |= new
    body = ''.join(layer_html(L, i) for i, L in enumerate(spec.get('layers', [])))
    page.evaluate("html => { document.getElementById('root').innerHTML = html; }", body)
    page.evaluate('document.fonts.ready.then(() => 1)')
    if clip:  # (x0, y0, x1, y1) の範囲だけ撮って全体の大きさの画像に戻す（fit を速くする）
        x0, y0, x1, y1 = [int(v) for v in clip]
        png = page.screenshot(omit_background=True, clip={'x': x0, 'y': y0, 'width': x1 - x0, 'height': y1 - y0})
        part = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
        im = np.zeros((H, W, 4), np.uint8)
        im[y0:y0 + part.shape[0], x0:x0 + part.shape[1]] = part[:H - y0, :W - x0]
        return im
    png = page.screenshot(omit_background=True, clip={'x': 0, 'y': 0, 'width': W, 'height': H})
    im = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
    return im  # BGRA


def hex2bgr(c):
    c = c.strip()
    if c.startswith('#'):
        c = c[1:]
        if len(c) == 3:
            c = ''.join(ch * 2 for ch in c)
        return (int(c[4:6], 16), int(c[2:4], 16), int(c[0:2], 16))
    m = __import__('re').findall(r'[\d.]+', c)
    if c.startswith('rgb') and len(m) >= 3:
        return (float(m[2]), float(m[1]), float(m[0]))
    return None


def layer_colors(spec):
    import re
    cols = []
    for L in spec.get('layers', []):
        for k in ('color', 'fill'):
            v = L.get(k)
            if isinstance(v, str):
                for c in re.findall(r'#[0-9a-fA-F]{3,6}|rgba?\([^)]*\)', v):
                    cols.append(c)
        for w, c in L.get('strokes') or []:
            cols.append(c)
        for r in L.get('runs') or []:
            for k in ('color', 'fill'):
                if isinstance(r.get(k), str):
                    cols += re.findall(r'#[0-9a-fA-F]{3,6}|rgba?\([^)]*\)', r[k])
    out = []
    for c in cols:
        b = hex2bgr(c)
        if b is not None and b not in out:
            out.append(b)
    return out


def erase_mask(spec, orig, alpha=None):
    mask = np.zeros((H, W), np.uint8)
    raw = np.zeros((H, W), bool)  # 元の文字の画素（広げる前）＝形の一致を見る相手
    lab = cv2.cvtColor(orig, cv2.COLOR_BGR2LAB).astype(np.float32)
    default_cols = layer_colors(spec)
    for e in spec.get('erase', []):
        if isinstance(e, dict):
            x, y, w, h = e['rect']
            full = e.get('full', False)
            cols = [hex2bgr(c) for c in e.get('colors', [])] or default_cols
            tol = e.get('tol', 28)
        else:
            x, y, w, h = e
            full, cols, tol = False, default_cols, 28
        x, y, w, h = int(max(0, x)), int(max(0, y)), int(w), int(h)
        if isinstance(e, dict) and e.get('by') == 'layers' and alpha is not None:
            a = (alpha[y:y + h, x:x + w] > 8).astype(np.uint8) * 255
            g = int(e.get('grow', spec.get('grow', 11)))
            mask[y:y + h, x:x + w] = np.maximum(mask[y:y + h, x:x + w], cv2.dilate(a, np.ones((g, g), np.uint8)))
            raw[y:y + h, x:x + w] |= alpha[y:y + h, x:x + w] > 128
            continue
        if full or not cols:
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
            raw[y:y + h, x:x + w] = True
            continue
        sub = lab[y:y + h, x:x + w]
        m = np.zeros(sub.shape[:2], bool)
        for c in cols:
            cl = cv2.cvtColor(np.uint8([[c]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
            m |= np.linalg.norm(sub - cl, axis=2) < tol
        g = int(spec.get('grow', 11))
        mm = cv2.dilate(m.astype(np.uint8) * 255, np.ones((g, g), np.uint8))
        mask[y:y + h, x:x + w] = np.maximum(mask[y:y + h, x:x + w], mm)
        raw[y:y + h, x:x + w] |= m
    erase_mask.raw = raw
    return mask


def compose(spec, orig_bgr, rgba):
    mask = erase_mask(spec, orig_bgr, rgba[:, :, 3])
    alpha = rgba[:, :, 3]
    drawn = cv2.dilate((alpha > 8).astype(np.uint8) * 255, np.ones((5, 5), np.uint8))
    mask = cv2.bitwise_or(mask, drawn)
    bg = cv2.inpaint(orig_bgr, mask, 5, cv2.INPAINT_TELEA) if mask.any() else orig_bgr.copy()
    a = (alpha.astype(np.float32) / 255)[:, :, None]
    out = (rgba[:, :, :3].astype(np.float32) * a + bg.astype(np.float32) * (1 - a)).astype(np.uint8)
    keep = np.zeros((H, W), np.uint8)
    for poly in spec.get('front', []):  # 文字より前にある人物など: [[x,y],...] の多角形
        cv2.fillPoly(keep, [np.array(poly, np.int32)], 255)
    if keep.any():
        out[keep > 0] = orig_bgr[keep > 0]
        rgba[keep > 0, 3] = 0
        if hasattr(erase_mask, 'raw'):
            erase_mask.raw[keep > 0] = False
    return out, mask, bg


def score(orig, out, mask):
    if mask.mean() < 0.002 * 255:
        return 0.0, {'note': '文字の範囲がほぼ無い'}
    g1 = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    _, smap = ssim(g1, g2, full=True, data_range=255)
    m = mask > 0
    s = float(smap[m].mean())
    lab1 = cv2.cvtColor(orig, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab2 = cv2.cvtColor(out, cv2.COLOR_BGR2LAB).astype(np.float32)
    de = float(np.linalg.norm(lab1 - lab2, axis=2)[m].mean())
    col = max(0.0, 1 - de / 40)
    total = 100 * (0.7 * max(0.0, s) + 0.3 * col)
    return round(total, 1), {'ssim': round(s, 3), 'deltaE': round(de, 1), 'area': round(float(m.mean()), 3)}


def run(spec_path, orig_path, out_dir, page):
    spec = json.load(open(spec_path))
    orig = cv2.resize(cv2.imread(orig_path), (W, H))
    rgba = render_layers(spec, page)
    out, mask, bg = compose(spec, orig, rgba)
    sc, det = score(orig, out, mask)
    A = rgba[:, :, 3] > 128
    Tm = getattr(erase_mask, 'raw', np.zeros_like(A))
    uni = (A | Tm).sum()
    iou = float((A & Tm).sum() / uni) if uni else 0.0
    det['iou'] = round(iou, 3)
    det['region'] = sc
    sc = round(100 * (0.5 * iou) + 0.5 * sc, 1)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, spec['id'])
    cv2.imwrite(base + '_render.png', out)
    # 確認用: 上 元 / 下 再現、右に差の強さ
    diff = cv2.absdiff(orig, out)
    diff = cv2.applyColorMap(cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY) * 3, cv2.COLORMAP_INFERNO)
    side = np.vstack([np.hstack([orig, bg]), np.hstack([out, diff])])
    cv2.imwrite(base + '_compare.jpg', cv2.resize(side, (1280, 720)), [cv2.IMWRITE_JPEG_QUALITY, 85])
    res = {'id': spec['id'], 'score': sc, **det}
    json.dump(res, open(base + '_score.json', 'w'))
    return res


def main():
    from playwright.sync_api import sync_playwright
    specs = [a for a in sys.argv[1:] if a.endswith('.json')]
    orig_dir = os.environ.get('THUMB_ORIG', os.path.join(HERE, 'orig'))
    out_dir = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(HERE, 'out')
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
                              args=['--allow-file-access-from-files'])
        page = b.new_page(viewport={'width': W, 'height': H})
        for sp in specs:
            sid = json.load(open(sp))['id']
            r = run(sp, os.path.join(orig_dir, sid + '.jpg'), out_dir, page)
            print(json.dumps(r, ensure_ascii=False))
        b.close()


if __name__ == '__main__':
    main()
