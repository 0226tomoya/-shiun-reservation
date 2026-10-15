"""ショートの「カット済みの本線」と「発言（時刻つき）」と「商品情報」から、字幕・カード・効果音・BGM を自動で置く（8 月の型）。
    python3 short_overlay_auto.py IN.json OUT.json [PARAMS.json]
IN: {"length", "cuts": [[頭, 長さ]...], "words": [[頭, 終わり, 字]...], "product": {...}}
  product: {"name_hint": ["ヘンリー", ...]（発言の中の商品の呼び方）, "has_sizetable", "heights": [158,165,...], "colors": [...]}
OUT: {"subs": [[頭, 長さ, 文]], "cards": [[頭, 長さ, 文, 種類]], "se": [[頭]], "bgm": [[名前, 音量]]}
決まり（8 月の 4 本・字幕 166 枚から。PARAMS で変えられる）:
  - 字幕は本線の編集点で始まり、次の字幕の頭まで続ける（すき間 0）。字数が target 字を超えるか文の切れ目でつぎの字幕に替える
  - 1 枚は 1〜4 カットをまたぐ（中央値 2）。1 枚の長さは max_dur 秒まで
  - 商品名カード（＋効果音）は、発言で商品の呼び方が最初に出たカットの頭。価格カード（＋効果音）は「円」「価格」の発言のカット。発売日カードは最後の 4.5 秒
  - カードが出ている間は字幕を出さない
"""
import json
import re
import sys

P = {'target': 11, 'max_chars': 22, 'max_dur': 4.0, 'min_dur': 0.6, 'card_dur': 2.0, 'price_dur': 5.5, 'release_dur': 4.5, 'size_dur': 4.6, 'lag': 0.2, 'word_lag': 0.0, 'snap_lo': -0.3, 'snap_hi': 0.35, 'bgm': ['ES_Bumfuzzle - Jobii', '-28dB'], 'chunk': 'cut', 'max_merge': 0, 'merge_dur': 2.6, 'color_dur': 1.95, 'height_step': 1.034, 'ins_max': 4.6, 'detail_re': '生地|素材|丈感|着丈|北が|涼しく|ディテール|シルエット|ソール|インソール|本革', 'min_chars': 6, 'min_punct': 3, 'gap_split': 0.0, 'chunk_snap': 0.35}
SENT_END = re.compile(r'[。！？!?]$|(ます|です|した|ない|ません|よね|けど|から|ので|ね|よ)$')


def cut_texts(cuts, words, lag=0.0):
    out = []
    for t0, du in cuts:
        t1 = t0 + du
        out.append(''.join(w for a, b, w in words if a - lag >= t0 - 0.02 and a - lag < t1 - 0.02))
    return out


END_MARK = re.compile(r'(が|を|けど|けれど|し|から|ので|ば|ですが|には|ために|ても|でも|て|に|は|と|ます|ました|です|ない|た|ね|よ)$')


def cut_chunks(cuts, tx, busy, p):
    subs, cur = [], None
    for (t0, du), t in zip(cuts, tx):
        if any(a - 0.01 <= t0 < b - 0.01 for a, b in busy):
            if cur: subs.append(cur); cur = None
            continue
        if not t:
            if cur: cur[1] = t0 + du - cur[0]
            continue
        if cur is None:
            cur = [t0, du, t]
            continue
        n = len(cur[2]) + len(t)
        prev = cur[2].rstrip()
        # 先読み: このカットで文が終わり、合わせても max_merge 字・merge_dur 秒以内なら 1 枚にまとめる
        if not prev.endswith('。') and t.rstrip().endswith('。') and n <= p['max_merge'] and t0 + du - cur[0] <= p['merge_dur']:
            cur[1] = t0 + du - cur[0]; cur[2] += t
            continue
        mark = prev.endswith(('。', '、')) or (END_MARK.search(prev.rstrip('。、')) and len(prev) >= p['min_chars'])
        if len(cur[2]) >= p['target'] or n > p['max_chars'] or SENT_END.search(cur[2]) or mark or t0 + du - cur[0] > p['max_dur']:
            subs.append(cur); cur = [t0, du, t]
        else:
            cur[1] = t0 + du - cur[0]; cur[2] += t
    if cur: subs.append(cur)
    return subs


