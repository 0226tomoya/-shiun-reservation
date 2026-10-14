"""ジェットカット（short_jetcut.py）の後に、ユーザー（編集者）の詰め方の型を当てる。テロップ・インサートを載せる前提の切り方。
    python3 short_cut_rules.py JET.json ASR_DIR OUT.json

ASR_DIR: マイクごとの文字起こし（<マイク名>.json、faster-whisper の単語の時刻つき）
型（2026-10-14、ユーザーが直したショート 4 本と比べて決めた。評価は cut_score.py。4 本の平均 64.7 → 75.2 点）:
  1. 尾の助詞を切る: 中身を飛ばす直前のカット（次のカットまで元の時刻で 0.3 秒より離れる）が助詞（は・が・を・に・と・も・で・の・て…）で
     終わるなら、その助詞の手前で切る（「前のソールは、」→「前のソール」）
  2. 言い直しは後を残す: 同じ言葉（2 字以上）が 5 秒以内に 2 回 → 前の回の頭から後の回の頭の手前までを抜く
  3. 文の途中の伸びた助詞を抜く: 助詞の頭から次の語の頭まで 0.35 秒以上（「も、ー」「を…」）→ その助詞を抜いて句と句を直につなぐ
  4. cut_pins.py の候補のうち、ユーザーもほぼ削っていた種類（冒頭の一般論・言い直し・言い重ね・例の 3 つ目・カードで見せる言い方）は自動で削る。
     当たりの低い種類（相づち・言いさし）は削らずにピン（FCP の To Do マーカー）で残す
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PART = re.compile(r'^(は|が|を|に|と|も|で|の|て|って|から|けど|ので|し|とか|や|へ|より)[、,]?$')
N = lambda t: re.sub(r'[、。,.\s!?！？]', '', t or '')
PM = 0.02          # 語の頭の 0.02 秒手前で切る
JUMP = 0.3         # 次のカットまでこれより離れていたら「中身を飛ばした」とみなす
RETAKE_WIN = 5.0   # 言い直しを探す範囲（秒）
MID_PART = 0.35    # 文の途中の助詞を抜く長さ（助詞の頭から次の語の頭まで）
KEEP_MIN = 0.15    # これより短い切れ端は残さない
AUTO = ('一般論', '言い直し', '言い重ね', '例の 3 つ目', 'カード')

_W = {}


def words(asr_dir, mic):
    if mic not in _W:
        f = os.path.join(asr_dir, mic[:-4] + '.json')
        _W[mic] = [w for sg in json.load(open(f)) for w in sg['words']] if os.path.exists(f) else []
    return _W[mic]


def seg_words(edl, s, asr_dir):
    c = edl['clips'][s['clip']]
    a, b = s['in'] + c['offset'], s['out'] + c['offset']
    return [w for w in words(asr_dir, c['mic']) if (min(w['end'], b) - max(w['start'], a)) > 0.5 * (w['end'] - w['start'])]


def cut_out(segs, clip, a, b):
    out = []
    for s in segs:
        if s['clip'] != clip or s['out'] <= a or s['in'] >= b:
            out.append(s)
            continue
        if a - s['in'] >= KEEP_MIN:
            out.append({**s, 'out': round(a, 4)})
        if s['out'] - b >= KEEP_MIN:
            out.append({**s, 'in': round(b, 4)})
    return out


def tail_particles(edl, asr_dir):
    segs, out, n = edl['segments'], [], 0
    for i, s in enumerate(segs):
        c = edl['clips'][s['clip']]
        if not c.get('mic'):
            out.append(s)
            continue
        W = seg_words(edl, s, asr_dir)
        nx = segs[i + 1] if i + 1 < len(segs) else None
        cont = nx is not None and nx['clip'] == s['clip'] and 0 <= nx['in'] - s['out'] <= JUMP
        if W and len(W) >= 2 and not cont and PART.match(W[-1]['word'].strip()):
            t = W[-1]['start'] - c['offset'] - PM
            if t - s['in'] >= 0.25 and t < s['out']:
                s = {**s, 'out': round(t, 4)}
                n += 1
        out.append(s)
    return {**edl, 'segments': out}, n


def retakes(edl, asr_dir):
    allw = []
    for s in edl['segments']:
        c = edl['clips'][s['clip']]
        if c.get('mic'):
            allw += [(c['mic'], c['offset'], s['clip'], w) for w in seg_words(edl, s, asr_dir)]
    cuts = []
    for i in range(len(allw)):
        done = False
        for L in range(6, 0, -1):
            if i + L > len(allw):
                continue
            A = allw[i:i + L]
            ta = N(''.join(x[3]['word'] for x in A))
            if len(ta) < 2:
                continue
            for j in range(i + L, min(len(allw), i + L + 12)):
                if j + L > len(allw):
                    break
                B = allw[j:j + L]
                if B[0][3]['start'] - A[0][3]['start'] > RETAKE_WIN or B[0][0] != A[0][0]:
                    done = True  # 一番長い語の並びで範囲を超えたら、短い並びでは探さない（短い一致は「言い直し」でないことが多い。4 本で点が下がった）
                    break
                if N(''.join(x[3]['word'] for x in B)) == ta:
                    cuts.append((A[0][2], A[0][3]['start'] - A[0][1] - PM, B[0][3]['start'] - B[0][1] - PM))
                    done = True
                    break
            if done:
                break
    segs = edl['segments']
    for clip, a, b in cuts:
        segs = cut_out(segs, clip, a, b)
    return {**edl, 'segments': segs}, len(cuts)


def mid_particles(edl, asr_dir):
    cuts = []
    for s in edl['segments']:
        c = edl['clips'][s['clip']]
        if not c.get('mic'):
            continue
        off = c['offset']
        a, b = s['in'] + off, s['out'] + off
        W = [w for w in words(asr_dir, c['mic']) if w['start'] >= a - 0.05 and w['end'] <= b + 0.3]
        for i in range(1, len(W) - 1):
            w, nx = W[i], W[i + 1]
            if PART.match(w['word'].strip()) and nx['start'] - w['start'] >= MID_PART and nx['start'] < b:
                cuts.append((s['clip'], w['start'] - off - PM, nx['start'] - off - PM))
    segs = edl['segments']
    for clip, a, b in cuts:
        segs = cut_out(segs, clip, a, b)
    return {**edl, 'segments': segs}, len(cuts)


def pins_and_auto(edl, asr_dir, tmp, auto_cut=True):
    json.dump(edl, open(tmp, 'w'), ensure_ascii=False)
    subprocess.run([sys.executable, os.path.join(HERE, 'cut_pins.py'), tmp, asr_dir, tmp], check=True, capture_output=True)
    e = json.load(open(tmp))
    pins = e.get('pins', [])
    auto = [p for p in pins if any(k in p['note'] for k in AUTO)] if auto_cut else []
    keep, tl, removed = [], 0.0, []
    for s in e['segments']:
        d = s['out'] - s['in']
        hit = [p for p in auto if tl <= p['at'] < tl + d]
        if hit:
            removed += [p['note'] for p in hit]
        else:
            keep.append(s)
        tl += d
    e['segments'] = keep
    # 残すピン（人の判断）だけを、削った後のタイムラインで打ち直す
    json.dump({**e, 'pins': []}, open(tmp, 'w'), ensure_ascii=False)
    subprocess.run([sys.executable, os.path.join(HERE, 'cut_pins.py'), tmp, asr_dir, tmp], check=True, capture_output=True)
    e2 = json.load(open(tmp))
    e2['pins'] = [p for p in e2.get('pins', []) if not any(k in p['note'] for k in AUTO)]
    os.remove(tmp)
    return e2, removed


def main():
    src, asr_dir, dst = sys.argv[1:4]
    edl = json.load(open(src))
    L0 = sum(s['out'] - s['in'] for s in edl['segments'])
    edl, n1 = tail_particles(edl, asr_dir)
    edl, n2 = retakes(edl, asr_dir)
    edl, removed = pins_and_auto(edl, asr_dir, dst + '.tmp')
    edl, n3 = mid_particles(edl, asr_dir)
    if n3:  # 途中の助詞を抜いてタイムラインが縮んだので、ピンを打ち直す
        edl, _ = pins_and_auto({**edl, 'pins': []}, asr_dir, dst + '.tmp', auto_cut=False)
    json.dump(edl, open(dst, 'w'), ensure_ascii=False, indent=1)
    L1 = sum(s['out'] - s['in'] for s in edl['segments'])
    print(f'尾の助詞 {n1}・言い直し {n2}・途中の助詞 {n3}・自動で削った候補 {len(removed)}・ピン {len(edl.get("pins", []))}・長さ {L0:.1f} → {L1:.1f} 秒')
    for r in removed:
        print('  削った:', r)


if __name__ == '__main__':
    main()
