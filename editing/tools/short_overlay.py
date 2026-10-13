"""ユーザーがカットを確定した FCPXML に、字幕・商品カード・商品画像・効果音・BGM・調整レイヤーを足す。
本線（spine の mc-clip・asset-clip）には一切手を触れない。文字列のまま差し込むので、ユーザーの XML の書き方・順番はそのまま残る。

    python3 short_overlay.py BASE.fcpxml overlay_A.json [overlay_B.json …] --out OUT.fcpxml [--only] [--log LOG.json]

- BASE: ユーザーが FCP から書き出した Info.fcpxml（4 プロジェクト入り）
- overlay_*.json: プロジェクトごとの指示（下）。複数渡すと 1 本の fcpxml にまとめる
- --only: 指示を渡したプロジェクトだけを残す（1 本ずつの書き出し用）
- イベントの中身（ブラウザのクリップ・キーワードコレクション）は書き出さない（プロジェクトだけ）。resources は全部残す。

指示 JSON（時刻は「カットの番号」で書く。カット = プロジェクトの spine の子の順番 0, 1, 2 …）:
{
 "project": "shiun_ショート_カーコート",          # プロジェクト名（NFC で比べる）
 "adjustment": true,                              # 調整レイヤー（lane 1・全体・scale 1.15・position 0 7.34375）。既にあれば足さない
 "bgm": true,                                     # ES_Cherry Blossom −28dB を頭から終わりまで（lane −2）
 "subs":   [{"a": 4, "b": 5, "text": "今年の秋冬の"}],               # a〜b のカット（両端を含む）に 1 枚。"t0"/"t1"（秒）で途中から・途中まで
 "cards":  [{"kind": "product", "a": 2, "b": 3, "lines": ["SOFT GRAIN CAR COAT", "Color : BLACK | Size : XS, S, M"],
             "image": "完パケ/SNS用高画質/3.SOFT GRAIN CAR COAT/00001カー.jpg", "se": true},
            {"kind": "price", "a": 61, "b": 62, "lines": [...], "se": true, "y": 35.3501},
            {"kind": "release", "a": 63, "b": 65},
            {"kind": "height", "a": 47, "b": 49, "text": "164cm / Size : S"}],
 "inserts": [{"a": 4, "b": 8, "image": "完パケ/SNS用高画質/3.SOFT GRAIN CAR COAT/00002カー.jpg"}]  # 任意で "scale", "position"
}
- 画像のパスは「A24 shiun10月ラインナップ/」から先（NFC）。resources にある asset をそのまま使う（無ければ止まる）。
- 型（書式・数値）はユーザーがカーコートの冒頭で直したものを写す（KNOW: editing/knowledge/shiun_ショートの決まり.md の「カーコート冒頭の型」）。
"""
import json
import re
import sys
import unicodedata as ud
from fractions import Fraction as F
from urllib.parse import unquote
from xml.sax.saxutils import escape

FD = F(1001, 60000)  # 59.94p の 1 コマ
N = lambda s: ud.normalize('NFC', s or '')
NL = '\u2028'  # テロップの中の改行（差し込むときの字下げから守る）


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return F(int(a), int(b))
    return F(s)


def ts(f):
    """有理数の秒 → 'N/60000s'（ユーザーの XML と同じ分母）"""
    f = F(f)
    if f == 0:
        return '0s'
    v = f * 60000
    if v.denominator == 1:
        return f'{v.numerator}/60000s'
    return f'{f.numerator}/{f.denominator}s'


def snap(sec):
    return round(F(sec) / FD) * FD


def width(text):
    """字数（全角 1・半角 0.5）"""
    return sum(0.5 if ord(c) < 0x2000 else 1 for c in text)


# ---------- 型（カーコート冒頭でユーザーが直した値をそのまま） ----------
SUB_POS = '3.5 -415'
SUB_STYLE = 'font="Klee" fontSize="28" fontFace="Demibold" fontColor="1 1 1 1" bold="1" baseline="405"'  # 縁取りは付けない（XML ではぼかしが書けないため、ユーザー指示で削除）
ADJ_TF = '<adjust-transform position="0 7.34375" scale="1.15 1.15" />'
IMG_SCALE, IMG_POS = '1.5 1.5', '0.572917 0'  # SNS 用高画質（5:6）を縦いっぱいに
SE_DUR = F(37037, 60000)
CARD_POS = {'product': '-2.04 2.97505', 'price': '-2.04 35.3501'}
VOLFADE = ('<adjust-volume>\n<param name="amount">\n<fadeIn type="easeIn" duration="839/720000s" />\n'
           '<fadeOut type="easeIn" duration="782/720000s" />\n</param>\n</adjust-volume>')

