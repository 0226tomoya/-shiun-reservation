"""対談・トーク動画（横 16:9）のカット済み XML に、テロップ（右上の WAMU・左上の見出し・フルテロップ）を重ねる。本線は 1 コマも変えない。
    python3 talk_overlay.py BASE.fcpxml OVERLAY.json OUT.fcpxml

OVERLAY.json:
  {"wamu": true,
   "headings": [{"start": 秒, "end": 秒, "line1": "見出し", "line2": "小さい 2 行目（無ければ空）"}],
   "subs": [{"start": 秒, "end": 秒, "text": "テロップ", "speaker": "wamu|guest"}],
   "pins": [{"at": 秒, "note": "人の判断が要る所"}]}
時刻はタイムライン（プロジェクトの頭から）の秒。
見た目（Paste の値。`editing/PASTE_DATABASE.md`・`editing/components/Paste_AI用テンプレ.fcpxml`）:
  WAMU   : 基本タイトル・Futura MediumItalic「WAMU」68 ／「164cm / 58kg」33・中央揃え・行間 −10・位置 813.9, 440.4（右上）・全編・lane 5
  見出し : 基本タイトル・Masqualero bold 40 ／ 25・左揃え・行間 −5・位置 −956.953, 485.985（左上）・縮小 0.9・lane 4
  字幕   : 基本タイトル・Klee Medium 32・白・字間 1.6・中央揃え・位置 1, −483.734（下）・lane 3。最後の 1 字は字間なしの別の text-style
  縁取り（strokeColor）は XML では書かない（ユーザーの決め。FCP 側のテンプレで付ける）
"""
import copy
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr

BASIC = '.../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti'
KEY_POS = '9999/999166631/999166633/1/100/101'
KEY_SCALE = '9999/999166631/999166633/1/100/105'
KEY_FLAT = '9999/999166631/999166633/2/351'
KEY_ALIGN = '9999/999166631/999166633/2/354/999169573/401'
KEY_LS = '9999/999166631/999166633/2/354/999169573/404'


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fr(int(a), int(b))
    return Fr(s)


def ts(f):
    f = Fr(f)
    return f'{f.numerator}s' if f.denominator == 1 else f'{f.numerator}/{f.denominator}s'


class Overlay:
    def __init__(self, root):
        self.root = root
        res = root.find('resources')
        self.res = res
        seq = root.find('.//project/sequence')
        fmt = next(f for f in res.findall('format') if f.get('id') == seq.get('format'))
        self.fd = T(fmt.get('frameDuration'))
        self.spine = seq.find('spine')
        self.items = [(T(c.get('offset')), T(c.get('duration')), c) for c in self.spine]
        eff = next((e for e in res.findall('effect') if e.get('uid') == BASIC), None)
        if eff is None:
            ids = {e.get('id') for e in res}
            n = 1
            while f'r{n}' in ids:
                n += 1
            eff = ET.SubElement(res, 'effect', {'id': f'r{n}', 'name': '基本タイトル', 'uid': BASIC})
        self.eff = eff.get('id')
        self.tsn = 0

    def fr(self, t):
        return Fr(round(Fr(t) / self.fd)) * self.fd

    def host(self, t):
        t = self.fr(t)
        for off, du, c in self.items:
            if off <= t < off + du:
                return c, T(c.get('start')) + (t - off)
        off, du, c = self.items[-1]
        return c, T(c.get('start')) + (t - off)

    def tsid(self):
        self.tsn += 1
        return f'tov{self.tsn}'

    def title(self, t0, t1, lane, name, params, runs, transform=None):
        """runs: [(文字, text-style の属性)]"""
        c, local = self.host(t0)
        dur = max(self.fd, self.fr(t1) - self.fr(t0))
        e = ET.Element('title', {'ref': self.eff, 'lane': str(lane), 'offset': ts(local), 'name': name, 'start': '3600s', 'duration': ts(dur)})
        for k, v, key in params:
            ET.SubElement(e, 'param', {'name': k, 'key': key, 'value': v})
        tx = ET.SubElement(e, 'text')
        defs = []
        for s, attrs in runs:
            i = self.tsid()
            r = ET.SubElement(tx, 'text-style', {'ref': i}); r.text = s
            defs.append((i, attrs))
        for i, attrs in defs:
            d = ET.SubElement(e, 'text-style-def', {'id': i})
            ET.SubElement(d, 'text-style', attrs)
        if transform:
            ET.SubElement(e, 'adjust-transform', transform)
        # mc-clip の子の順番（DTD）: adjust-*, mc-source の後、marker・filter-audio の前
        kids = list(c)
        pos = len(kids)
        for j, k in enumerate(kids):
            if k.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker', 'filter-video', 'filter-video-mask', 'filter-audio', 'metadata'):
                pos = j
                break
        c.insert(pos, e)
        return e

    def marker(self, t, note):
        c, local = self.host(t)
        kids = list(c)
        pos = len(kids)
        for j, k in enumerate(kids):
            if k.tag in ('filter-video', 'filter-video-mask', 'filter-audio', 'metadata'):
                pos = j
                break
        c.insert(pos, ET.Element('marker', {'start': ts(local), 'duration': ts(self.fd), 'value': '要判断: ' + note, 'completed': '0'}))


