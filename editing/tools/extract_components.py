"""実際の編集 FCPXML から「シーン単位のパーツ」を元の設定のまま抜き出し、
FCP に読み込めるパーツ集 FCPXML を作る。

使い方:
    python3 extract_components.py SOURCE.fcpxml PROJECT_NAME scenes.json OUT.fcpxml

scenes.json: [{"id": "S01", "label": "名前カード", "t0": 0.0, "t1": 4.7}, ...]
    t0/t1 は元プロジェクト上の秒数。t0 <= 開始 < t1 の接続クリップ（テロップ、
    調整レイヤー、画像、B-roll、複合クリップ）を、相対位置とレーンを保ったまま
    1シーン = 1つのギャップに貼り付ける。メインカメラ（マルチカム）と BGM は除外する。

出力のプロジェクト内では、シーンがギャップとして順番に並び、各ギャップにマーカー
（シーンID とラベル）が付く。素材ファイルはオフラインになるが、テロップ・調整レイヤー・
エフェクトの設定はすべて元のまま残る。
"""
import copy
import json
import sys
from fractions import Fraction
import xml.etree.ElementTree as ET

CLIP_TAGS = {'clip', 'asset-clip', 'video', 'audio', 'title', 'ref-clip', 'mc-clip', 'gap', 'sync-clip'}
EXCLUDE_NAMES = {'BGM'}
TOL = Fraction(1, 5)  # シーン境界の丸め誤差（秒）


def T(s):
    s = (s or '0s').rstrip('s')
    return Fraction(s) if s else Fraction(0)


def S(fr):
    fr = Fraction(fr).limit_denominator(240000)
    if fr.denominator == 1:
        return f'{fr.numerator}s'
    return f'{fr.numerator}/{fr.denominator}s'


def collect_connected(project):
    """トップレベルのスパイン要素と、その接続クリップを絶対時間付きで列挙する。"""
    out = []
    spine = project.find('sequence/spine')
    for e in spine:
        if e.tag not in CLIP_TAGS:
            continue
        off, st = T(e.get('offset')), T(e.get('start'))
        out.append({'el': e, 'abs': off, 'lane': None, 'parent': None})
        for ch in e:
            if ch.tag in CLIP_TAGS and ch.get('lane') is not None:
                a = off + (T(ch.get('offset')) - st)
                out.append({'el': ch, 'abs': a, 'lane': int(ch.get('lane')), 'parent': e})
    return out


def deps(el, res, acc):
    """el が参照するリソース ID を再帰的に集める。"""
    for x in el.iter():
        for k in ('ref', 'format'):
            rid = x.get(k)
            if rid and rid in res and rid not in acc:
                acc.add(rid)
                deps(res[rid], res, acc)
    return acc


def main():
    src, proj_name, scenes_path, out_path = sys.argv[1:5]
    tree = ET.parse(src)
    root = tree.getroot()
    resources = root.find('resources')
    res = {e.get('id'): e for e in resources}
    project = [p for p in root.iter('project') if p.get('name') == proj_name][0]
    seq = project.find('sequence')
    items = collect_connected(project)
    scenes = json.load(open(scenes_path, encoding='utf-8'))

    new_spine = ET.Element('spine')
    used = set()
    deps(seq, {k: v for k, v in res.items() if k == seq.get('format')}, used)
    used.add(seq.get('format'))
    cursor = Fraction(0)
    for sc in scenes:
        t0, t1 = Fraction(str(sc['t0'])), Fraction(str(sc['t1']))
        picked = []
        for it in items:
            e = it['el']
            if e.get('name') in EXCLUDE_NAMES or e.tag == 'mc-clip':
                continue
            if e.get('enabled') == '0':
                continue
            if t0 - TOL <= it["abs"] < t1 - TOL:
                picked.append(it)
        # スパイン直置きの要素（カウントダウン動画など）は lane 1 に上げ、他を +1 する
        has_spine = any(p['lane'] is None for p in picked)
        dur = max([t1 - t0] + [p['abs'] - t0 + T(p['el'].get('duration')) for p in picked if p['lane'] is None or p['lane'] >= 0])
        gap = ET.SubElement(new_spine, 'gap', name=f"{sc['id']} {sc['label']}", offset=S(cursor), start='0s', duration=S(dur))
        for p in sorted(picked, key=lambda p: (p['lane'] if p['lane'] is not None else 0, p['abs'])):
            e = copy.deepcopy(p['el'])
            lane = p['lane']
            if lane is None:
                lane = 1
                # 接続クリップは個別に拾うので、スパイン要素からは外して重複を防ぐ
                for ch in list(e):
                    if ch.tag in CLIP_TAGS and ch.get('lane') is not None:
                        e.remove(ch)
            elif has_spine and lane > 0:
                lane += 1
            e.set('lane', str(lane))
            e.set('offset', S(p['abs'] - t0))
            # 接続クリップ配下の子要素のオフセットは要素自身のローカル時間なのでそのまま
            gap.append(e)
            deps(e, res, used)
        ET.SubElement(gap, 'marker', start='0s', duration=S(Fraction(1001, 60000)), value=f"{sc['id']} {sc['label']}")
        cursor += dur

    # 新しいドキュメントを組み立てる（リソースは元の順番を維持）
    new_root = ET.Element('fcpxml', version=root.get('version'))
    new_res = ET.SubElement(new_root, 'resources')
    for e in resources:
        if e.get('id') in used:
            new_res.append(copy.deepcopy(e))
    lib = ET.SubElement(new_root, 'library')
    ev = ET.SubElement(lib, 'event', name='shiun 編集パーツ')
    pr = ET.SubElement(ev, 'project', name=f'パーツ集_{proj_name}')
    sq = ET.SubElement(pr, 'sequence', {k: v for k, v in seq.attrib.items() if k != 'duration'})
    sq.set('duration', S(cursor))
    sq.append(new_spine)
    ET.indent(new_root)
    with open(out_path, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(new_root, encoding='utf-8'))
    print(f'{len(scenes)} scenes, {S(cursor)}, {len(used)} resources -> {out_path}')


if __name__ == '__main__':
    main()
