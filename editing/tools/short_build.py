"""shiun の販促ショート（縦 1080x1920・59.94p）の FCPXML を、編集表（EDL の JSON）から作る。
python3 short_build.py edl.json out.fcpxml

型: A23 のライブラリに入っている 2026-08 の販促ショート「COW LEATHER LOAFER」（修正なしで通った最新の型）。
そのプロジェクトの部品（字幕・商品名カード・価格・発売日・身長ラベルのタイトル、調整レイヤー、BGM、効果音、Limiter）を
複製して、文言と時刻だけを差し替える。書式（フォント・大きさ・位置・縁）は型のまま。

本線は「映像のアングル（DSCF の MOV）＋ピンマイクのアングル（wav）」のマルチカムを素材ごとに作り、
ずれ（マイクの時刻 = 映像の時刻 + offset 秒、editing/tools/av_sync.py で測った値）を 1/48000 秒単位で入れる。

編集表 edl.json:
{
 "name": "プロジェクト名",
 "media_root": "file:///…/本編/" ,   # 素材の場所（Mac で開いたとき relink しやすいように）
 "audio_root": "file:///…/音声/",
 "clips": {"DSCF0030": {"dur": 324.0, "fps": 24, "mic": "TX02_MIC035_….wav", "mic_dur": 328.44, "offset": 2.7284}},
 "segments": [{"clip": "DSCF0030", "in": 12.3, "out": 13.0}],        # 本線（素材の映像の秒）。順に並べる。任意で "scale": 1.05, "position": "0 2.08"（画角そろえ）
 "inserts":  [{"clip": "DSCF0031", "in": 5.0, "out": 7.0, "at": 20.0, "lane": 2}],  # 本線の上に重ねる映像（音なし）
 "subs":     [{"text": "低身長のために", "at": 0.0, "dur": 1.6}],      # 字幕（タイムラインの秒）
 "cards":    [{"kind": "hook|product|product_side|price|release|height", "lines": ["…"], "at": 0, "dur": 3}],
 "se":       [{"kind": "decide|click", "at": 15.6}],
 "bgm": true, "zoom_in": true
}
"""
from urllib.parse import quote, unquote
import sys, json, copy, re, os, unicodedata
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr

TMPL = os.environ.get('SHORT_TMPL', '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/a23x/A23_shiun 26 Fall 1st Collection.fcpxmld/Info.fcpxml')
FD = Fr(1001, 60000)  # 59.94p の 1 コマ


def fr(x):
    """秒（float）→ 1 コマ単位に丸めた有理数"""
    return round(Fr(x) / FD) * FD


def ts(f):
    f = Fr(f)
    if f == 0:
        return '0s'
    return f'{f.numerator}s' if f.denominator == 1 else f'{f.numerator}/{f.denominator}s'


def ats(x):
    """音のずれ用: 1/48000 秒単位"""
    f = Fr(round(x * 48000), 48000)
    return ts(f)


def parse_t(s):
    s = (s or '0s').rstrip('s')
    return Fr(s) if '/' not in s else Fr(int(s.split('/')[0]), int(s.split('/')[1]))


src = ET.parse(TMPL).getroot()
res = {e.get('id'): e for e in src.find('resources')}
proj = [p for p in src.iter('project') if p.get('name') == 'COW LEATHER LOAFER'][0]
spine0 = proj.find('sequence/spine')
items = [(c, x) for c in spine0 for x in c.iter() if x is not c]


def find(pred):
    for c, x in items:
        if pred(x):
            return x
    raise KeyError


def tname(x):
    return unicodedata.normalize('NFC', x.get('name') or '')  # Mac の名前は濁点が分かれている（NFD）ことがある


def text_of(x):
    return ''.join(t.text or '' for t in x.iter('text-style'))