def main():
    base, ovp, out = sys.argv[1:4]
    head = open(base, encoding='utf-8').read(400)
    tree = ET.parse(base)
    root = tree.getroot()
    o = Overlay(root)
    ov = json.load(open(ovp))
    total = sum(du for _, du, _ in o.items)
    if ov.get('wamu'):
        st = {'font': 'Futura', 'fontFace': 'Medium Italic', 'fontColor': '1 1 1 1', 'alignment': 'center', 'lineSpacing': '-10',
              'shadowColor': '0 0 0 0.5', 'shadowOffset': '5 315', 'shadowBlurRadius': '10'}
        o.title(0, total, 5, 'WAMU - 基本タイトル',
                [('位置', '813.9 440.4', KEY_POS), ('平坦化', '1', KEY_FLAT), ('配置', '1 (水平方向に中央揃え)', KEY_ALIGN), ('行間', '-10', KEY_LS)],
                [('WAMU\n', {**st, 'fontSize': '68'}), ('164cm / 58kg', {**st, 'fontSize': '33'})])
    for h in ov.get('headings', []):
        st = {'font': 'Masqualero', 'fontColor': '1 1 1 1', 'bold': '1', 'lineSpacing': '-5', 'alignment': 'left'}
        runs = [(h['line1'] + ('\n' if h.get('line2') else ''), {**st, 'fontSize': '40'})]
        if h.get('line2'):
            runs.append((h['line2'], {**st, 'fontSize': '25'}))
        o.title(h['start'], h['end'], 4, h['line1'][:20] + ' - 基本タイトル',
                [('位置', '-956.953 485.985', KEY_POS), ('調整', '1 1.4', KEY_SCALE), ('平坦化', '1', KEY_FLAT), ('配置', '0 (左揃え)', KEY_ALIGN), ('行間', '-5', KEY_LS)],
                runs, {'scale': '0.9 0.9'})
    for s in ov.get('subs', []):
        tx = s['text']
        st = {'font': 'Klee', 'fontSize': '32', 'fontFace': 'Medium', 'fontColor': '1 1 1 1', 'alignment': 'center', 'lineSpacing': '-5'}
        runs = [(tx[:-1], {**st, 'kerning': '1.6'}), (tx[-1:], st)] if len(tx) > 1 else [(tx, st)]
        o.title(s['start'], s['end'], 3, tx[:20] + ' - 基本タイトル',
                [('位置', '1 -483.734', KEY_POS), ('平坦化', '1', KEY_FLAT), ('配置', '1 (水平方向に中央揃え)', KEY_ALIGN), ('行間', '-5', KEY_LS)],
                runs)
    for p in ov.get('pins', []):
        o.marker(p['at'], p['note'])
    tree.write(out, encoding='UTF-8', xml_declaration=True)
    m = re.search(r'<!DOCTYPE[^>]*>', head)
    body = open(out, encoding='utf-8').read()
    body = body.replace("<?xml version='1.0' encoding='UTF-8'?>", '<?xml version="1.0" encoding="UTF-8"?>\n' + (m.group(0) if m else '<!DOCTYPE fcpxml>'), 1)
    open(out, 'w', encoding='utf-8').write(body)
    print(f"WAMU {1 if ov.get('wamu') else 0}・見出し {len(ov.get('headings', []))}・字幕 {len(ov.get('subs', []))}・ピン {len(ov.get('pins', []))}")


if __name__ == '__main__':
    main()
