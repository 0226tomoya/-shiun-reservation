"""FCPXML を Apple の DTD（CommandPost 配布の v1.13）で検証する。v1.14 で増えた要素によるエラーは除外して表示する。

    python3 validate_fcpxml.py FILE.fcpxml
"""
import os
import re
import subprocess
import sys
import urllib.request

DTD_URL = 'https://raw.githubusercontent.com/CommandPost/CommandPost/develop/src/extensions/cp/apple/fcpxml/dtd/FCPXMLv1_13.dtd'
KNOWN_1_14 = ('match-analysis-type', 'attribute version of fcpxml', 'does not validate')


def dtd_path():
    p = os.path.join(os.path.expanduser('~'), '.cache', 'fcpxml', 'FCPXMLv1_13.dtd')
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        urllib.request.urlretrieve(DTD_URL, p)
    return p


def validate(path):
    r = subprocess.run(['xmllint', '--noout', '--dtdvalid', dtd_path(), path], capture_output=True, text=True)
    errs = [l for l in r.stderr.splitlines() if 'validity error' in l and not any(k in l for k in KNOWN_1_14)]
    # smart-collection の match-analysis-type 起因の行も除外
    errs = [l for l in errs if 'got (match-analysis-type' not in l]
    return errs


def check_refs(path):
    """参照（ref・format）が、正しい種類のリソースを指しているか。FCP は種類が違うと読み込みを拒否する
    （例: filter-video の ref が asset を指している → 「見つかったリソースは無効です」）。重複 ID も見る。"""
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    rs = list(root.find('resources'))
    errs = []
    seen = {}
    for e in rs:
        if e.get('id') in seen:
            errs.append(f"重複したリソース ID {e.get('id')}")
        seen[e.get('id')] = e
    want = {'filter-video': {'effect'}, 'filter-audio': {'effect'}, 'title': {'effect'}, 'generator': {'effect'},
            'asset-clip': {'asset'}, 'video': {'asset', 'effect'}, 'audio': {'asset'}, 'ref-clip': {'media'},
            'mc-clip': {'media'}, 'sync-source': None, 'mc-source': None}
    for el in root.iter():
        ref = el.get('ref')
        if ref and want.get(el.tag) is not None:
            tg = seen[ref].tag if ref in seen else None
            if tg not in want[el.tag]:
                errs.append(f"{el.tag}（{el.get('name')}）の ref={ref} が {tg or '存在しないリソース'} を指している")
        fm = el.get('format')
        if fm and el.tag not in ('fcpxml',) and (fm not in seen or seen[fm].tag != 'format'):
            errs.append(f"{el.tag}（{el.get('name')}）の format={fm} が format でない")
    ids = set()
    for d in root.iter('text-style-def'):
        if d.get('id') in ids:
            errs.append(f"重複した text-style-def ID {d.get('id')}")
        ids.add(d.get('id'))
    return errs


if __name__ == '__main__':
    errs = validate(sys.argv[1])
    from collections import Counter as _C
    rerrs = check_refs(sys.argv[1])
    if rerrs:
        print(f'参照の誤り {len(rerrs)} 件（FCP で読み込めない）')
        for k, v in _C(rerrs).most_common(10):
            print(f'  ×{v} {k}')
        sys.exit(1)
    if not errs:
        print('OK（v1.14 で増えた要素以外のエラーなし）')
    else:
        from collections import Counter
        c = Counter(re.sub(r'^.*?: ', '', e, count=1)[:220] for e in errs)
        print(f'エラー {len(errs)} 件')
        for k, v in c.most_common(10):
            print(f'  ×{v} {k}')
        sys.exit(1)
