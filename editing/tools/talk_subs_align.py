"""対談のフルテロップ（文だけ）を、文字起こしの単語の時刻に突き合わせて、出す時刻を決める。あわせて
「起こしに無い言葉を足していないか」「話したのにテロップに無い所（拾い漏れ）」を出す。

    python3 talk_subs_align.py ASR.json TELOPS.json OUT_SUBS.json [--report REPORT.md] [--gap 2.0]

ASR.json   : faster-whisper の出力（[{start, end, text, words: [{start, end, word}]}]）。時刻はタイムラインの秒
TELOPS.json: [{"text": "テロップ"}, ...]（話した順）。（ ）の中は補った言葉として突き合わせから外す
OUT_SUBS   : [{"start", "end", "text", "match", "asr"}]
  match = テロップの文字（（ ）の外）のうち、起こしの該当範囲と一致した割合。低いもの（0.6 未満）は言っていない言葉の疑い
時刻: 頭 = テロップの最初の一致した文字の単語の頭。終わり = 次のテロップの頭（相づちの間は出したまま）。
      ただし最後の一致した文字の単語の終わりから --gap 秒を超えて無言なら、そこで切る
"""
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher

FILLERS = ('えーと', 'えっと', 'えー', 'あー', 'あの', 'あのー', 'まあ', 'まぁ', 'なんか', 'うん', 'はい', 'そうそう', 'そうですね', 'そうね', 'そう',
           'ね', 'ええ', 'へー', 'おー', 'なるほど', 'こう', 'その', 'ちょっと', 'いや')
PUNCT = re.compile(r'[\s、。，．,.!！?？「」『』…・〜~ー\-—:：;；"\'“”]')


def norm(s):
    return PUNCT.sub('', unicodedata.normalize('NFKC', s))


def char_stream(asr):
    """起こしを 1 文字ずつに（文字の時刻つき）"""
    cs, ts = [], []
    for seg in asr:
        for w in seg.get('words') or []:
            t = norm(w['word'])
            if not t:
                continue
            n = len(t)
            for i, ch in enumerate(t):
                cs.append(ch)
                ts.append((w['start'] + (w['end'] - w['start']) * i / n, w['start'] + (w['end'] - w['start']) * (i + 1) / n))
    return ''.join(cs), ts


def main():
    asr = json.load(open(sys.argv[1]))
    tel = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    rep = sys.argv[sys.argv.index('--report') + 1] if '--report' in sys.argv else None
    gap = float(sys.argv[sys.argv.index('--gap') + 1]) if '--gap' in sys.argv else 2.0
    C, TS = char_stream(asr)
    used = [False] * len(C)
    p = 0
    res = []
    for k, t in enumerate(tel):
        body = norm(re.sub(r'[（(][^）)]*[）)]', '', t['text']))
        if not body:
            continue
        # 前のテロップの終わりから先の窓で、一番よく合う所
        lo = max(0, p - 5)
        hi = min(len(C), p + len(body) * 4 + 60)
        win = C[lo:hi]
        sm = SequenceMatcher(None, body, win, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size >= 2 or (b.size == 1 and len(body) <= 3)]
        got = sum(b.size for b in blocks)
        if not blocks:
            res.append({'text': t['text'], 'start': None, 'end': None, 'match': 0.0, 'asr': ''})
            continue
        a = lo + blocks[0].b
        b = lo + blocks[-1].b + blocks[-1].size
        # 窓の先の方に飛んだ小さい一致（同じ言葉の繰り返し）で範囲が伸びすぎないように
        if b - a > len(body) * 3 + 20 and len(blocks) > 1:
            blocks = blocks[:-1]
            b = lo + blocks[-1].b + blocks[-1].size
            got = sum(x.size for x in blocks)
        for i in range(a, b):
            used[i] = True
        res.append({'text': t['text'], 'start': TS[a][0], 'last': TS[b - 1][1], 'match': round(got / len(body), 2), 'asr': C[a:b], 'i0': a, 'i1': b})
        p = b
    # 時刻: 次の頭まで。ただし無言が gap 秒を超えたら切る
    ok = [r for r in res if r.get('start') is not None]
    for i, r in enumerate(ok):
        nxt = ok[i + 1]['start'] if i + 1 < len(ok) else r['last'] + gap
        r['end'] = min(nxt, r['last'] + gap) if nxt - r['last'] > gap else nxt
        if r['end'] - r['start'] < 0.5:
            r['end'] = r['start'] + 0.5
    json.dump([{k: r[k] for k in ('start', 'end', 'text', 'match', 'asr')} for r in ok], open(out, 'w'), ensure_ascii=False, indent=1)
    # 拾い漏れ: テロップに使われなかった起こしの文字のかたまり（つなぎ言葉・相づちだけのものは外す）
    miss = []
    i = 0
    while i < len(C):
        if used[i]:
            i += 1
            continue
        j = i
        while j < len(C) and not used[j]:
            j += 1
        s = C[i:j]
        core = s
        for f in sorted(FILLERS, key=len, reverse=True):
            core = core.replace(f, '')
        if len(core) >= 6:
            miss.append((TS[i][0], TS[j - 1][1], s))
        i = j
    low = [r for r in ok if r['match'] < 0.6]
    print(f'テロップ {len(tel)}・時刻が付いた {len(ok)}・一致が低い（足した言葉の疑い） {len(low)}・拾い漏れの疑い {len(miss)}')
    if rep:
        with open(rep, 'w') as f:
            f.write('# 突き合わせの結果\n\n## 一致が低いテロップ（起こしに無い言葉を足した疑い）\n\n')
            for r in low:
                f.write(f"- {r['start']:.2f} 「{r['text']}」 一致 {r['match']} ／ 起こし「{r['asr']}」\n")
            f.write('\n## テロップに使われていない発言（6 字以上）\n\n')
            for a, b, s in miss:
                f.write(f'- {a:.2f}〜{b:.2f} {s}\n')


if __name__ == '__main__':
    main()
