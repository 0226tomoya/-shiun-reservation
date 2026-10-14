"""わむうチャンネルのショート（公開済み）を、YouTube の自動字幕（単語の時刻つき json3）と 1 秒ごとのコマ（ストーリーボード）で数える。
動画本体が取れない時（YouTube の 403）の代わり。コマ単位のカットの精度は測れないので、カットの評価は cut_score.py（素材とユーザーのカットがある回）で行う。
    python3 wamu_short_analyze.py WS_DIR OUT.json
WS_DIR/v/<id>.info.json・<id>.ja.json3、WS_DIR/sb/<id>.json・<id>_<n>.jpg
数えるもの（1 本ずつ）:
  話: 長さ・字数・1 秒の字数・語と語の間（0.3 秒超の間の数／分）・最初の発話までの秒・冒頭 3 秒の言葉・最後の言葉
  画: 話す画（一番多い画に似たコマ）とインサートの割合・インサートの回数と長さ・最初のインサートの秒・白黒のコマ・赤い字のコマ・画の切り替わりの回数／分
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image


def words(j3):
    d = json.load(open(j3))
    W = []
    for e in d.get('events', []):
        if 'segs' not in e:
            continue
        t0 = e['tStartMs'] / 1000
        for s in e['segs']:
            txt = s.get('utf8', '')
            if not txt.strip() or txt == '\n':
                continue
            W.append([t0 + s.get('tOffsetMs', 0) / 1000, txt.strip()])
    W.sort()
    return W


def frames(sbdir, vid):
    m = json.load(open(f'{sbdir}/{vid}.json'))
    fr = []
    for i in range(m['n']):
        p = f'{sbdir}/{vid}_{i}.jpg'
        if not os.path.exists(p):
            break
        im = Image.open(p).convert('RGB')
        for r in range(m['rows']):
            for c in range(m['cols']):
                fr.append(np.asarray(im.crop((c * m['w'], r * m['h'], (c + 1) * m['w'], (r + 1) * m['h'])), np.float32))
    n = int(m['dur'] * m['fps']) + 1
    return fr[:n], 1 / m['fps']


def visual(fr, dt):
    if not fr:
        return {}
    h = fr[0].shape[0]
    # 字幕の帯を除いた上半分（顔・背景）で似ているかを見る
    feat = [f[: int(h * 0.42)].reshape(-1, 3)[::7].astype(np.float32) for f in fr]
    hist = [np.histogramdd(x, bins=(6, 6, 6), range=((0, 256),) * 3)[0].ravel() / len(x) for x in feat]
    H = np.array(hist)
    med = np.median(H, axis=0)
    dist = np.abs(H - med).sum(1)
    main = dist < 0.6
    ins_runs, cur = [], 0
    for v in main:
        if not v:
            cur += 1
        elif cur:
            ins_runs.append(cur); cur = 0
    if cur:
        ins_runs.append(cur)
    first_ins = next((i * dt for i, v in enumerate(main) if not v), None)
    sat = [np.mean(np.max(f, 2) - np.min(f, 2)) for f in fr]
    bw = sum(1 for s in sat if s < 6)
    red = 0
    for f in fr:
        band = f[int(h * 0.35): int(h * 0.75)]
        r, g, b = band[..., 0], band[..., 1], band[..., 2]
        if np.mean((r > 150) & (g < 90) & (b < 90)) > 0.003:
            red += 1
    diffs = [np.mean(np.abs(fr[i] - fr[i - 1])) for i in range(1, len(fr))]
    changes = sum(1 for x in diffs if x > 18)
    dur = len(fr) * dt
    return {'話す画の割合': round(float(main.mean()), 2), 'インサート回数': len(ins_runs), 'インサート平均秒': round(float(np.mean(ins_runs)) * dt, 1) if ins_runs else 0,
            '最初のインサート秒': round(first_ins, 1) if first_ins is not None else None, '白黒コマ': bw, '赤字コマ': red,
            '画の大きな切り替わり／分': round(changes / dur * 60, 1)}


def speech(W, dur):
    if not W:
        return {}
    txt = ''.join(w for _, w in W)
    t = [a for a, _ in W]
    gaps = np.diff(t)
    return {'字数': len(txt), '字／秒': round(len(txt) / max(dur, 1), 2), '最初の発話秒': round(t[0], 2),
            '0.6秒超の語間／分': round(float((gaps > 0.6).sum()) / dur * 60, 1), '語間の中央値': round(float(np.median(gaps)), 3) if len(gaps) else None,
            '冒頭3秒': ''.join(w for a, w in W if a < 3.0), '最後': ''.join(w for a, w in W if a > t[-1] - 3)}


def main():
    ws, out = sys.argv[1], sys.argv[2]
    res = []
    for info in sorted(glob.glob(f'{ws}/v/*.info.json')):
        d = json.load(open(info))
        vid = d['id']
        r = {'id': vid, '日付': d.get('upload_date'), '長さ': d.get('duration'), '再生': d.get('view_count'), '題': d.get('title')}
        j3 = f'{ws}/v/{vid}.ja.json3'
        if os.path.exists(j3):
            r.update(speech(words(j3), d.get('duration') or 1))
        if os.path.exists(f'{ws}/sb/{vid}.json'):
            fr, dt = frames(f'{ws}/sb', vid)
            r.update(visual(fr, dt))
        res.append(r)
    json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
    print(len(res), '本')


if __name__ == '__main__':
    main()
