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


if __name__ == '__main__':
    errs = validate(sys.argv[1])
    if not errs:
        print('OK（v1.14 で増えた要素以外のエラーなし）')
    else:
        from collections import Counter
        c = Counter(re.sub(r'^.*?: ', '', e, count=1)[:220] for e in errs)
        print(f'エラー {len(errs)} 件')
        for k, v in c.most_common(10):
            print(f'  ×{v} {k}')
        sys.exit(1)