BGM_ASSET = ('<asset id="{id}" name="ES_Cherry Blossom (Instrumental Version) - Nyck Caution" uid="2CE7CDC29015E66BF81A008094D9522A" '
             'start="0s" duration="5893953/48000s" hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000">\n'
             '            <media-rep kind="original-media" sig="2CE7CDC29015E66BF81A008094D9522A" '
             'src="file:///Users/modantaimusu/Downloads/%E3%82%A8%E3%83%95%E3%82%A7%E3%82%AF%E3%83%88/BGM/%E4%BD%BF%E3%81%88%E3%82%8B%E3%81%8B%E3%82%82/'
             'ES_Cherry%20Blossom%20(Instrumental%20Version)%20-%20Nyck%20Caution.mp3" />\n        </asset>')
CUSTOM_EFFECT = '<effect id="{id}" name="カスタム" uid=".../Titles.localized/Build In:Out.localized/Custom.localized/Custom.moti" />'


class Ctx:
    def __init__(self, base_text):
        self.text = base_text
        self.res_start = base_text.index('<resources>')
        self.res_end = base_text.index('</resources>')
        res = base_text[self.res_start:self.res_end]
        ids = [int(x) for x in re.findall(r'\bid="r(\d+)"', res)]
        self.next_id = max(ids) + 1
        self.new_res = []
        self.ts_n = 0
        # 画像の asset: パス（NFC・「A24 shiun10月ラインナップ/」から先）→ id
        self.img = {}
        for m in re.finditer(r'<asset id="(r\d+)"[^>]*>\s*<media-rep[^>]*src="([^"]+)"', res):
            src = N(unquote(m.group(2)))
            if 'A24 shiun10月ラインナップ/' in src:
                self.img[src.split('A24 shiun10月ラインナップ/', 1)[1]] = m.group(1)
        # 効果・書式の id
        self.eff = {N(m.group(2)): m.group(1) for m in re.finditer(r'<effect id="(r\d+)" name="([^"]+)"', res)}
        resn = N(res)  # 名前は NFD で書かれていることがある（「ボ」など）
        self.se_id = re.search(r'<asset id="(r\d+)" name="決定ボタンを押す32"', resn).group(1)
        # 効果音・BGM の format は、ユーザーが置いた効果音と同じもの
        self.rate_undef = re.search(r'<asset-clip ref="' + self.se_id + r'"[^>]*format="(r\d+)"', N(base_text)).group(1)
        # カラー調整（ユーザーがカーコートの商品画像に付けたもの）をそのまま写す
        m = re.search(r'<filter-video ref="(r\d+)" name="カラー調整">.*?</filter-video>', base_text, re.S)
        self.color_filter = m.group(0)
        # 画像のキーワード（イベントのクリップに付いているもの → タイムラインの video では小文字）
        self.kw = {}
        for m in re.finditer(r'<clip name="[^"]*"[^>]*>\s*<video ref="(r\d+)"[^>]*/>\s*<keyword [^>]*value="([^"]+)"', base_text):
            self.kw[m.group(1)] = m.group(2)
        self.bgm_id = None
        self.custom_id = None

    def rid(self):
        r = f'r{self.next_id}'
        self.next_id += 1
        return r

    def tsid(self):
        self.ts_n += 1
        return f'tsov{self.ts_n}'

    def bgm(self):
        if not self.bgm_id:
            self.bgm_id = self.rid()
            self.new_res.append(BGM_ASSET.format(id=self.bgm_id))
        return self.bgm_id

    def custom(self):
        if not self.custom_id:
            self.custom_id = self.eff.get('カスタム') or self.rid()
            if 'カスタム' not in self.eff:
                self.new_res.append(CUSTOM_EFFECT.format(id=self.custom_id))
        return self.custom_id

    def image(self, rel):
        rel = N(rel)
        if rel not in self.img:
            raise SystemExit(f'画像が resources にありません: {rel}')
        return self.img[rel]