T = {
    'sub': find(lambda x: x.tag == 'title' and tname(x).startswith('当たり前だけど')),
    'hook': find(lambda x: x.tag == 'title' and tname(x).startswith(' これが') and x.get('lane') == '3'),
    'product': find(lambda x: x.tag == 'title' and tname(x).startswith('COW LEATHER LOAFER') and x.get('lane') == '3' and '2.975' in ''.join(p.get('value', '') for p in x.iter('param'))),
    'product_side': find(lambda x: x.tag == 'title' and tname(x).startswith('COW LEATHER LOAFER') and x.get('lane') == '5'),
    'price': find(lambda x: x.tag == 'title' and tname(x).startswith('COW LEATHER LOAFER') and '35.35' in ''.join(p.get('value', '') for p in x.iter('param'))),
    'release': find(lambda x: x.tag == 'title' and 'Release' in tname(x)),
    'height': find(lambda x: x.tag == 'title' and tname(x).startswith('158cm : 37')),
    'adj': find(lambda x: x.tag == 'title' and tname(x) == 'Adjustment Layer'),
    'bgm': find(lambda x: x.tag == 'asset-clip' and tname(x).startswith('ES_Cherry')),
    'decide': find(lambda x: x.tag == 'asset-clip' and tname(x).startswith('決定ボタン')),
}
for k, f in (('zoom', lambda x: x.tag == 'title' and tname(x) == 'ズーム 01'),):
    try:
        T[k] = find(f)
    except KeyError:
        pass
try:
    T['click'] = find(lambda x: x.tag == 'asset-clip' and tname(x).startswith('マウス・シングルクリック'))
except KeyError:
    T['click'] = T['decide']
limiter = None
for c in spine0:
    fa = c.find('filter-audio')
    if fa is not None and fa.get('name') == 'Limiter':
        limiter = fa
        break
mc_fades = spine0.find('mc-clip/adjust-volume')

edl = json.load(open(sys.argv[1]))
out_path = sys.argv[2]

# ---- 新しい文書 ----
root = ET.Element('fcpxml', {'version': src.get('version', '1.11')})
resources = ET.SubElement(root, 'resources')
used = {}
seq_fmt = proj.find('sequence').get('format')


def need(rid):
    """型の resources から rid と、その中で参照している物をまとめて写す"""
    if rid in used or rid not in res:
        return
    used[rid] = copy.deepcopy(res[rid])
    for e in res[rid].iter():
        for k in ('ref', 'format'):
            if e.get(k) and e.get(k) != rid:
                need(e.get(k))


need(seq_fmt)
ts_counter = [90000]


def renumber_styles(el):
    """複製したタイトルの text-style-def の id を新しい番号にする"""
    m = {}
    for d in el.iter('text-style-def'):
        ts_counter[0] += 1
        m[d.get('id')] = f'ts{ts_counter[0]}'
        d.set('id', m[d.get('id')])
    for s in el.iter('text-style'):
        if s.get('ref') in m:
            s.set('ref', m[s.get('ref')])


def clone(key):
    el = copy.deepcopy(T[key])
    for e in el.iter():
        for k in ('ref', 'format'):
            if e.get(k):
                need(e.get(k))
    renumber_styles(el)
    return el


# 素材（映像・音声）
fmt_src_id = 'rS1'
# 縦撮りの DSCF の MOV は、FCP では 1080x1920・24.00p（frameDuration 1000/24000s、name なし）として読まれる（実物の書き出しで確認）
SRC_FPS = edl.get('src_fps', 24)
CONFORM_RATE = {24: '24', 23.976: '23.98', 29.97: '29.97', 30: '30'}[SRC_FPS]
SFD = {24: Fr(1, 24), 23.976: Fr(1001, 24000), 29.97: Fr(1001, 30000), 30: Fr(1, 30)}[SRC_FPS]
ET.SubElement(resources, 'format', {'id': fmt_src_id, 'frameDuration': {24: '1000/24000s', 23.976: '1001/24000s', 29.97: '1001/30000s', 30: '1000/30000s'}[SRC_FPS], 'width': '1080', 'height': '1920', 'colorSpace': '1-1-1 (Rec. 709)'})


def url(root_url, fname):
    """file:// の URL。日本語や空白は FCP の書き出しと同じく % で書く"""
    if root_url.startswith('file://'):
        return 'file://' + quote(unquote(root_url[7:]) + fname)
    return root_url + quote(fname)
