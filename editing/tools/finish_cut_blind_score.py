"""答えを見ていない判断（blind の answer.json: cut / pin）を、完成で実際に削った発言（diff.json の kept）と比べる。
    python3 finish_cut_blind_score.py DIFF.json ANSWER.json
- cut: 削った時間の適合率・再現率・F1（発言ごとに min(予想で削る秒, 実際に削った秒)）
- pin: ピンの発言のうち実際に削られた割合（当たり）、実際に削った時間のうちピンか cut に入っていた割合（拾えた割合）
"""
import json
import sys

diff = json.load(open(sys.argv[1]))
ans = json.load(open(sys.argv[2]))
dur = [d['t1'] - d['t0'] for d in diff]
gold = [(1 - d['kept']) * x for d, x in zip(diff, dur)]
cut, pin = set(ans.get('cut', [])), set(ans.get('pin', []))
pred = [dur[i] if i in cut else 0 for i in range(len(diff))]
tp = sum(min(a, b) for a, b in zip(pred, gold))
P = tp / max(sum(pred), 1e-9); R = tp / max(sum(gold), 1e-9)
pin_sec = sum(dur[i] for i in pin if i < len(dur)); pin_hit = sum(gold[i] for i in pin if i < len(dur))
cover = sum(gold[i] for i in cut | pin if i < len(dur)) / max(sum(gold), 1e-9)
print(json.dumps({'cut_F1': round(2 * P * R / max(P + R, 1e-9), 3), 'cut_適合率': round(P, 3), 'cut_再現率': round(R, 3),
                  'cut_秒': round(sum(pred), 1), '実際に削った秒': round(sum(gold), 1),
                  'pin_本': len(pin), 'pin_当たり': round(pin_hit / max(pin_sec, 1e-9), 3), 'cut+pin で拾えた割合': round(cover, 3)}, ensure_ascii=False))
