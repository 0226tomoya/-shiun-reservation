"""渡す前の総点検。今日（10/13）までに FCP で起きたトラブルを、XML の段階で全部見つける。1 つでも × があれば渡さない。

    python3 preflight_fcpxml.py OUT.fcpxml [--media-info media_info.json]

見る所（× は渡せない、△ は理由を確かめる）:
  × DTD（Apple の書式）に合わない                       … FCP で読み込めない（10/13 の 1 回目）
  × ref・format が resources に無い                      … 同上（BGM・効果音の format の写し漏れ）
  × つないだ要素が親クリップの範囲の外                    … FCP が黙って捨てる
  × マルチカムのアングルの頭に空きがあるのに gap が無い    … 波形と聞こえる音がずれる（ローファー 1.7 秒、スラックス 25.7 秒）
  △ 素材のフレームレートとタイムラインが違うのに conform-rate scaleEnabled="0" が無い
                                                        … 自動速度で遅くなるおそれ（FCP の書き出しでは省かれることもある）
  × こちらで作った撮影素材（MOV・MP4。uid が無い）の asset の頭が 0 秒で、実物の情報（media_info）が無い
                                                        … タイムコードと合わず再接続できない
  × media_info があるのに、asset の頭・長さ・パスが実物と違う
  △ テロップに縁取り（strokeColor / strokeWidth）がある   … XML ではぼかしが書けない。ユーザーの決めで XML では付けない
  △ 素材のパスが /tmp・/var/folders・Downloads にある     … 消えやすい
  △ テロップに「追加予定」「(仮)」「TODO」が残っている
"""
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fr(int(a), int(b))
    return Fr(s)


def main():
    path = sys.argv[1]
    mi = {}
    if '--media-info' in sys.argv:
        mi = json.load(open(sys.argv[sys.argv.index('--media-info') + 1]))
    bad, warn = [], []
    # 1. DTD
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'validate_fcpxml.py'), path], capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or [''])[-1]
    if not last.startswith('OK'):
        bad.append('DTD: ' + last)
    root = ET.parse(path).getroot()
    res = {e.get('id'): e for e in root.find('resources')}
    # 2. 参照
    for e in root.iter():
        for k in ('ref', 'format'):
            v = e.get(k)
            if v and e.tag not in ('text-style',) and v not in res:
                bad.append(f'参照: {e.tag}「{e.get("name")}」の {k}={v} が resources に無い')
    # 3. つないだ要素が親の範囲の中か
    for p in root.iter('project'):
        sp = p.find('sequence/spine')
        if sp is None:
            continue
        for c in sp:
            st, du = T(c.get('start')), T(c.get('duration'))
            for ch in c:
                if ch.get('lane') is None or ch.get('offset') is None:
                    continue
                o = T(ch.get('offset'))
                if not (st <= o < st + du):
                    bad.append(f'範囲外: {p.get("name")} の {c.get("name")} に付いた {ch.tag}「{ch.get("name")}」')
    # 4. マルチカムのアングルの頭の空き（使っていないマルチカムは △）
    used = {e.get('ref') for pj in root.iter('project') for e in pj.iter('mc-clip')}
    for m in root.find('resources').iter('media'):
        mc = m.find('multicam')
        if mc is None:
            continue
        for ang in mc.findall('mc-angle'):
            kids = list(ang)
            if kids and kids[0].tag != 'gap' and T(kids[0].get('offset')) > 0:
                (bad if m.get('id') in used else warn).append(f'音ずれ: マルチカム「{m.get("name")}」のアングル「{ang.get("name")}」の頭に gap が無い（offset {float(T(kids[0].get("offset"))):.3f} 秒）' + ('' if m.get('id') in used else '・どのプロジェクトも使っていない'))
    # 5. 自動速度（conform-rate）
    seq_fd = {}
    for p in root.iter('project'):
        f = res.get(p.find('sequence').get('format'))
        if f is not None and f.get('frameDuration'):
            seq_fd[p.get('name')] = T(f.get('frameDuration'))
    tl_fds = set(seq_fd.values())
    for m in root.find('resources').iter('media'):
        mc = m.find('multicam')
        if mc is not None and res.get(mc.get('format')) is not None and res[mc.get('format')].get('frameDuration'):
            tl_fds.add(T(res[mc.get('format')].get('frameDuration')))
    for e in root.iter('asset-clip'):
        a = res.get(e.get('ref'))
        if a is None or a.get('hasVideo') != '1':
            continue
        f = res.get(a.get('format'))
        if f is None or not f.get('frameDuration'):
            continue  # 静止画など
        src = T(f.get('frameDuration'))
        if tl_fds and all(src != fd and (src / fd).denominator != 1 for fd in tl_fds):
            cr = e.find('conform-rate')
            if cr is None or cr.get('scaleEnabled') != '0':
                warn.append(f'自動速度: 「{e.get("name")}」（{float(1 / src):.3f}p）に conform-rate scaleEnabled="0" が無い（FCP の書き出しでも省かれることがある。音ずれが無いか聞いて確かめる）')
    # 6. 撮影素材の asset の頭（タイムコード）
    for a in res.values():
        if a.tag != 'asset':
            continue
        rep = a.find('media-rep')
        src = unquote(rep.get('src')) if rep is not None else ''
        name = a.get('name')
        if re.search(r'\.(mov|mp4|mxf)$', src, re.I) and a.get('hasVideo') == '1':
            if name in mi:
                want = mi[name]['asset']
                for k in ('start', 'duration'):
                    if T(want.get(k)) != T(a.get(k)):
                        bad.append(f'素材: 「{name}」の {k} が実物（{want.get(k)}）と違う（{a.get(k)}）')
                if mi[name].get('src') and unquote(mi[name]['src']) != src:
                    bad.append(f'素材: 「{name}」のパスが実物と違う')
            elif T(a.get('start')) == 0 and not a.get('uid'):  # uid がある＝FCP が書き出した実物の情報なので信じる
                bad.append(f'再接続: 「{name}」の頭が 0 秒で、実物の情報が無い（撮影素材はタイムコードから始まる。FCP で素材の XML を書き出してもらう）')
        if re.search(r'^/(tmp|private/var/folders|var/folders)/|/Downloads/', src.replace('file://', '')):
            warn.append(f'消えやすい場所: 「{name}」{src}')
    # 7. テロップ
    n_stroke = 0
    for t in root.iter('title'):
        txt = ''.join(x.text or '' for x in t.iter('text-style'))
        if re.search(r'追加予定|\(仮\)|（仮）|TODO', txt):
            warn.append(f'仮置き: 「{txt.strip()[:30]}」')
    for s in root.iter('text-style'):
        if s.get('strokeColor') or s.get('strokeWidth'):
            n_stroke += 1
    if n_stroke:
        warn.append(f'縁取り: {n_stroke} か所（XML ではぼかしが書けない。ユーザーの決めで付けない）')
    for b in bad:
        print('×', b)
    for w in warn:
        print('△', w)
    print(f'結果: × {len(bad)}・△ {len(warn)}' + ('（渡せる）' if not bad else '（渡せない）'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