# 実物の素材の情報（FCP で書き出した素材の XML から short_media_info.py で作る）。あれば asset をそのまま使う
MINFO_PATH = os.environ.get('SHORT_MEDIA_INFO') or edl.get('media_info')
MINFO = json.load(open(MINFO_PATH)) if MINFO_PATH and os.path.exists(MINFO_PATH) else {}
src0 = {}  # 素材名 → 素材の頭の時刻（タイムコード）


def real_asset(rid, key, fallback_attrs, fallback_src):
    """実物の情報があればそれで asset を作る（頭の時刻・長さ・チャンネル・uid・format を実物と同じにする）"""
    mi = MINFO.get(key)
    if not mi:
        el = ET.SubElement(resources, 'asset', dict(fallback_attrs, id=rid))
        ET.SubElement(el, 'media-rep', {'kind': 'original-media', 'src': fallback_src})
        src0[key] = Fr(0)
        return el
    attrs = dict(mi['asset'])
    if mi.get('format'):
        fid = 'rF' + rid
        ET.SubElement(resources, 'format', dict(mi['format'], id=fid))
        attrs['format'] = fid
    el = ET.SubElement(resources, 'asset', dict(attrs, id=rid))
    rep = ET.SubElement(el, 'media-rep', {'kind': 'original-media', 'src': mi['src'] or fallback_src})
    if mi.get('bookmark'):
        ET.SubElement(rep, 'bookmark').text = mi['bookmark']
    src0[key] = parse_t(attrs.get('start'))
    return el


