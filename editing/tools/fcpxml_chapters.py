# FCPXML のチャプターマーカー（ピン）をタイムラインの時刻に直して一覧にする: python3 fcpxml_chapters.py Info.fcpxml
import sys, xml.etree.ElementTree as ET
from fractions import Fraction as Fr
def t(s):
    if not s: return Fr(0)
    s=s.rstrip('s')
    if '/' in s: a,b=s.split('/'); return Fr(int(a),int(b))
    return Fr(s)
root=ET.parse(sys.argv[1]).getroot()
seq=root.find('.//project/sequence')
par={c:p for p in seq.iter() for c in p}
def tomap(e, x):
    # x: e のローカル時刻 → タイムライン時刻
    while e is not seq:
        p=par[e]
        if e.tag=='spine' or e.get('offset') is None:
            x = x + t(e.get('offset')) if e.tag=='spine' else x
        else:
            x = t(e.get('offset')) + (x - t(e.get('start')))
        e=p
        if e.tag=='sequence': break
    return x
for m in seq.iter('chapter-marker'):
    e=par[m]; tl=tomap(e, t(m.get('start')))
    s=float(tl); print(f"{int(s//60)}:{int(s%60):02d}\t{s:.2f}\t{m.get('value')}\t{e.tag} {e.get('name','')[:30]} lane={e.get('lane')}")
