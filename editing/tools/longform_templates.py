"""完成版の FCPXML から、長編のテロップの「型」を種類ごとに 1 つずつ抜き出す（書体・大きさ・位置・字間・フェード・影をそのまま使うため）。

    python3 longform_templates.py OUT.json WORKDIR A6x A8x A10x ...

WORKDIR/<動画>/Info.fcpxml（完成版）と WORKDIR/<動画>/gold.json（longform_events.py の出力）を読み、
gold の部品と文が同じ <title> を探して、その種類の型にする（先に書いた動画を優先）。
OUT.json: {種類: {"src": 動画, "title": <title> の XML, "effects": {id: <effect> の XML}, "lane": レーン},
           "sfx:種類": {"src": 動画, "clip": <asset-clip> の XML, "asset": <asset> の XML, "format": <format> の XML}}
効果音は gold の sfx の名前（素材名）と同じ名前の asset-clip（本線につないだもの）を型にする。複合クリップ（クリック・シャッター）は別の回の asset-clip を探す
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
        assets = {a.get('id'): a for a in root.iter('asset')}
        fmts = {f.get('id'): f for f in root.iter('format')}
        for e in gold:
            k = e['kind']
            if not k.startswith('sfx:') or k == 'sfx:other' or k in tpl:
                continue
            same = lambda c: unicodedata.normalize('NFC', c.get('name') or '') == unicodedata.normalize('NFC', e['text'])
            ac = next((c for c in root.iter('asset-clip') if same(c)), None)
            if ac is None or ac.get('ref') not in assets:
                rc = next((c for c in root.iter('ref-clip') if same(c)), None)
                media = {m.get('id'): m for m in root.iter('media')}
                if rc is None or rc.get('ref') not in media:
                    continue
                m = media[rc.get('ref')]
                inner = {c.get('ref') for c in m.iter() if c.get('ref') in assets}
                fs = {assets[i].get('format') for i in inner} | {x.get('format') for x in m.iter() if x.get('format')}
                tpl[k] = {'src': v, 'clip': ET.tostring(rc, encoding='unicode'), 'media': ET.tostring(m, encoding='unicode'),
                          'assets': [ET.tostring(assets[i], encoding='unicode') for i in inner],
                          'formats': [ET.tostring(fmts[f], encoding='unicode') for f in fs if f in fmts]}
                continue
            a = assets[ac.get('ref')]
            f = fmts.get(a.get('format') or ac.get('format'))
            tpl[k] = {'src': v, 'clip': ET.tostring(ac, encoding='unicode'), 'asset': ET.tostring(a, encoding='unicode'),
                      'format': ET.tostring(f, encoding='unicode') if f is not None else None}
        # 複合クリップの部品（商品番号の箱「本編 クリップ」・冒頭プロフィール）
        media = {m.get('id'): m for m in root.iter('media')}
        for e in gold:
            k = e['kind']
            if k not in ('item_label', 'op_profile') or k in tpl:
                continue
            rc = next((c for c in root.iter('ref-clip') if unicodedata.normalize('NFC', c.get('name') or '') == unicodedata.normalize('NFC', e['text'])
                       and c.get('ref') in media), None)
            if rc is None:
                continue
            m = media[rc.get('ref')]
            refs = {x.get('ref') for x in m.iter() if x.get('ref')} | {f.get('ref') for f in rc.iter('filter-video')}
            fs = {x.get('format') for x in m.iter() if x.get('format')} | {assets[r].get('format') for r in refs if r in assets}
            tpl[k] = {'src': v, 'clip': ET.tostring(rc, encoding='unicode'), 'media': ET.tostring(m, encoding='unicode'),
                      'effects': {r: ET.tostring(eff[r], encoding='unicode') for r in refs if r in eff},
                      'assets': [ET.tostring(assets[r], encoding='unicode') for r in refs if r in assets],
                      'formats': [ET.tostring(fmts[f], encoding='unicode') for f in fs if f in fmts]}
    json.dump(tpl, open(out, 'w'), ensure_ascii=False, indent=1)
    print({k: v['src'] for k, v in tpl.items()})
    print('無い種類:', [k for k in KINDS if k not in tpl])


if __name__ == '__main__':
    main()
