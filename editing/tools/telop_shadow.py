"""テロップの影（わむうの完成版の見た目）を FCPXML に書く。

完成版の影は 2 種類（2026-10 に 6 本の完成版 XML・川島さん本編のライブラリ・完成動画のコマで確認）:

1. 文字の「ぼかした縁取り」— ライブラリの中（Motion の ozml）では縁取り（アウトライン）が有効で、黒・ぼかし 10:
     対談の字幕（游ゴシック Bold 45） 不透明度 0.7（一部 0.5）・幅 3
     長編の事実・感想・縦書き（Klee・hanatotyoutyo） 不透明度 0.25・幅 2
     長編の YuGothic 30（コーデの一覧など） 不透明度 0.5・幅 2
   完成動画では文字のまわりにふわっと黒い影が出る。ところが FCPXML には縁取りのぼかしを書く所がなく、
   書き出すと strokeColor・strokeWidth だけが残る（読み込むと固い線になる＝A29 で「縁取りは書かない」になった理由）。
   そこで XML では、同じ見た目になるドロップシャドウ（距離 0・ぼかし 10）で書く → halo()
   ※ ozml の flags の 0x8000 が立っていれば無効（最下位ビットではない。fcpevent_titles.py の旧判定は誤り）

2. クリップに付ける「ドロップシャドウ」フィルタ（FxPlug）— 完成版の見出しの複合クリップ（A6「本編 クリップ 1」）・
   挿し込み画像（A12 のサムネ・A15 の公式サイトの画面）に、不透明度 0.75・ぼかし 30・位置 0.5 0・プリセット カスタム
   → add_drop_shadow()
"""
import xml.etree.ElementTree as ET

DROP_UID = 'FxPlug:9C13F991-BC99-4DC8-B150-381D7CCE183B'
# 完成版 A6 の「本編 クリップ 1」のドロップシャドウの effectConfig（FCP が書くそのまま）
DROP_CONFIG = ('YnBsaXN0MDDUAQIDBAUGBwpYJHZlcnNpb25ZJGFyY2hpdmVyVCR0b3BYJG9iamVjdHMSAAGGoF8QD05TS2V5ZWRBcmNoaXZlctEICVRyb290gAGlCwwV'
               'FhdVJG51bGzTDQ4PEBIUV05TLmtleXNaTlMub2JqZWN0c1YkY2xhc3OhEYACoROAA4AEXXBsdWdpblZlcnNpb24QAdIYGRobWiRjbGFzc25hbWVYJGNs'
               'YXNzZXNfEBNOU011dGFibGVEaWN0aW9uYXJ5oxocHVxOU0RpY3Rpb25hcnlYTlNPYmplY3QIERokKTI3SUxRU1lfZm55gIKEhoiKmJqfqrPJzdoAAAAA'
               'AAABAQAAAAAAAAAeAAAAAAAAAAAAAAAAAAAA4w==')
DROP_PARAMS = [('不透明度', '2', '0.75'), ('プリセット', '8', '3 (カスタム)'), ('ぼかし', '4', '30'),
               ('ブラー減衰', '5', '1'), ('位置', '3', '0.5 0'), ('遠近の量', '7', '0')]

# 文字の影の型（不透明度・ぼかし）。縁取りは太さ（幅 2〜3）がある分、同じ不透明度の影より濃く見えるので、
# 川島さん本編のコマ（字幕）と見比べて影の不透明度を縁取りの約 1.4 倍にした（0.7 → 1.0。scratchpad の halo_cmp2.png）
SUB_TALK = (1.0, 10)      # 対談の字幕（縁取り 0.7・幅 3）
TEL_LONG = (0.35, 10)     # 長編の事実・感想・縦書き（縁取り 0.25・幅 2）
LIST_LONG = (0.7, 10)     # 長編のコーデの一覧など（縁取り 0.5・幅 2）


def halo(opacity, blur=10):
    """ぼかした縁取りの代わりの、文字のドロップシャドウ（text-style の属性）"""
    return {'shadowColor': f'0 0 0 {opacity:g}', 'shadowOffset': '0 315', 'shadowBlurRadius': f'{blur:g}'}


def drop_effect(resources, new_id):
    """resources に「ドロップシャドウ」の effect が無ければ足し、その id を返す"""
    for e in resources.findall('effect'):
        if e.get('uid') == DROP_UID:
            return e.get('id')
    rid = new_id()
    ET.SubElement(resources, 'effect', {'id': rid, 'name': 'ドロップシャドウ', 'uid': DROP_UID})
    return rid


def add_drop_shadow(clip, effect_id):
    """クリップ（title・video・ref-clip）にドロップシャドウのフィルタを付ける（既にあれば何もしない）。
    DTD（v1.13）の title は …anchor*, marker*, filter-video*, metadata? の順なので、
    既にある filter-video の先頭（フェードの前＝先に影）か、metadata の前か、末尾に入れる"""
    if any(f.get('ref') == effect_id for f in clip.findall('filter-video')):
        return
    fv = ET.Element('filter-video', {'ref': effect_id, 'name': 'ドロップシャドウ'})
    d = ET.SubElement(fv, 'data', {'key': 'effectConfig'})
    d.text = DROP_CONFIG
    for nm, k, v in DROP_PARAMS:
        ET.SubElement(fv, 'param', {'name': nm, 'key': k, 'value': v})
    kids = list(clip)
    idx = next((i for i, c in enumerate(kids) if c.tag in ('filter-video', 'filter-video-mask', 'filter-audio', 'metadata')), len(kids))
    clip.insert(idx, fv)