# ---------- spine の解析（文字列の位置つき） ----------
def spine_children(proj_text):
    """spine の直下の子（mc-clip・asset-clip など）の (開始, 終了, タグ, 属性) を順に返す"""
    s = proj_text.index('<spine>') + len('<spine>')
    e = proj_text.index('</spine>')
    out = []
    pos = s
    tag_re = re.compile(r'<(/?)([\w-]+)([^>]*?)(/?)>', re.S)
    depth = 0
    start = None
    for m in tag_re.finditer(proj_text, s, e):
        close, name, attrs, selfclose = m.group(1), m.group(2), m.group(3), m.group(4)
        if not close:
            if depth == 0:
                start = m.start()
                cur = (name, dict(re.findall(r'([\w:-]+)="([^"]*)"', attrs)))
            if selfclose:
                if depth == 0:
                    out.append((start, m.end(), cur[0], cur[1]))
            else:
                depth += 1
        else:
            depth -= 1
            if depth == 0:
                out.append((start, m.end(), cur[0], cur[1]))
    return out


AFTER_ANCHORS = ('marker', 'chapter-marker', 'rating', 'keyword', 'analysis-marker', 'filter-audio', 'filter-video', 'audio-channel-source', 'audio-role-source')


def insert_point(clip_text):
    """クリップの中で、つなぐ要素を入れる位置（DTD の順: … mc-source → つなぐ物 → マーカー → filter）"""
    tag_re = re.compile(r'<(/?)([\w-]+)([^>]*?)(/?)>', re.S)
    depth = 0
    for m in tag_re.finditer(clip_text):
        close, name, _, selfclose = m.groups()
        if not close:
            if depth == 1 and name in AFTER_ANCHORS:
                return m.start()
            if not selfclose:
                depth += 1
        else:
            depth -= 1
            if depth == 0:
                return m.start()
    raise ValueError('clip の終わりが見つからない')


# ---------- 要素の XML ----------
def title_sub(ctx, text, lane, off, dur):
    a, b = ctx.tsid(), ctx.tsid()
    body, last = escape(text[:-1]), escape(text[-1])
    return f'''<title ref="{ctx.eff['基本タイトル']}" lane="{lane}" offset="{ts(off)}" name="{escape(text)} - 基本タイトル" start="3600s" duration="{ts(dur)}">
    <param name="位置" key="9999/999166631/999166633/1/100/101" value="{SUB_POS}" />
    <param name="平坦化" key="9999/999166631/999166633/2/351" value="1" />
    <param name="配置" key="9999/999166631/999166633/2/354/999169573/401" value="1 (水平方向に中央揃え)" />
    <param name="行間" key="9999/999166631/999166633/2/354/999169573/404" value="-21" />
    <param name="disableDRT" key="3733" value="1" />
    <text>
        <text-style ref="{a}">{body}</text-style>
        <text-style ref="{b}">{last}</text-style>
    </text>
    <text-style-def id="{a}">
        <text-style {SUB_STYLE} kerning="1.4" alignment="center" lineSpacing="-21">
            <param name="MotionSimpleValues" key="MotionTextStyle:SimpleValues">
                <param name="motionTextTracking" key="tracking" value="1.4" />
            </param>
        </text-style>
    </text-style-def>
    <text-style-def id="{b}">
        <text-style {SUB_STYLE} alignment="center" lineSpacing="-21" />
    </text-style-def>
    <adjust-colorConform enabled="1" autoOrManual="manual" conformType="conformNone" peakNitsOfPQSource="1000" peakNitsOfSDRToPQSource="203" />
</title>'''


def title_card(ctx, lines, lane, off, dur, pos):
    """商品名・価格カード（ユーザーの商品名テロップ: Masqualero 45・調整 1 1.4・行間 −3・scale 0.7）"""
    a = ctx.tsid()
    txt = escape(NL.join(lines))  # 文中の改行は字下げを足さないよう、差し込みの最後に戻す
    return f'''<title ref="{ctx.eff['基本タイトル']}" lane="{lane}" offset="{ts(off)}" name="{escape(lines[0])} - 基本タイトル" start="3600s" duration="{ts(dur)}">
    <param name="位置" key="9999/999166631/999166633/1/100/101" value="{pos}" />
    <param name="調整" key="9999/999166631/999166633/1/100/105" value="1 1.4" />
    <param name="平坦化" key="9999/999166631/999166633/2/351" value="1" />
    <param name="配置" key="9999/999166631/999166633/2/354/3369912973/401" value="1 (水平方向に中央揃え)" />
    <param name="行間" key="9999/999166631/999166633/2/354/3369912973/404" value="-3" />
    <param name="配置" key="9999/999166631/999166633/2/354/999169573/401" value="1 (水平方向に中央揃え)" />
    <param name="行間" key="9999/999166631/999166633/2/354/999169573/404" value="-3" />
    <text>
        <text-style ref="{a}">{txt}</text-style>
    </text>
    <text-style-def id="{a}">
        <text-style font="Masqualero" fontSize="45" fontColor="1 1 1 1" bold="1" alignment="center" lineSpacing="-3" />
    </text-style-def>
    <adjust-transform scale="0.7 0.7" />
</title>'''


