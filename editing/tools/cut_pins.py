"""切るかどうか人の判断が要る所を見つけ、編集表（EDL）に「ピン」として足す。切らずに残し、short_build.py が FCP の To Do マーカーを打つ。
python3 cut_pins.py edl.json asr_dir out.json

見つけるもの（10/13、ユーザーが直したショート 4 本で、ユーザーが中身を削った所の傾向から）:
- 相づちを求める言い回し      「〜ですよね」「〜ますよね」「〜でしょ」
- 言い重ね                    「AもBも」「〜も、〜も」が続く所、同じ語の言い直し
- 例の 3 つ目以降              身長などの数字の例が 3 つ以上並ぶ所（158・164・168）
- つかみの一般論              冒頭 10 秒の「所詮」「そもそも」「一般的に」「みんな」
- カードで見せる所の言い方     「以下の日程」「下記の日程」「価格は」（カードと字幕が重なる）
- 言いさし                    2 字以下で終わる切れ端の発言
ピンは {at: タイムラインの秒, note: 理由, kind}。同じ所に 2 つは打たない（1 秒以内はまとめる）。
"""
import json
import os
import re
import sys

RULES = [
    ('相づち', re.compile(r'(です|ます|でしょう?)よね[。、]?$|でしょ[。、]?$'), '相づちを求める言い回し（切る候補）'),
    ('一般論', re.compile(r'所詮|そもそも|一般的に|みんな|世の中'), 'つかみの一般論（切る候補・冒頭だけ）'),
    ('カード', re.compile(r'以下の日程|下記の日程|下記の通り|以下の通り'), 'カードで見せる所の言い方（切る候補）'),
]
NUM = re.compile(r'(\d{3})\s*(cm|センチ)')


def words(asr_dir, mic):
    f = os.path.join(asr_dir, mic[:-4] + '.json')
    return [w for sg in json.load(open(f)) for w in sg['words']] if os.path.exists(f) else []


def main():
    edl = json.load(open(sys.argv[1]))
    asr_dir = sys.argv[2]
    cache = {}
    pins = []
    tl = 0.0
    nums = []  # (タイムライン, 数字)
    prev_tail = ''
    for s in edl['segments']:
        c = edl['clips'][s['clip']]
        d = s['out'] - s['in']
        if c.get('mic'):
            W = cache.setdefault(c['mic'], words(asr_dir, c['mic']))
            off = c['offset']
            ws = [w for w in W if w['end'] > s['in'] + off + 0.02 and w['start'] < s['out'] + off - 0.02]
            text = ''.join(w['word'] for w in ws).strip()
            for kind, rx, note in RULES:
                if kind == '一般論' and tl > 10:
                    continue
                if rx.search(text):
                    pins.append({'at': tl + 0.05, 'note': f'{note}「{text[:20]}」', 'kind': kind})
            if 0 < len(re.sub(r'[、。\s]', '', text)) <= 2 and not text.endswith('。'):
                pins.append({'at': tl + 0.05, 'note': f'言いさし（切る候補）「{text}」', 'kind': '言いさし'})
            # 言い重ね: 「〜も」で終わる区間が続く／同じ語を前の区間の終わりでも言っている
            t2 = re.sub(r'[、。\s]', '', text)
            if t2.endswith('も') and prev_tail.endswith('も'):
                pins.append({'at': tl + 0.05, 'note': f'言い重ね（切る候補）「{text[:20]}」', 'kind': '言い重ね'})
            elif len(t2) >= 3 and prev_tail and t2[:3] in prev_tail[-8:]:
                pins.append({'at': tl + 0.05, 'note': f'同じ言葉の言い直し（切る候補）「{text[:20]}」', 'kind': '言い直し'})
            prev_tail = t2 or prev_tail
            for m in NUM.finditer(text):
                nums.append((tl, m.group(1)))
        tl += d
    # 例の 3 つ目以降（10 秒以内に違う数字が 3 つ以上）
    for i in range(2, len(nums)):
        if nums[i][0] - nums[i - 2][0] <= 10 and len({n for _, n in nums[i - 2:i + 1]}) == 3:
            pins.append({'at': nums[i][0] + 0.05, 'note': f'例の 3 つ目（切る候補）「{nums[i][1]}cm」', 'kind': '例の3つ目'})
    pins.sort(key=lambda p: p['at'])
    merged = []
    for p in pins:
        if merged and p['at'] - merged[-1]['at'] < 1.0:
            merged[-1]['note'] += '／' + p['note']
            continue
        merged.append(p)
    edl['pins'] = merged
    json.dump(edl, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
    from collections import Counter
    print(f'ピン {len(merged)} 本', dict(Counter(p['kind'] for p in pins)))


if __name__ == '__main__':
    main()
