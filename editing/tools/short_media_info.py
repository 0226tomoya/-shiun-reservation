"""FCP から書き出した素材の XML（イベントに元の MOV・WAV を読み込んで「書き出し → XML」したもの）から、
素材ごとの asset と format をそのまま抜き出す。short_build.py がこれを使うと、XML の素材が実物と同じ範囲
（タイムコードの頭・長さ・チャンネル）になり、FCP で再接続できる。
python3 short_media_info.py 書き出した.fcpxml(d) media_info.json
"""
import sys, os, json
import xml.etree.ElementTree as ET

src = sys.argv[1]
if os.path.isdir(src):
    src = os.path.join(src, 'Info.fcpxml')
root = ET.parse(src).getroot()
res = {e.get('id'): e for e in root.find('resources')}
out = {}
for a in root.find('resources').iter('asset'):
    name = os.path.splitext(a.get('name'))[0]
    rep = a.find('media-rep')
    info = {'asset': {k: v for k, v in a.attrib.items() if k != 'id'},
            'src': rep.get('src') if rep is not None else None,
            'bookmark': (rep.find('bookmark').text if rep is not None and rep.find('bookmark') is not None else None)}
    f = res.get(a.get('format'))
    if f is not None:
        info['format'] = {k: v for k, v in f.attrib.items() if k != 'id'}
    out[name] = info
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
print(f'{len(out)} 素材: ' + ', '.join(f"{k}（頭 {v['asset'].get('start')}）" for k, v in out.items()))
