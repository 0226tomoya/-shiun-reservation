"""インサートのクロップ（画面を覆えているか）と、字幕と発言の一致を調べる。

    python3 audit_inserts.py EDIT.fcpxml TRANSCRIPT.json [--subs-only]

1) 全画面のインサート（lane 3 以上の写真・動画で、2 分割・公式サイトの画面・身長別比較・紹介インの左右でないもの）:
   FCP の「収まる」（縦横比を保って画面に収める）＋拡大・位置・切り取りで、1920x1080 の画面を端まで覆えているか。
   覆えていない端（黒やすき間が出る）を px で出す。
2) 2 分割: 左右それぞれが画面の半分（960px）を覆えているか、中央を越えてはみ出していないか（左は上のレイヤーで中央で切る）。
3) 字幕: 字幕が出ている間に話している言葉と、字幕の文字がどれだけ重なるか（文字の 2 文字のかたまりの一致率）。
"""
import json
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fraction(int(a), int(b))
    return Fraction(s)


def main():
    edit, trp = sys.argv[1:3]
    v1 = sys.argv[sys.argv.index('--v1') + 1] if '--v1' in sys.argv else None
    r = ET.parse(edit).getroot()
    res = {e.get('id'): e for e in r.find('resources')}
    p = [p for p in r.iter('project') if p.get('name') == '本編'][0]
    items = []
    for e in p.find('sequence/spine'):
        o, st = T(e.get('offset')), T(e.get('start'))
        for c in e:
            if c.get('offset') is None or c.tag in ('chapter-marker', 'marker', 'keyword'):
                continue
            if e.tag == 'title':
                c.set('_inblock', '1')  # 身長別比較のブロック（スパインの調整レイヤーの中）
            items.append((float(o + T(c.get('offset')) - st), c))
    # 身長別比較のブロック（調整レイヤーの中の窓）と ED（切り抜きの並べ方）は型どおりの置き方なので対象外
    ED_T = max([t for t, c in items if (c.get('name') or '').startswith('ed_')] or [1e9]) - 10
    ch = [float(T(e.get('offset')) + T(m.get('start')) - T(e.get('start'))) for e in p.find('sequence/spine') for m in e.findall('chapter-marker') if m.get('value') == 'ED']
    if ch:
        ED_T = min(ED_T, min(ch))
    for t, c in items:
        if c.tag == 'title' and c.find('asset-clip') is not None or c.find('clip') is not None:
            pass
    blocks = [(t, t + float(T(c.get('duration')))) for t, c in items if c.tag == 'title' and any(x.tag in ('asset-clip', 'clip', 'video') for x in c)]
    for t, c in items:
        if any(a - 0.01 <= t < b for a, b in blocks) and int(c.get('lane') or 0) >= 3 and c.tag != 'title':
            if any(a - 0.01 <= t < b and (b - a) > 30 for a, b in blocks):
                c.set('_inblock', '1')
    # ---- 1・2) インサートの覆い方 ----
    by_t = {}
    for t, c in items:
        by_t.setdefault(round(t, 2), []).append(c)
    gaps = []
    for t, c in items:
        lane = int(c.get('lane') or 0)
        if lane < 3 or c.tag not in ('video', 'asset-clip', 'clip'):
            continue
        if c.get('_inblock') or t >= ED_T:
            continue
        v = c.find('video') if c.tag == 'clip' else c
        a = res.get(v.get('ref'))
        if a is None:
            continue
        f = res.get(a.get('format'))
        if f is None or not f.get('width'):
            continue
        w, h = int(f.get('width')), int(f.get('height'))
        tr = c.find('adjust-transform')
        pos = [float(x) for x in ((tr.get('position') if tr is not None else None) or '0 0').split()] if tr is not None and tr.get('position') else [0.0, 0.0]
        if tr is not None and tr.find('param') is not None:
            pos = [0.0, 0.0]  # キーフレームのパン（真ん中で見る）
        sc = float(((tr.get('scale') if tr is not None else None) or '1 1').split()[0])
        fit = min(1920 / w, 1080 / h)
        W, H = w * fit * sc, h * fit * sc
        cx, cy = 960 + pos[0] * 10.8, 540 - pos[1] * 10.8
        crop = c.find('adjust-crop/trim-rect')
        cr = {k: float(crop.get(k, 0)) * 10.8 * sc for k in ('left', 'right', 'top', 'bottom')} if crop is not None else {'left': 0, 'right': 0, 'top': 0, 'bottom': 0}
        x0, x1 = cx - W / 2 + cr['left'], cx + W / 2 - cr['right']
        y0, y1 = cy - H / 2 + cr['top'], cy + H / 2 - cr['bottom']
        name = (c.get('name') or '')
        same = by_t.get(round(t, 2), [])
        pair = sum(1 for x in same if x.tag == 'video' and int(x.get('lane') or 0) in (lane - 1, lane + 1) and x.find('adjust-transform') is not None
                   and abs(abs(float((x.find('adjust-transform').get('position') or '0 0').split()[0])) - 44.4) < 3)
        if pair and abs(abs(pos[0]) - 44.44) < 3:
            left = pos[0] < 0
            need = (0, 960) if left else (960, 1920)
            g = {'左': max(0, x0 - need[0]), '右': max(0, need[1] - x1), '上': max(0, y0), '下': max(0, 1080 - y1)}
            over = (x1 - 960) if left else 0
            kind = '2分割' + ('左' if left else '右')
        else:
            if abs(pos[0]) > 30 or w <= 1000 and h <= 1000:  # 公式サイトの画面などの置き方は別の型
                continue
            g = {'左': max(0, x0), '右': max(0, 1920 - x1), '上': max(0, y0), '下': max(0, 1080 - y1)}
            over = 0
            kind = '全画面'
        bad = {k: round(v) for k, v in g.items() if v > 0.5}
        if bad or over > 0.5:
            gaps.append((round(t, 2), kind, name, bad, round(over)))
    print(f'インサートの覆い方の問題: {len(gaps)}')
    for x in gaps[:40]:
        print('  ', x)
    # ---- 3) 字幕と発言 ----
    tr = json.load(open(trp, encoding='utf-8'))
    segs = tr['segments'] if isinstance(tr, dict) else tr
    words = [(w['start'], w['end'], w['word']) for s in segs if not s.get('removed') for w in s.get('words', [])]
    if v1:
        # 文字起こしは v1 の時刻: 素材の時刻を通して、この編集データの時刻へ写す
        vp = [q for q in ET.parse(v1).getroot().iter('project') if q.get('name') == '本編'][0]
        VS = [(float(T(e.get('offset'))), float(T(e.get('duration'))), float(T(e.get('start'))), e.get('ref')) for e in vp.find('sequence/spine') if e.tag == 'mc-clip']
        CS = [(float(T(e.get('offset'))), float(T(e.get('duration'))), float(T(e.get('start'))), e.get('ref')) for e in p.find('sequence/spine') if e.tag == 'mc-clip']

        def mp(t):
            for o, d, st, ref in VS:
                if o <= t < o + d:
                    s_ = st + t - o
                    for co, cd, cs, cr in CS:
                        if cr == ref and cs <= s_ < cs + cd:
                            return co + s_ - cs
            return t
        words = [(mp(a), mp(b), w) for a, b, w in words]
    # 本編の時刻（身長別比較の差し込みでずれた分）: マルチカムの位置から写す
    def big(s):
        return {s[i:i + 2] for i in range(len(s) - 1)}
    low = []
    for t, c in items:
        if not (c.get('name') or '').startswith('subtitle'):
            continue
        txt = ''.join(x.text or '' for x in c.iter('text-style')).replace('\n', '').replace(' ', '')
        d = float(T(c.get('duration')))
        spoken = ''.join(w for s_, e_, w in words if s_ < t + d + 0.5 and e_ > t - 1.0)
        a, b = big(txt), big(spoken)
        sim = len(a & b) / max(1, len(a))
        low.append((round(sim, 2), round(t, 2), txt[:40], spoken[:40]))
    low.sort()
    print(f'字幕 {len(low)}: 発言との一致率 0.3 未満 {sum(1 for x in low if x[0] < .3)}')
    for x in low[:15]:
        print('  ', x)


if __name__ == '__main__':
    main()
