"""出来上がった FCPXML のテロップに、完成版と同じ影を付ける（テロップの影だけを変え、ほかは触らない）。

    python3 apply_telop_shadow.py IN.fcpxml OUT.fcpxml

影の値の出どころは telop_shadow.py。付ける所:
  対談の字幕（游ゴシック Bold 45）        … 文字のドロップシャドウ（ぼかした縁取りの代わり。黒 1.0・距離 0・ぼかし 10）
  長編の事実・感想・縦書き（縁取り 0.25）  … 同じ形で 0.35。XML の縁取り（strokeColor・strokeWidth）は外す（読み込むと固い線になるため）
  長編の YuGothic の縁取り 0.5            … 同じ形で 0.7
  見出し・名前（Corporate Logo・源ノ明朝 Heavy の基本タイトル） … クリップにドロップシャドウのフィルタ（0.75・ぼかし 30）
既に影（shadowColor）を持つ文字（Paste の WAMU・題のタイプライターなど）は、ユーザーの設定なのでそのまま。
"""
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from telop_shadow import SUB_TALK, TEL_LONG, LIST_LONG, halo, drop_effect, add_drop_shadow  # noqa: E402

HEAD_FONTS = ('Corporate Logo', 'Source Han Serif JP')


def main():
    src, out = sys.argv[1], sys.argv[2]
    head = open(src, encoding='utf-8').read(400)
    tree = ET.parse(src)
    root = tree.getroot()
    res = root.find('resources')
    ids = {e.get('id') for e in root.iter() if e.get('id')}

    def new_id():
        n = 1
        while f'r{n}' in ids:
            n += 1
        ids.add(f'r{n}')
        return f'r{n}'

    drop = drop_effect(res, new_id)
    n_sub = n_long = n_head = 0
    for t in root.iter('title'):
        styles = [ts for d in t.findall('text-style-def') for ts in d.findall('text-style')]
        for ts in styles:
            a = ts.attrib
            if 'shadowColor' in a:
                continue
            if a.get('font') == 'YuGothic' and a.get('fontSize') == '45' and a.get('bold') == '1':
                a.update(halo(*SUB_TALK)); n_sub += 1
            elif a.get('strokeColor') in ('0 0 0 0.25', '0 0 0 0.5') and a.get('strokeWidth', '').startswith('-'):
                op = TEL_LONG if a['strokeColor'].endswith('0.25') else LIST_LONG
                a.pop('strokeColor'); a.pop('strokeWidth')
                a.update(halo(*op)); n_long += 1
        if any(ts.get('font', '').startswith(HEAD_FONTS) for ts in styles):
            add_drop_shadow(t, drop); n_head += 1
    tree.write(out, encoding='UTF-8', xml_declaration=True)
    body = open(out, encoding='utf-8').read()
    m = re.search(r'<!DOCTYPE[^>]*>', head)
    body = body.replace("<?xml version='1.0' encoding='UTF-8'?>", '<?xml version="1.0" encoding="UTF-8"?>\n' + (m.group(0) if m else '<!DOCTYPE fcpxml>'), 1)
    open(out, 'w', encoding='utf-8').write(body)
    print(f'字幕の影 {n_sub}・長編のテロップの影 {n_long}・見出し／名前のドロップシャドウ {n_head}')


if __name__ == '__main__':
    main()