def title_release(ctx, text, lane, off, dur):
    """発売日カード（前の版 v5 の型: Masqualero 30・調整 1.05 1.6092・行間 −7・scale 0.9）"""
    a = ctx.tsid()
    return f'''<title ref="{ctx.eff['基本タイトル']}" lane="{lane}" offset="{ts(off)}" name="{escape(text)} - 基本タイトル" start="3600s" duration="{ts(dur)}">
    <param name="位置" key="9999/999166631/999166633/1/100/101" value="0.17325 -13.6782" />
    <param name="調整" key="9999/999166631/999166633/1/100/105" value="1.05 1.6092" />
    <param name="平坦化" key="9999/999166631/999166633/2/351" value="1" />
    <param name="配置" key="9999/999166631/999166633/2/354/999169573/401" value="1 (水平方向に中央揃え)" />
    <param name="行間" key="9999/999166631/999166633/2/354/999169573/404" value="-7" />
    <text>
        <text-style ref="{a}">{escape(text)}</text-style>
    </text>
    <text-style-def id="{a}">
        <text-style font="Masqualero" fontSize="30" fontColor="1 1 1 1" bold="1" alignment="center" lineSpacing="-7" />
    </text-style-def>
    <adjust-transform scale="0.9 0.9" />
</title>'''


def title_height(ctx, text, lane, off, dur):
    """身長ラベル（前の版 v5 の型: カスタム・Masqualero 25・右揃え・右上）"""
    a = ctx.tsid()
    return f'''<title ref="{ctx.custom()}" lane="{lane}" offset="{ts(off)}" name="{escape(text)} - カスタム" start="3600s" duration="{ts(dur)}">
    <param name="位置" key="9999/10199/10201/1/100/101" value="56.9125 -37.8" />
    <param name="調整" key="9999/10199/10201/1/100/105" value="1 1.4" />
    <param name="配置" key="9999/10199/10201/2/354/1002961760/401" value="2 (右揃え)" />
    <param name="Out Sequencing" key="9999/10199/10201/4/10233/201/202" value="0 (終了)" />
    <text>
        <text-style ref="{a}">{escape(text)}</text-style>
    </text>
    <text-style-def id="{a}">
        <text-style font="Masqualero" fontSize="25" fontColor="1 1 1 1" bold="1" alignment="right" />
    </text-style-def>
    <adjust-transform position="20.0417 37.526" />
</title>'''


def video_img(ctx, rel, lane, off, dur, scale=IMG_SCALE, pos=IMG_POS):
    rid = ctx.image(rel)
    name = rel.rsplit('/', 1)[1].rsplit('.', 1)[0]
    kw = ctx.kw.get(rid)
    kwx = f'\n    <keyword start="3600s" duration="10s" value="{escape(kw.lower())}" />' if kw else ''
    return f'''<video ref="{rid}" lane="{lane}" offset="{ts(off)}" name="{escape(name)}" start="3600s" duration="{ts(dur)}">
    <adjust-transform position="{pos}" scale="{scale}" />{kwx}
    {ctx.color_filter}
</video>'''


def se_clip(ctx, off):
    return f'''<asset-clip ref="{ctx.se_id}" lane="-1" offset="{ts(off)}" name="決定ボタンを押す32" duration="{ts(SE_DUR)}" format="{ctx.rate_undef}" audioRole="dialogue">
    {VOLFADE}
</asset-clip>'''


def bgm_clip(ctx, off, dur):
    return f'''<asset-clip ref="{ctx.bgm()}" lane="-2" offset="{ts(off)}" name="ES_Cherry Blossom (Instrumental Version) - Nyck Caution" duration="{ts(dur)}" format="{ctx.rate_undef}" audioRole="music" start="0s">
    <adjust-volume amount="-28dB">
        <param name="amount">
            <fadeOut type="easeIn" duration="589589/720000s" />
        </param>
    </adjust-volume>
</asset-clip>'''


