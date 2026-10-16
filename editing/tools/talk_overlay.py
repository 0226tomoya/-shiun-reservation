"""対談・トーク動画（横 16:9）のカット済み XML に、川島さん本編（A4 shiunミュール）と同じ型のテロップとアイキャッチを重ねる。
    python3 talk_overlay.py BASE.fcpxml OVERLAY.json OUT.fcpxml

OVERLAY.json（時刻はアイキャッチを入れる前のタイムラインの秒）:
  {"wamu": true,
   "title": {"start": 秒, "line1": "青柳さんに聞いてみた", "line2": "shiun XSレビュー"},   # 左上の見出し（以後ずっと）
   "topics": [{"start": 秒, "end": 秒, "text": "①サイズの悩み"}],                        # 見出しの下の話題の箱（座布団01_07）
   "name_card": {"start": 秒, "role": "〇〇", "name": "青柳", "honorific": "さん"},         # ゲストの名前（5 秒）
   "subs": [{"start": 秒, "end": 秒, "text": "テロップ"}],
   "eyecatch": {"at": [秒, ...], "src": "file:///…/わむうアイキャッチ.mp4"},              # 話題の大きな切り替わりに本線へ挿入
   "pins": [{"at": 秒, "note": "人の判断が要る所"}]}

見た目（実物の値。川島さん本編のライブラリ CurrentVersion.fcpevent の ozml と、Paste の「わむうテンプレ(マスト)」から）:
  WAMU     : Paste の値に、完成版 6 本（A6〜A15）と同じ変形（位置 16.463, 10.1298・縮小 0.8）。基本タイトル・Futura MediumItalic「WAMU」68 ／「164cm / 58kg」33・文字の不透明度 0.5・中央揃え・行間 −10・
             位置 813.9, 440.4・下の行だけドロップシャドウ（Motion の既定: 黒 0.75・距離 5・角度 315）。
             下の行のアウトライン（幅 1.5・ブラー 10）とグローは FCPXML で書けないので付けない
  見出し   : 基本タイトル・コーポレート・ロゴ（FCPXML では font="Corporate Logo ver2"・fontFace なし。A6 の完成版の書き方。「Corporate Logo」+Bold は読めず Helvetica 6 になった＝A29 v2）「〇〇さんに聞いてみた」35 ⏎ 「題」60（改行の字は 63）・白・中央揃え・位置 −711.829, 485.271
  話題の箱 : 座布団01_07（MP_テロップパック）・Klee Medium 100・中央揃え・箱の不透明度 0.75・カスタム幅/高さ 8・オフセット −13.2 / −63・
             ポイント1 X 0.31688・ポイント2 X 0.81688・クリップの位置 −66.3611, 34.7593（見出しの下）
  名前     : 基本タイトル・コーポレート・ロゴ Bold「肩書き」35 ⏎「名前」70「さん」35・中央揃え・位置 600.501, −277.258・5.005 秒
  字幕     : 基本タイトル・游ゴシック Bold 45・ベースライン −8・白・中央揃え・行間 −21・頭に改行（1 行の字幕は下の行に出る）・
             位置 0, −432.992・クリップの位置 0, 3.7037。次の字幕まで出したまま（川島さん本編は 97.6% が隙間 0）
  アイキャッチ: 「わむうアイキャッチ」1.4014 秒（音つき）を本線に挿入。WAMU・見出し・話題の箱はアイキャッチの上には出さない
  縁取り（strokeColor）は書かない。影は telop_shadow.py（字幕＝ぼかした縁取りの代わりの文字の影、見出し・名前＝ドロップシャドウのフィルタ）
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from telop_shadow import SUB_TALK, halo, drop_effect, add_drop_shadow  # noqa: E402

BASIC = '.../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti'
ZABU_UID = '~/Titles.localized/MP_テロップパック/34_座布団/座布団01_07/座布団01_07.moti'
ZABU_SRC = ('file:///Users/modantaimusu/Library/Containers/com.apple.FinalCut/Data/Movies/Motion%20Templates.localized/Titles.localized/'
            'MP_%E3%83%86%E3%83%AD%E3%83%83%E3%83%95%E3%82%9A%E3%83%8F%E3%82%9A%E3%83%83%E3%82%AF/34_%E5%BA%A7%E5%B8%83%E5%9B%A3/'
            '%E5%BA%A7%E5%B8%83%E5%9B%A301_07/%E5%BA%A7%E5%B8%83%E5%9B%A301_07.moti')
KEY_POS = '9999/999166631/999166633/1/100/101'
KEY_FLAT = '9999/999166631/999166633/2/351'
KEY_ALIGN = '9999/999166631/999166633/2/354/999169573/401'
KEY_LS = '9999/999166631/999166633/2/354/999169573/404'
# 座布団01_07 の公開パラメータ（川島さん本編の「ブーツも欲しい」の値）
ZABU_PARAMS = [
    ('カスタム：幅', '9999/3296114725/3334349960/3/3334349967/2', '8'),
    ('カスタム：高さ', '9999/3296114725/3334349960/3/3334349967/3', '8'),
    ('ポイント1', '9999/3296114725/3296114728/2/1/12', '0.31688 0.5'),
    ('ポイント2', '9999/3296114725/3296114728/2/1/13', '0.81688 0.5'),
    ('不透明度', '9999/3296114749/3296122091/3296122092/2/353/113/141', '0.75'),
    ('オフセット：幅', '9999/3296114749/3296122091/3296122092/4/3296122137/214', '-13.2'),
    ('オフセット：高さ', '9999/3296114749/3296122091/3296122092/4/3296122137/215', '-63'),
    ('配置', '9999/3334349830/3296113261/3296113262/2/354/3143323677/401', '1 (水平方向に中央揃え)'),
]
EYE_DUR = Fr(84084, 60000)  # 1.4014 秒（川島さん本編の長さ）
LANE = {'wamu': 2, 'title': 3, 'sub': 4, 'topic': 5, 'name': 6}
CORP = {'font': 'Corporate Logo ver2', 'fontColor': '1 1 1 1', 'bold': '1', 'alignment': 'center'}  # A6 の完成版の書き方（書体の指定なし）


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fr(int(a), int(b))
    return Fr(s)


def ts(f):
    f = Fr(f)
    return f'{f.numerator}s' if f.denominator == 1 else f'{f.numerator}/{f.denominator}s'


def new_id(res, pre):
    ids = {e.get('id') for e in res}
    n = 1
    while f'{pre}{n}' in ids:
        n += 1
    return f'{pre}{n}'


class Overlay:
    def __init__(self, root):
        self.root = root
        self.res = root.find('resources')
        seq = root.find('.//project/sequence')
        fmt = next(f for f in self.res.findall('format') if f.get('id') == seq.get('format'))
        self.fd = T(fmt.get('frameDuration'))
        self.seq = seq
        self.spine = seq.find('spine')
        self.basic = self.effect('基本タイトル', BASIC)
        self.zabu = self.effect('座布団01_07', ZABU_UID, ZABU_SRC)
        self.tsn = 0
        self.eyes = []  # 挿入したアイキャッチ（挿入後のタイムラインの頭）
        self.reindex()

    def effect(self, name, uid, src=None):
        e = next((e for e in self.res.findall('effect') if e.get('uid') == uid), None)
        if e is None:
            a = {'id': new_id(self.res, 'r'), 'name': name, 'uid': uid}
            if src:
                a['src'] = src
            e = ET.SubElement(self.res, 'effect', a)
        return e.get('id')

    def reindex(self):
        self.items = [(T(c.get('offset')), T(c.get('duration')), c) for c in self.spine]

    def fr(self, t):
        return Fr(round(Fr(t) / self.fd)) * self.fd

    # ---- アイキャッチ（本線に挿入）----
    def insert_eyecatch(self, at_list, src):
        if not at_list:
            return []
        vf = ET.SubElement(self.res, 'format', {'id': new_id(self.res, 'r'), 'name': 'FFVideoFormat1080p2398',
                                                 'frameDuration': '1001/24000s', 'width': '1920', 'height': '1080', 'colorSpace': '1-1-1 (Rec. 709)'})
        aid = new_id(self.res, 'r')
        a = ET.SubElement(self.res, 'asset', {'id': aid, 'name': 'わむうアイキャッチ', 'start': '0s', 'duration': '34034/24000s',
                                               'hasVideo': '1', 'format': vf.get('id'), 'videoSources': '1',
                                               'hasAudio': '1', 'audioSources': '1', 'audioChannels': '2', 'audioRate': '48000'})
        ET.SubElement(a, 'media-rep', {'kind': 'original-media', 'src': src})
        # 切り替わりに一番近い本線の継ぎ目に入れる（後ろから入れると前の時刻が変わらない）
        placed = []
        for t in sorted(at_list, reverse=True):
            k = min(range(1, len(self.items)), key=lambda i: abs(self.items[i][0] - Fr(t)))
            placed.append(self.items[k][0])
            el = ET.Element('asset-clip', {'ref': aid, 'offset': ts(self.items[k][0]), 'name': 'わむうアイキャッチ',
                                           'duration': ts(EYE_DUR), 'start': '0s', 'format': vf.get('id'), 'tcFormat': 'NDF'})
            ET.SubElement(el, 'conform-rate', {'scaleEnabled': '0'})
            idx = list(self.spine).index(self.items[k][2])
            self.spine.insert(idx, el)
            for c in list(self.spine)[idx + 1:]:
                c.set('offset', ts(T(c.get('offset')) + EYE_DUR))
            self.reindex()
        placed.sort()
        # 元の時刻（挿入前）での継ぎ目
        self.eyes_src = placed
        self.eyes = [p + EYE_DUR * i for i, p in enumerate(placed)]
        seq_d = T(self.seq.get('duration') or '0s')
        if seq_d:
            self.seq.set('duration', ts(seq_d + EYE_DUR * len(placed)))
        return placed

    def map(self, t):
        """挿入前の時刻 → 挿入後の時刻"""
        t = Fr(t)
        return t + EYE_DUR * sum(1 for p in getattr(self, 'eyes_src', []) if p <= t)

    def split_eye(self, a, b):
        """[a, b)（挿入後の時刻）からアイキャッチの区間を抜いた区間の並び"""
        out, cur = [], a
        for e in self.eyes:
            if cur < e < b:
                out.append((cur, e))
                cur = e + EYE_DUR
            elif e <= cur < e + EYE_DUR:
                cur = e + EYE_DUR
        if b - cur > self.fd:
            out.append((cur, b))
        return [(x, y) for x, y in out if y - x > self.fd]

    def host(self, t):
        t = self.fr(t)
        for off, du, c in self.items:
            if off <= t < off + du and c.get('name') != 'わむうアイキャッチ':
                return c, T(c.get('start')) + (t - off)
        cand = [(off, du, c) for off, du, c in self.items if c.get('name') != 'わむうアイキャッチ' and off <= t] or self.items
        off, du, c = cand[-1]
        return c, T(c.get('start')) + (t - off)

    def tsid(self):
        self.tsn += 1
        return f'tov{self.tsn}'

    def title(self, t0, t1, lane, name, params, runs, transform=None, ref=None):
        """runs: [(文字, text-style の属性)]。t0, t1 は挿入後の時刻"""
        c, local = self.host(t0)
        dur = max(self.fd, self.fr(t1) - self.fr(t0))
        e = ET.Element('title', {'ref': ref or self.basic, 'lane': str(lane), 'offset': ts(local), 'name': name, 'start': '3600s', 'duration': ts(dur)})
        for k, v, key in params:
            ET.SubElement(e, 'param', {'name': k, 'key': key, 'value': v})
        tx = ET.SubElement(e, 'text')
        defs = []
        for s, attrs in runs:
            i = self.tsid()
            r = ET.SubElement(tx, 'text-style', {'ref': i})
            r.text = s
            defs.append((i, attrs))
        for i, attrs in defs:
            d = ET.SubElement(e, 'text-style-def', {'id': i})
            ET.SubElement(d, 'text-style', attrs)
        if transform:
            ET.SubElement(e, 'adjust-transform', transform)
        # mc-clip の子の順番（DTD）: adjust-*, mc-source の後、marker・filter-audio の前
        kids = list(c)
        pos = len(kids)
        for j, k in enumerate(kids):
            if k.tag in ('marker', 'chapter-marker', 'keyword', 'rating', 'analysis-marker', 'filter-video', 'filter-video-mask', 'filter-audio', 'metadata'):
                pos = j
                break
        c.insert(pos, e)
        return e

    def marker(self, t, note):
        c, local = self.host(t)
        kids = list(c)
        pos = len(kids)
        for j, k in enumerate(kids):
            if k.tag in ('filter-video', 'filter-video-mask', 'filter-audio', 'metadata'):
                pos = j
                break
        c.insert(pos, ET.Element('marker', {'start': ts(local), 'duration': ts(self.fd), 'value': '要判断: ' + note, 'completed': '0'}))


def basic_params(pos, align='1 (水平方向に中央揃え)', ls=None):
    p = [('位置', pos, KEY_POS), ('平坦化', '1', KEY_FLAT), ('配置', align, KEY_ALIGN)]
    if ls is not None:
        p.append(('行間', str(ls), KEY_LS))
    return p


def main():
    base, ovp, out = sys.argv[1:4]
    head = open(base, encoding='utf-8').read(400)
    tree = ET.parse(base)
    root = tree.getroot()
    o = Overlay(root)
    ov = json.load(open(ovp))
    ey = ov.get('eyecatch') or {}
    o.insert_eyecatch(ey.get('at', []), ey.get('src', ''))
    total = sum(du for _, du, _ in o.items)
    if ov.get('wamu'):
        # 完成版（A6〜A15）の書き方そのまま。影・縁は XML には出ていない
        st = {'font': 'Futura', 'fontFace': 'Medium Italic', 'fontColor': '1 1 1 0.5', 'italic': '1', 'alignment': 'center'}
        for a, b in o.split_eye(Fr(0), total):
            o.title(a, b, LANE['wamu'], 'WAMU - 基本タイトル', basic_params('813.916 440.387', ls=-10),
                    [('WAMU', {**st, 'fontSize': '68', 'lineSpacing': '-10'}), ('\n', {**st, 'fontSize': '33', 'lineSpacing': '-10'}), ('164cm / 58kg', {**st, 'fontSize': '33'})],
                    {'position': '16.463 10.1298', 'scale': '0.8 0.8'})
    drop = drop_effect(o.res, lambda: new_id(o.res, 'r'))
    tt = ov.get('title')
    if tt:
        for a, b in o.split_eye(o.map(tt['start']), total):
            e_ = o.title(a, b, LANE['title'], tt['line1'][:20] + ' - 基本タイトル', basic_params('-711.829 485.271'),
                         [(tt['line1'], {**CORP, 'fontSize': '35'}), ('\n', {**CORP, 'fontSize': '63'}), (tt['line2'], {**CORP, 'fontSize': '60'})])
            ET.SubElement(e_, 'adjust-blend', {'mode': '14 (オーバーレイ)'})  # 完成版 A6 の見出しと同じ合成モード
            add_drop_shadow(e_, drop)
    for tp in ov.get('topics', []):
        for a, b in o.split_eye(o.map(tp['start']), o.map(tp['end'])):
            o.title(a, b, LANE['topic'], tp['text'][:20] + ' - 座布団01_07', [(k, v, key) for k, key, v in ZABU_PARAMS],
                    [(tp['text'], {'font': 'Klee', 'fontSize': '100', 'fontFace': 'Medium', 'fontColor': '1 1 1 1', 'alignment': 'center'})],
                    {'position': '-66.3611 34.7593'}, ref=o.zabu)
    nc = ov.get('name_card')
    if nc:
        a = o.map(nc['start'])
        e_ = o.title(a, a + Fr(5005, 1000), LANE['name'], (nc.get('role') or nc['name'])[:20] + ' - 基本タイトル', basic_params('600.501 -277.258'),
                [(nc.get('role', '') + '\n', {**CORP, 'fontSize': '35'}), (nc['name'], {**CORP, 'fontSize': '70'}),
                 (nc.get('honorific', 'さん'), {**CORP, 'fontSize': '35'})])
        add_drop_shadow(e_, drop)
    sub_st = {'font': 'YuGothic', 'fontSize': '45', 'fontColor': '1 1 1 1', 'bold': '1', 'baseline': '-8', 'alignment': 'center', 'lineSpacing': '-21',
              **halo(*SUB_TALK)}
    for s in ov.get('subs', []):
        for a, b in o.split_eye(o.map(s['start']), o.map(s['end'])):
            o.title(a, b, LANE['sub'], s['text'][:20] + ' - 基本タイトル', basic_params('0 -432.992', ls=-21),
                    [('\n' + s['text'], sub_st)], {'position': '0 3.7037'})
    for p in ov.get('pins', []):
        o.marker(o.map(p['at']), p['note'])
    tree.write(out, encoding='UTF-8', xml_declaration=True)
    m = re.search(r'<!DOCTYPE[^>]*>', head)
    body = open(out, encoding='utf-8').read()
    body = body.replace("<?xml version='1.0' encoding='UTF-8'?>", '<?xml version="1.0" encoding="UTF-8"?>\n' + (m.group(0) if m else '<!DOCTYPE fcpxml>'), 1)
    open(out, 'w', encoding='utf-8').write(body)
    print(f"アイキャッチ {len(o.eyes)}・WAMU {1 if ov.get('wamu') else 0}・見出し {1 if tt else 0}・話題 {len(ov.get('topics', []))}・"
          f"名前 {1 if nc else 0}・字幕 {len(ov.get('subs', []))}・ピン {len(ov.get('pins', []))}・長さ {float(total):.1f} 秒")


if __name__ == '__main__':
    main()