def text_chunks(words, cuts, busy, p):
    """言葉で区切る（文節の終わり・句読点・字数）→ 区切りを一番近い編集点に寄せる"""
    starts = [c0 for c0, _ in cuts]

    def near(t):
        c = [c0 for c0 in starts if abs(c0 - t) <= p['chunk_snap']]
        return min(c, key=lambda c0: abs(c0 - t)) if c else None

    def in_card(t):
        return any(a - 0.05 <= t < b - 0.05 for a, b in busy)

    chunks, cur, t_cur = [], '', None
    for i, (a, b, w) in enumerate(words):
        a -= p['lag']
        if in_card(a):
            if cur: chunks.append([t_cur, cur]); cur = ''
            continue
        clean = w.replace('。', '').replace('、', '')
        if not cur:
            t_cur = a
        cur += clean
        nxt_gap = (words[i + 1][0] - b) if i + 1 < len(words) else 9
        punct = w.endswith(('。', '、')) or (i + 1 < len(words) and words[i + 1][2].startswith(('。', '、')))
        L = len(cur)
        if (punct and L >= p['min_punct']) or (END_MARK.search(clean) and L >= p['min_chars'] and (nxt_gap > p['gap_split'] or L >= p['target'])) or L >= p['max_chars']:
            chunks.append([t_cur, cur]); cur = ''
    if cur: chunks.append([t_cur, cur])
    subs = []
    for t, txt in chunks:
        if not txt: continue
        c = near(t)
        t0 = c if c is not None else t
        if subs and t0 <= subs[-1][0] + 0.05:
            subs[-1][2] += txt; continue
        subs.append([round(t0, 3), 1.0, txt])
    for i, s_ in enumerate(subs):
        nxt = subs[i + 1][0] if i + 1 < len(subs) else s_[0] + 1.6
        s_[1] = round(max(0.3, nxt - s_[0]), 3)
    return subs