def adj_layer(ctx, off, dur):
    return f'''<title ref="{ctx.eff['Adjustment Layer']}" lane="1" offset="{ts(off)}" name="Adjustment Layer" start="107999892/30000s" duration="{ts(dur)}">
    {ADJ_TF}
</title>'''


# ---------- 1 プロジェクト ----------
def build_project(ctx, proj_text, ov, log):
    kids = spine_children(proj_text)
    cuts = []
    for (s, e, tag, at) in kids:
        cuts.append(dict(s=s, e=e, tag=tag, off=T(at.get('offset')), start=T(at.get('start')), dur=T(at.get('duration')), name=at.get('name')))
    end_all = cuts[-1]['off'] + cuts[-1]['dur']
    seq_dur = T(re.search(r'<sequence [^>]*duration="([^"]+)"', proj_text).group(1))
    assert end_all == seq_dur, (end_all, seq_dur)

    def t_of(idx, which, override=None):
        if override is not None:
            return snap(override)
        if idx == 'end':
            return end_all
        c = cuts[idx]
        return c['off'] if which == 'a' else c['off'] + c['dur']

    def host(t):
        for i, c in enumerate(cuts):
            if c['off'] <= t < c['off'] + c['dur']:
                return i
        raise ValueError(t)

    # 既にある「つないだ要素」（ユーザーが直した所）を占有として読む
    occ = {}  # lane → [(t0, t1, 種類)]
    existing = {'adj': False}
    for c in cuts:
        ct = proj_text[c['s']:c['e']]
        for m in re.finditer(r'<(title|video|asset-clip)\b([^>]*)>', ct):
            at = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(2)))
            if 'lane' not in at:
                continue
            t0 = c['off'] + T(at['offset']) - c['start']
            t1 = t0 + T(at['duration'])
            occ.setdefault(int(at['lane']), []).append((t0, t1, 'user:' + at.get('name', '')))
            if at.get('name') == 'Adjustment Layer':
                existing['adj'] = True
    adds = {}  # spine の子の番号 → [xml]

    def free(lane, t0, t1):
        return all(t1 <= a or t0 >= b for a, b, _ in occ.get(lane, []))

    def put(xml_fn, t0, t1, lane, kind, bump=True):
        while bump and not free(lane, t0, t1):
            lane += 1 if lane > 0 else -1
        occ.setdefault(lane, []).append((t0, t1, kind))
        i = host(t0)
        off = cuts[i]['start'] + (t0 - cuts[i]['off'])
        adds.setdefault(i, []).append(xml_fn(lane, off, t1 - t0))
        log.append(dict(kind=kind, t0=float(t0), t1=float(t1), lane=lane, cut=i))
        return lane

    # 調整レイヤー
    if ov.get('adjustment') and not existing['adj']:
        put(lambda L, o, d: adj_layer(ctx, o, d), F(0), end_all, 1, 'adjustment', bump=False)
    # 画像（インサート）
    for ins in ov.get('inserts', []):
        t0, t1 = t_of(ins['a'], 'a', ins.get('t0')), t_of(ins['b'], 'b', ins.get('t1'))
        put(lambda L, o, d, ins=ins: video_img(ctx, ins['image'], L, o, d, ins.get('scale', IMG_SCALE), ins.get('position', IMG_POS)),
            t0, t1, 2, 'image:' + ins['image'].rsplit('/', 1)[1])
    # カード
    for c in ov.get('cards', []):
        t0, t1 = t_of(c['a'], 'a', c.get('t0')), t_of(c.get('b', c['a']), 'b', c.get('t1'))
        if c.get('frames'):
            t1 = t0 + c['frames'] * FD
        if c.get('image'):
            put(lambda L, o, d, c=c: video_img(ctx, c['image'], L, o, d), t0, t1, 2, 'image:' + c['image'].rsplit('/', 1)[1])
        if c['kind'] in ('product', 'price'):
            pos = c.get('pos') or CARD_POS[c['kind']]
            put(lambda L, o, d, c=c, pos=pos: title_card(ctx, c['lines'], L, o, d, pos), t0, t1, 3, c['kind'] + ':' + c['lines'][0])
        elif c['kind'] == 'release':
            put(lambda L, o, d, c=c: title_release(ctx, c.get('text', '2026.10.31 sat 10pm - Release'), L, o, d), t0, t1, 3, 'release')
        elif c['kind'] == 'height':
            put(lambda L, o, d, c=c: title_height(ctx, c['text'], L, o, d), t0, t1, 3, 'height:' + c['text'])
        if c.get('se'):
            put(lambda L, o, d: se_clip(ctx, o), t0, t0 + SE_DUR, -1, 'se')
    # 字幕
    for sb in ov.get('subs', []):
        t0, t1 = t_of(sb['a'], 'a', sb.get('t0')), t_of(sb['b'], 'b', sb.get('t1'))
        if width(sb['text']) > 18:
            raise SystemExit(f"字幕が 18 字を超えています: {sb['text']}")
        put(lambda L, o, d, sb=sb: title_sub(ctx, sb['text'], L, o, d), t0, t1, 2, 'sub:' + sb['text'])
    # BGM
    if ov.get('bgm'):
        put(lambda L, o, d: bgm_clip(ctx, o, d), F(0), end_all, -2, 'bgm', bump=False)

    # 後ろから差し込む（前の位置がずれないように）
    out = proj_text
    for i in sorted(adds, reverse=True):
        c = cuts[i]
        ct = out[c['s']:c['e']]
        p = insert_point(ct)
        # 直前の改行・字下げのあとに差し込み、元の行の字下げを保つ
        head = ct[:p]
        m = re.search(r'\n([ \t]*)$', head)
        if m:
            indent = m.group(1)
            block = ''.join(x.replace('\n', '\n' + indent) + '\n' + indent for x in adds[i])
            ct2 = head + block + ct[p:]
        else:
            ct2 = head + ''.join(adds[i]) + ct[p:]
        out = out[:c['s']] + ct2.replace(NL, '\n') + out[c['e']:]
    return out


