"""完成版の FCPXML から、長編のテロップの「型」を種類ごとに 1 つずつ抜き出す（書体・大きさ・位置・字間・フェード・影をそのまま使うため）。

    python3 longform_templates.py OUT.json WORKDIR A6x A8x A10x ...

WORKDIR/<動画>/Info.fcpxml（完成版）と WORKDIR/<動画>/gold.json（longform_events.py の出力）を読み、
gold の部品と文が同じ <title> を探して、その種類の型にする（先に書いた動画を優先）。
OUT.json: {種類: {"src": 動画, "title": <title> の XML, "effects": {id: <effect> の XML}, "lane": レーン}}
"""
import json
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict

KINDS = ('fact', 'opinion', 'vertical', 'price', 'tsukkomi', 'color', 'topic', 'heading', 'item_card', 'coord',
         'shiun_card', 'title_call', 'channel', 'closing', 'wamu')


def n(s):
    return ''.join(c for c in unicodedata.normalize('NFKC', s or '') if not c.isspace())


def main():
    out, work, vids = sys.argv[1], sys.argv[2], sys.argv[3:]
    tpl = {}
    for v in vids:
        root = ET.parse(f'{work}/{v}/Info.fcpxml').getroot()
        eff = {e.get('id'): e for e in root.iter('effect')}
        gold = json.load(open(f'{work}/{v}/gold.json'))['events']
        by = defaultdict(list)
        for e in gold:
            by[n(e['text'])].append(e)
        for t in root.iter('title'):
            txt = ''.join(x.text or '' for x in t.iter('text-style') if x.text)
            for e in by.get(n(txt), []):
                k = e['kind']
                if k not in KINDS or k in tpl:
                    continue
                refs = {t.get('ref')} | {f.get('ref') for f in t.iter('filter-video')}
                tpl[k] = {'src': v, 'title': ET.tostring(t, encoding='unicode'), 'lane': e.get('lane'),
                          'effects': {r: ET.tostring(eff[r], encoding='unicode') for r in refs if r in eff}}
    json.dump(tpl, open(out, 'w'), ensure_ascii=False, indent=1)
    print({k: v['src'] for k, v in tpl.items()})
    print('無い種類:', [k for k in KINDS if k not in tpl])


if __name__ == '__main__':
    main()
