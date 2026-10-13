"""shiun の販促ショートの編集表（EDL）を、過去のショートの決まり（editing/knowledge/shiun_ショートの決まり.md）で採点する。100 点満点。
python3 short_score.py edl.json [台本.md]
画で見ないと分からない所（画角・インサートが話している部位か・色）は、確認用の動画を見た人が edl の "visual_check" に書く:
 "visual_check": {"framing": 0〜5, "inserts_match": 0〜5, "notes": "…"}
"""
import sys, json, re, statistics, unicodedata

edl = json.load(open(sys.argv[1]))
script = open(sys.argv[2]).read() if len(sys.argv) > 2 else ''
segs, subs, cards = edl['segments'], edl.get('subs', []), edl.get('cards', [])
total = sum(s['out'] - s['in'] for s in segs)
pts, notes = {}, []


def part(name, got, full, why=''):
    pts[name] = (round(max(0, min(full, got)), 1), full)
    if got < full and why:
        notes.append(f'{name}: {why}')


# 1. 構成（20）: 長さ・つかみ・並び
n_items = max(1, len([c for c in cards if c['kind'] == 'product']))
lo, hi = (69, 112) if n_items == 1 else (88, 124)
s_len = 8 if lo <= total <= hi else max(0, 8 - abs(total - (lo if total < lo else hi)) / 5)
hook = [c for c in cards if c['kind'] == 'hook'] or [s for s in subs if s['at'] < 0.5]
s_hook = 6 if hook and min(h['at'] for h in hook) <= 0.3 else 0
order_kinds = [c['kind'] for c in sorted(cards, key=lambda c: c['at'])]
want = ['product', 'price', 'release']
idx = [order_kinds.index(k) for k in want if k in order_kinds]
s_order = 6 if len(idx) == 3 and idx == sorted(idx) else 2 * len(idx)
part('構成', s_len + s_hook + s_order, 20, f'長さ {total:.1f}s（{lo}〜{hi}）・つかみ {"あり" if s_hook else "なし"}・並び {order_kinds}')

# 2. カット（15）: 1 カットの長さ（0.65 秒前後）・短すぎる切れ端・つなぎの空き
durs = [s['out'] - s['in'] for s in segs]
med = statistics.median(durs) if durs else 0
s_med = 8 if 0.45 <= med <= 1.2 else max(0, 8 - abs(med - 0.8) * 8)
tiny = sum(1 for d in durs if d < 0.25)
s_tiny = max(0, 4 - tiny)
rev = sum(1 for a, b in zip(segs, segs[1:]) if a['clip'] == b['clip'] and abs(b['in'] - a['out']) < 0.02)  # 切っていない継ぎ目
s_join = 3 if rev <= len(segs) * 0.1 else 1
part('カット', s_med + s_tiny + s_join, 15, f'中央 {med:.2f}s・0.25 秒未満 {tiny}・切らずにつないだ所 {rev}')

# 3. 字幕（20）: 発話の時間を覆うか・文字数・表示時間・すき間・打ち残し
cover = sum(s['dur'] for s in subs) / total if total else 0
s_cov = 8 * min(1, cover / 0.85)
long = [s['text'] for s in subs if max(len(l) for l in s['text'].split('\n')) > 18]
s_len2 = max(0, 4 - len(long))
bad_dur = [s for s in subs if not (0.5 <= s['dur'] <= 4.0)]
s_dur = max(0, 3 - len(bad_dur) * 0.5)
gaps = [b['at'] - (a['at'] + a['dur']) for a, b in zip(subs, subs[1:])]
over = sum(1 for g in gaps if g < -0.02)
s_gap = 2 if over == 0 else 0
romaji = [s['text'] for s in subs if re.search(r'(?<![A-Za-z])[a-z]{1,2}(?![A-Za-z])', s['text']) and re.search(r'[ぁ-んァ-ン一-龥]', s['text'])]
s_rom = 3 if not romaji else 0
part('字幕', s_cov + s_len2 + s_dur + s_gap + s_rom, 20, f'覆い {cover:.0%}・18 字超 {len(long)}・表示時間外れ {len(bad_dur)}・重なり {over}・打ち残し {romaji[:2]}')

# 4. 商品の出し方（15）: カードの有無・台本との照合
kinds = {c['kind'] for c in cards}
s_cards = sum(3 for k in ('product', 'price', 'release') if k in kinds) + (2 if 'height' in kinds else 0)
mism = []
if script:
    norm = lambda t: unicodedata.normalize('NFKC', t).replace(' ', '')
    sn = norm(script)
    for c in cards:
        if c['kind'] in ('product', 'price'):
            for ln in c['lines']:
                m = re.findall(r'¥\s?[\d,]+|[A-Z][A-Z/\- ]{4,}[A-Z]', ln)
                for x in m:
                    if norm(x) not in sn:
                        mism.append(x)
s_check = 4 if not mism else 0
part('商品', s_cards + s_check, 15, f'カード {sorted(kinds)}・台本と合わない {mism[:3]}')

# 5. 音（10）: BGM・効果音
s_bgm = 5 if edl.get('bgm') else 0
se = edl.get('se', [])
prod_at = [c['at'] for c in cards if c['kind'] in ('product', 'price')]
s_se = 5 if se and all(any(abs(x['at'] - p) < 0.3 for x in se) for p in prod_at) else (2 if se else 0)
part('音', s_bgm + s_se, 10, f'BGM {"あり" if s_bgm else "なし"}・効果音 {len(se)}（商品名・価格の頭に合わせる）')

# 6. 画（10）: インサートの量・見た人の採点
ins = edl.get('inserts', [])
ins_t = sum(i['out'] - i['in'] for i in ins)
s_ins = 4 if 0.08 <= ins_t / total <= 0.5 else (2 if ins else 0)
vc = edl.get('visual_check', {})
s_vis = min(3, vc.get('framing', 0) * 0.6) + min(3, vc.get('inserts_match', 0) * 0.6)
part('画', s_ins + s_vis, 10, f'インサート {ins_t:.1f}s（{ins_t / total:.0%}）・目視 {vc or "まだ"}')

# 7. 書き出し（10）: 仮置き・空の字幕・時刻の整合
ph = [s['text'] for s in subs + [{'text': ' '.join(c['lines'])} for c in cards] if re.search(r'追加予定|仮|後ほど|TODO', s['text'])]
empty = [s for s in subs if not s['text'].strip()]
out_of = [x for x in subs + cards if x['at'] + x['dur'] > total + 0.05]
s_out = 10 - 4 * bool(ph) - 3 * bool(empty) - 3 * bool(out_of)
part('書き出し', s_out, 10, f'仮置き {ph[:2]}・空の字幕 {len(empty)}・はみ出し {len(out_of)}')

score = round(sum(v[0] for v in pts.values()), 1)
print(json.dumps({'score': score, 'parts': pts, 'notes': notes, 'length': round(total, 2)}, ensure_ascii=False, indent=1))