mc_of = {}
n = 0
for name, c in edl['clips'].items():
    n += 1
    vid = f'rV{n}'; aid = f'rA{n}'; mid = f'rM{n}'
    vdur = int(Fr(c['dur']) / SFD) * SFD  # 素材のコマ単位
    real_asset(vid, name, {'name': name, 'start': '0s', 'duration': ts(vdur), 'hasVideo': '1', 'format': fmt_src_id, 'videoSources': '1', 'hasAudio': '1', 'audioSources': '1', 'audioChannels': '2', 'audioRate': '48000'},
               url(edl['media_root'], name + '.MOV'))
    if c.get('mic'):
        real_asset(aid, c['mic'][:-4], {'name': c['mic'][:-4], 'start': '0s', 'duration': ats(c['mic_dur']), 'hasAudio': '1', 'audioSources': '1', 'audioChannels': '1', 'audioRate': '48000'},
                   url(edl['audio_root'], c['mic']))
        # マルチカム: 映像を 0 に、マイクをずれぶん動かす（マイクの時刻 = 映像の時刻 + offset）
        med = ET.SubElement(resources, 'media', {'id': mid, 'name': name + ' マルチカム'})
        mc = ET.SubElement(med, 'multicam', {'format': seq_fmt, 'tcStart': '0s', 'tcFormat': 'NDF'})
        av = ET.SubElement(mc, 'mc-angle', {'name': name, 'angleID': f'V{n}'})
        vac = ET.SubElement(av, 'asset-clip', {'ref': vid, 'offset': '0s', 'name': name, 'start': ts(src0[name]), 'duration': ts(vdur), 'audioRole': 'dialogue'})
        # 24.00p の素材を 59.94p に置くと、FCP は既定で「自動速度」をかけ 23.976 に 0.1% 遅くする（長いほど音とずれる）。型と同じく止める
        ET.SubElement(vac, 'conform-rate', {'scaleEnabled': '0', 'srcFrameRate': CONFORM_RATE})
        aa = ET.SubElement(mc, 'mc-angle', {'name': 'ピンマイク', 'angleID': f'A{n}'})
        # マイクの時刻 = 映像の時刻 + off。置く位置（offset）は 59.94p のコマに揃え、端数は start（1/48000 秒）で持つ
        off = Fr(round(c['offset'] * 48000), 48000)
        O = -(-max(Fr(0), -off) // FD) * FD
        st = O + off
        mdur = Fr(round(c['mic_dur'] * 48000), 48000) - st
        # 角度の頭に空きがあるときは、型（FCP の書き出し）と同じく gap を前に置く。gap が無いと FCP は波形だけ offset の位置に描き、
        # 再生はアングルの頭（0 秒）から鳴らすため、聞こえる音が offset ぶん（例: 1.7 秒）ずれる
        if O > 0:
            ET.SubElement(aa, 'gap', {'name': 'ギャップ', 'offset': '0s', 'start': '3600s', 'duration': ts(O)})
        ET.SubElement(aa, 'asset-clip', {'ref': aid, 'offset': ts(O), 'name': c['mic'][:-4], 'start': ts(src0[c['mic'][:-4]] + st), 'duration': ts(mdur), 'audioRole': 'dialogue'})
        mc_of[name] = (mid, f'V{n}', f'A{n}')
    else:
        mc_of[name] = (None, vid, None)

library = ET.SubElement(root, 'library')
event = ET.SubElement(library, 'event', {'name': 'shiun ショート'})
project = ET.SubElement(event, 'project', {'name': edl['name']})
total = sum(fr(s['out']) - fr(s['in']) for s in edl['segments'])
seq = ET.SubElement(project, 'sequence', {'format': seq_fmt, 'duration': ts(total), 'tcStart': '0s', 'tcFormat': 'NDF', 'audioLayout': 'stereo', 'audioRate': '48k'})
spine = ET.SubElement(seq, 'spine')

# 本線
placed = []  # (tl0, tl1, element, local_start)
tl = Fr(0)
for s in edl['segments']:
    a, b = fr(s['in']), fr(s['out'])
    mid, vang, aang = mc_of[s['clip']]
    if mid:
        el = ET.SubElement(spine, 'mc-clip', {'ref': mid, 'offset': ts(tl), 'name': s['clip'], 'start': ts(a), 'duration': ts(b - a)})
        if mc_fades is not None:
            el.append(copy.deepcopy(mc_fades))
        ET.SubElement(el, 'mc-source', {'angleID': aang, 'srcEnable': 'audio'})
        vsrc = ET.SubElement(el, 'mc-source', {'angleID': vang, 'srcEnable': 'video'})
        if s.get('scale') or s.get('position'):  # 画角をそろえる（任意）。mc-clip では映像の調整は映像の mc-source の中に置く
            sc = s.get('scale', 1)
            ET.SubElement(vsrc, 'adjust-transform', {'position': s.get('position', '0 0'), 'scale': f'{sc} {sc}'})
        if limiter is not None:
            need(limiter.get('ref')); el.append(copy.deepcopy(limiter))
    else:
        el = ET.SubElement(spine, 'asset-clip', {'ref': vang, 'offset': ts(tl), 'name': s['clip'], 'start': ts(src0[s['clip']] + a), 'duration': ts(b - a)})
        ET.SubElement(el, 'conform-rate', {'scaleEnabled': '0', 'srcFrameRate': CONFORM_RATE})
    placed.append((tl, tl + b - a, el, a))
    tl += b - a


def host(t0):
    """タイムラインの時刻 t0 にある本線のクリップと、その中の時刻"""
    for a, b, el, st in placed:
        if a <= t0 < b:
            return el, st + (t0 - a)
    a, b, el, st = placed[-1]
    return el, st + (t0 - a)


def attach(el, at, dur, lane=None):
    at = fr(at); dur = max(FD, fr(dur))
    h, local = host(at)
    el.set('offset', ts(local))
    el.set('duration', ts(dur))
    if lane is not None:
        el.set('lane', str(lane))
    h.append(el)
    return el


def set_text(el, lines, keep_last_plain=True):
    """型のタイトルの文字を差し替える。字幕は「最後の 1 字だけ字間なし」の型（A19 と同じ）を守る"""
    tx = el.find('text')
    styles = [s.get('ref') for s in tx.findall('text-style')]
    base = styles[0]
    kern = next((r for r in styles if r != base), base)
    for s in list(tx):
        tx.remove(s)
    full = '\n'.join(lines)
    if keep_last_plain and len(styles) >= 2 and len(full) >= 2:
        if text_of(T['sub']).startswith('\n'):
            ET.SubElement(tx, 'text-style', {'ref': base}).text = '\n'
        ET.SubElement(tx, 'text-style', {'ref': kern}).text = full[:-1]
        ET.SubElement(tx, 'text-style', {'ref': base}).text = full[-1]
    else:
        ET.SubElement(tx, 'text-style', {'ref': base}).text = full
    nm = el.get('name', '')
    el.set('name', lines[0][:30] + ' - ' + nm.split(' - ')[-1])


# 調整レイヤー（型と同じく本線の上に、話のまとまりごと）・字幕
for s in edl.get('subs', []):
    el = clone('sub')
    set_text(el, s['text'].split('\n'))
    if '\n' in s['text']:
        for p in el.iter('param'):
            if p.get('name') == '位置':
                p.set('value', '0 -400')
    attach(el, s['at'], s['dur'], s.get('lane', 2))
for c in edl.get('cards', []):
    el = clone(c['kind'])
    set_text(el, c['lines'], keep_last_plain=(c['kind'] == 'hook'))
    attach(el, c['at'], c['dur'], c.get('lane'))
for a in edl.get('adj', []):
    attach(clone('adj'), a['at'], a['dur'], 1)
for se in edl.get('se', []):
    el = clone(se['kind'])
    attach(el, se['at'], parse_t(T[se['kind']].get('duration')), el.get('lane'))
if edl.get('zoom_in') and 'zoom' in T:
    attach(clone('zoom'), 0, parse_t(T['zoom'].get('duration')), 2)
# インサート（本線の上の映像。音は消す）
for ins in edl.get('inserts', []):
    mid, vang, aang = mc_of[ins['clip']]
    ref = vang if not mid else None
    if ref is None:
        continue
    el = ET.Element('asset-clip', {'ref': ref, 'name': ins['clip'], 'start': ts(src0[ins['clip']] + fr(ins['in']))})
    ET.SubElement(el, 'conform-rate', {'scaleEnabled': '0', 'srcFrameRate': CONFORM_RATE})
    ET.SubElement(el, 'adjust-volume', {'amount': '-96dB'})
    if ins.get('scale'):
        ET.SubElement(el, 'adjust-transform', {'scale': f"{ins['scale']} {ins['scale']}", 'position': ins.get('position', '0 0')})
    attach(el, ins['at'], fr(ins['out']) - fr(ins['in']), ins.get('lane', 3))
# BGM（頭から最後まで）
if edl.get('bgm'):
    el = clone('bgm')
    el.set('start', T['bgm'].get('start', '0s'))
    attach(el, 0, total, -1)

# resources の並び: 型から写した物を前に
for rid, e in used.items():
    resources.insert(0, e)
ET.indent(root, '    ')
# クリップの子要素を DTD の順に並べ直す（つないだタイトル等の後に filter-audio が来ると FCP が読み込めない）
ORDER = ['note', 'conform-rate', 'timeMap', 'adjust-crop', 'adjust-corners', 'adjust-conform', 'adjust-transform', 'adjust-blend',
         'adjust-volume', 'adjust-panner', 'mc-source', None, 'marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker',
         'filter-video', 'filter-video-mask', 'filter-audio', 'metadata']
for clip in root.iter():
    if clip.tag in ('mc-clip', 'asset-clip', 'clip', 'ref-clip', 'sync-clip'):
        kids = list(clip)
        key = lambda e: ORDER.index(e.tag) if e.tag in ORDER else ORDER.index(None)
        if [key(e) for e in kids] != sorted(key(e) for e in kids):
            kids.sort(key=key)  # 安定ソートなので同じ種類の中の順は保つ
            for e in list(clip):
                clip.remove(e)
            clip.extend(kids)
xml = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n' + ET.tostring(root, encoding='unicode')
open(out_path, 'w').write(xml)
print(out_path, f'{float(total):.2f}s', len(edl['segments']), 'cuts', len(edl.get('subs', [])), 'subs')