def main():
    args = sys.argv[1:]
    out_path = args[args.index('--out') + 1]
    only = '--only' in args
    files = [a for a in args if a.endswith('.json') and not (args.index(a) > 0 and args[args.index(a) - 1] == '--log')]
    base = [a for a in args if a.endswith('.fcpxml')][0]
    text = open(base, encoding='utf-8').read()
    ctx = Ctx(text)
    ovs = [json.load(open(f, encoding='utf-8')) for f in files]
    # プロジェクトの位置
    projs = [(m.start(), text.index('</project>', m.start()) + len('</project>'), N(m.group(1)))
             for m in re.finditer(r'<project name="([^"]+)"', text)]
    logs = {}
    new_proj = {}
    for ov in ovs:
        hit = [p for p in projs if p[2] == N(ov['project'])]
        if not hit:
            raise SystemExit(f"プロジェクトが見つかりません: {ov['project']}")
        s, e, name = hit[0]
        log = []
        new_proj[name] = build_project(ctx, text[s:e], ov, log)
        logs[name] = log
    # イベントはプロジェクトだけにする
    ev_s = text.index('<event')
    ev_open_end = text.index('>', ev_s) + 1
    ev_e = text.index('</event>')
    m = re.search(r'\n([ \t]*)<project', text)
    indent = m.group(1)
    keep = []
    for s, e, name in projs:
        if only and name not in new_proj:
            continue
        keep.append(new_proj.get(name, text[s:e]))
    event_body = ''.join('\n' + indent + p for p in keep) + '\n' + indent[:-4]
    res_add = ''.join('\n        ' + r for r in ctx.new_res)
    out = (text[:ctx.res_end].rstrip() + res_add + '\n    ' + text[ctx.res_end:ev_open_end] + event_body + text[ev_e:])
    if '--no-outline' in args:
        # 縁取り（アウトライン）を消す。FCPXML には縁取りのぼかしの項目が無く、FCP で読み込むとぼかし 0 になるため（ユーザー指示）
        out = re.sub(r'\s(?:strokeColor|strokeWidth)="[^"]*"', '', out)
    open(out_path, 'w', encoding='utf-8').write(out)
    if '--log' in args:
        json.dump(logs, open(args[args.index('--log') + 1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for name, log in logs.items():
        from collections import Counter
        c = Counter(l['kind'].split(':')[0] for l in log)
        print(name, dict(c))
    print('→', out_path)


if __name__ == '__main__':
    main()
