"""ユーザーのカット（本線）が 1 コマも変わっていないかを確かめる。

    python3 short_cut_compare.py BASE.fcpxml OUT.fcpxml

- プロジェクトごとに、spine の子（mc-clip・asset-clip）の数・順番・タグ・属性（offset・start・duration・ref・name…）を比べる
- 子の中身のうち「つないだ要素」（lane のある title・video・asset-clip）以外（mc-source・adjust-volume・filter-audio など）が同じか
- BASE にあった「つないだ要素」（ユーザーが直した所）が OUT にそのまま残っているか
- sequence の duration・format が同じか
OUT に無いプロジェクトは比べない（1 本ずつの書き出し）。差があれば 1 を返す。
"""
import sys
import unicodedata as ud
import xml.etree.ElementTree as ET

N = lambda s: ud.normalize('NFC', s or '')


def canon(e):
    """要素を属性の順番によらない文字列にする"""
    a = ' '.join(f'{k}="{v}"' for k, v in sorted(e.attrib.items()))
    inner = ''.join(canon(c) for c in e)
    txt = (e.text or '').strip()
    return f'<{e.tag} {a}>{txt}{inner}</{e.tag}>'


def projects(path):
    r = ET.parse(path).getroot()
    return {N(p.get('name')): p for p in r.iter('project')}


def main():
    base, out = projects(sys.argv[1]), projects(sys.argv[2])
    bad = 0
    for name, po in out.items():
        pb = base.get(name)
        if pb is None:
            print(f'× {name}: 元の XML に無いプロジェクト'); bad += 1; continue
        sb, so = pb.find('sequence'), po.find('sequence')
        if sb.attrib != so.attrib:
            print(f'× {name}: sequence の属性が違う {sb.attrib} → {so.attrib}'); bad += 1
        cb, co = list(sb.find('spine')), list(so.find('spine'))
        if len(cb) != len(co):
            print(f'× {name}: 本線のクリップ数 {len(cb)} → {len(co)}'); bad += 1; continue
        n_conn = 0
        for i, (b, o) in enumerate(zip(cb, co)):
            if b.tag != o.tag or b.attrib != o.attrib:
                print(f'× {name} #{i}: {b.tag} {b.attrib} → {o.tag} {o.attrib}'); bad += 1
            core_b = [canon(c) for c in b if c.get('lane') is None]
            core_o = [canon(c) for c in o if c.get('lane') is None]
            if core_b != core_o:
                print(f'× {name} #{i}: クリップの中身（mc-source・音量・フィルタ）が違う'); bad += 1
            conn_b = [canon(c) for c in b if c.get('lane') is not None]
            conn_o = [canon(c) for c in o if c.get('lane') is not None]
            miss = [c for c in conn_b if c not in conn_o]
            if miss:
                print(f'× {name} #{i}: ユーザーのつないだ要素 {len(miss)} 個が消えた/変わった'); bad += 1
            n_conn += len(conn_o) - len(conn_b)
        print(f'{"OK" if not bad else "--"} {name}: 本線 {len(co)} 本（offset・start・duration・中身）一致、ユーザーの要素 {sum(1 for b in cb for c in b if c.get("lane") is not None)} 個そのまま、足した要素 {n_conn} 個')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
