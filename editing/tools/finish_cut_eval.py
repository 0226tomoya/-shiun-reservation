"""長編（ラインナップ）の仕上げのカット（粗編集 → 完成）を、機械的な型で当てられるかを測る。
    python3 finish_cut_eval.py SRC_DIR [SRC_DIR ...]
SRC_DIR/rough_tr.json（粗編集の文字起こし。発言ごと・単語の時刻つき）と diff.json（発言ごとの完成で残った割合 kept）を使う。
型（ショートのカット評価で効いたもの＋仕上げのカットの決まり）:
  retake  : 言い直し（同じ言葉 2 字以上が 5 秒以内に 2 回）→ 前の回
  filler  : つなぎ言葉だけの語（えー・あの・まあ・えっと・なんか・うん）
  direct  : 編集者への指示（カットで・共有します・順番でお願いします）
  douzo   : 差し込みの直前の「どうぞ」
  whole_x : 発言まるごと（指定の正規表現）
点: 削った時間の適合率・再現率・F1（発言ごとに「予想で削った秒」と「実際に削った秒」の小さい方を当たりとする）
"""
import json
import re
import sys

N = lambda t: re.sub(r'[、。,.\s!?！？]', '', t or '')
FILLER = re.compile(r'^(えー+|え+と|えっと|あの+|あのー|まあ|まー|なんか|うん|あー+|ええ)[、。]?$')
DIRECT = re.compile(r'カットで|カットして|共有します|順番でお願い|編集で|ここ切って|撮り直')
DOUZO = re.compile(r'^(こちらです(ね)?。?)?どうぞ。?$')


def predict(tr, rules):
    """発言ごとに削る秒を返す"""
    out = [0.0] * len(tr)
    W = [(i, w) for i, u in enumerate(tr) for w in u.get('words', [])]
    if 'retake' in rules:
        for k in range(len(W)):
            for L in range(6, 0, -1):
                if k + L > len(W): continue
                A = W[k:k + L]; ta = N(''.join(x[1]['word'] for x in A))
                if len(ta) < 2: continue
                hit = None
                for j in range(k + L, min(len(W), k + L + 12)):
                    if j + L > len(W): break
                    B = W[j:j + L]
                    if B[0][1]['start'] - A[0][1]['start'] > 5.0: break
                    if N(''.join(x[1]['word'] for x in B)) == ta:
                        hit = j; break
                if hit is not None:
                    i0 = A[0][0]
                    out[i0] += max(0, W[hit][1]['start'] - A[0][1]['start']) if W[hit][0] == i0 else (tr[i0]['end'] - A[0][1]['start'])
                    break
                elif k + L <= len(W) and any(W[j][1]['start'] - A[0][1]['start'] > 5.0 for j in range(k + L, min(len(W), k + L + 12))):
                    break
    if 'filler' in rules:
        for i, w in W:
            if FILLER.match(w['word'].strip()):
                out[i] += w['end'] - w['start']
    for i, u in enumerate(tr):
        d = u['end'] - u['start']
        if 'direct' in rules and DIRECT.search(u['text']):
            out[i] = d
        if 'douzo' in rules and DOUZO.match(u['text'].strip()):
            out[i] = d
        for x in rules:
            if x.startswith('whole:') and re.search(x[6:], u['text']):
                out[i] = d
        out[i] = min(out[i], d)
    return out


def score(tr, diff, pred):
    gold = [(1 - d['kept']) * (d['t1'] - d['t0']) for d in diff]
    tp = sum(min(a, b) for a, b in zip(pred, gold))
    P = tp / max(sum(pred), 1e-9); R = tp / max(sum(gold), 1e-9)
    return {'F1': round(2 * P * R / max(P + R, 1e-9), 3), '適合率': round(P, 3), '再現率': round(R, 3), '予想で削る秒': round(sum(pred), 1), '実際に削った秒': round(sum(gold), 1)}


if __name__ == '__main__':
    for d in sys.argv[1:]:
        tr = json.load(open(f'{d}/rough_tr.json')); diff = json.load(open(f'{d}/diff.json'))
        assert len(tr) == len(diff)
        print('==', d.rstrip('/').split('/')[-1], '粗編集', round(tr[-1]['end']), '秒')
        for rules in (['retake'], ['filler'], ['direct'], ['douzo'], ['retake', 'filler', 'direct', 'douzo']):
            print(' ', '+'.join(rules), score(tr, diff, predict(tr, rules)))