def predict(inp, p=P):
    cuts, words, L = inp['cuts'], inp['words'], inp['length']
    tx = cut_texts(cuts, words, p.get('word_lag', 0.0))
    pr = inp.get('product', {})
    cards, se = [], []
    flat, pos = '', []  # 発言をつないだ文字列と、1 字ごとの時刻
    for a, b, w in words:
        for ch in w:
            flat += ch; pos.append(a)

    def at(i):  # 文字起こしの時刻は声より少し遅れるので lag 秒戻す
        return (pos[min(i, len(pos) - 1)] - p['lag']) if pos else 0.0

    def snap(t):
        """発言の時刻 t に一番近いカットの頭（t の snap_lo〜snap_hi 秒の範囲）"""
        c = [c0 for c0, _ in cuts if p['snap_lo'] <= c0 - t <= p['snap_hi']]
        return min(c, key=lambda c0: abs(c0 - t)) if c else t

    hint = pr.get('name_hint') or []
    # 商品名カード: 「〜を作りました」の文の中で、商品の呼び方を言い始めた所（無ければ文の頭）
    t_prod = None
    for m in re.finditer(r'作りました|紹介します|完成しました', flat):
        seg_start = max(flat.rfind('。', 0, m.start()), flat.rfind('、', 0, m.start()), 0)
        hs = [flat.find(h, max(0, m.start() - 25), m.start()) for h in hint]
        hs = [h for h in hs if h >= 0]
        i = min(hs) if hs else seg_start + 1
        t_prod = snap(at(i)); break
    # 発売日カード: 「〇月〇日」
    m = re.search(r'\d+月\d+日', flat)
    t_rel = snap(at(m.start())) if m else max(0, L - p['release_dur'])
    # 価格カード: 発売日の前の、最後の「そんな」で始まる締めの文
    t_price = None
    k = flat.rfind('そんな', 0, m.start() if m else len(flat))
    if k >= 0 and at(m.start() if m else len(flat) - 1) - at(k) < 12:
        t_price = snap(at(k))
    # サイズ表: 商品名カードのあと、最初の「XS サイズ」「〜cm」（身長の「164cmの僕」は除く）
    t_size = None
    if t_prod is not None:
        for mm in re.finditer(r'((着丈|北|気|木|丈)は)?(XS|S|M|L) ?サイズ(が|で)?.{0,3}?\d+(\.\d)?cm', flat):
            if at(mm.start()) > t_prod + 0.5:
                t_size = snap(at(mm.start())); break
    # 身長のラベル: 「164cm の僕／人／方」
    heights = []
    for mm in re.finditer(r'(\d{3})cmの(僕|人|方)', flat):
        heights.append(snap(at(mm.start())))
    # 身長別の比較（4 人が 1 秒ずつ）: 「どんな体型／身長の〜も」
    mh = re.search(r'どんな(体型|身長)', flat)
    if mh and not heights:
        t = snap(at(mh.start()))
        heights = [round(t + i * p['height_step'], 3) for i in range(4)]
    # 色のカード: 商品名カードのあと、色の名前（product.colors）を最初に言った所。無ければ「カラーが」
    cols = pr.get('colors') or []
    tc = None
    hits = [flat.find(c) for c in cols if flat.find(c) >= 0]
    hits = [h for h in hits if t_prod is None or at(h) > t_prod]
    if hits:
        tc = snap(at(min(hits)))
    else:
        mc = re.search(r'カラー(が|は)', flat)
        tc = snap(at(mc.start())) if mc else None
    if tc is not None:
        cards.append([tc, p['color_dur'], 'COLOR', 'color'])
    if t_prod is not None:
        end = t_size if t_size and t_size > t_prod else t_prod + p['card_dur']
        cards.append([t_prod, round(min(end, t_prod + 4) - t_prod, 3), 'PRODUCT', 'product']); se.append([t_prod])
    if t_size is not None:
        cards.append([t_size, p['size_dur'], 'SIZETABLE', 'sizetable'])
    for h in heights:
        cards.append([h, 1.8, 'HEIGHT', 'height'])
    if t_price is not None:
        cards.append([t_price, round(t_rel - t_price, 3), 'PRICE', 'price']); se.append([t_price])
    cards.append([t_rel, round(L - t_rel, 3), 'RELEASE', 'release'])
    busy = [(c[0], c[0] + c[1]) for c in cards if c[3] not in ('height', 'color')]  # 身長・色のラベルの間は字幕を出す（8 月の正解）
    # 字幕
    if p.get('chunk') == 'text':
        subs = text_chunks(words, cuts, busy, p)
    else:
        subs = cut_chunks(cuts, tx, busy, p)
    # すき間 0: 次の字幕の頭まで伸ばす（カードの頭まで）
    for i in range(len(subs) - 1):
        nxt = subs[i + 1][0]
        stop = min([nxt] + [a for a, b in busy if a > subs[i][0]])
        if stop - subs[i][0] <= p['max_dur'] + 1:
            subs[i][1] = round(stop - subs[i][0], 3)
    # インサート: カードと同じ時間の画像／身長の発言の着用動画／詳細の発言の写真
    ins = []
    for c in cards:
        if c[3] in ('product', 'sizetable', 'color', 'price', 'release'):
            ins.append([c[0], c[1], 'CARD_' + c[3]])
    for mm in re.finditer(r'(\d{3})cmの(僕|人|方)|どんな(体型|身長)', flat):
        t = snap(at(mm.start()))
        e = flat.find('。', mm.end())
        t1 = at(e) if e >= 0 else t + 3
        ins.append([t, round(min(max(t1 - t, 1.0), p['ins_max']), 3), 'WEAR'])
    for mm in re.finditer(p['detail_re'], flat):
        t = snap(at(mm.start()))
        if any(a - 0.05 <= t < a + d for a, d, _ in ins):
            continue
        st = max(flat.rfind('。', 0, mm.start()), flat.rfind('、', 0, mm.start()))
        t = snap(at(st + 1)) if st >= 0 and at(mm.start()) - at(st + 1) < 2.5 else t
        e = flat.find('。', mm.end())
        t1 = at(e) if e >= 0 else t + 2.5
        ins.append([t, round(min(max(t1 - t, 1.0), p['ins_max']), 3), 'DETAIL'])
    ins.sort()
    return {'subs': subs, 'cards': cards, 'se': se, 'bgm': [p['bgm']], 'inserts': ins}


if __name__ == '__main__':
    inp = json.load(open(sys.argv[1]))
    p = dict(P)
    if len(sys.argv) > 3:
        p.update(json.load(open(sys.argv[3])))
    json.dump(predict(inp, p), open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
