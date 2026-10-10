"""本編の編集点を、ピンマイク音声で 1 つずつ調べる（発言の途中で切っていないか・無駄な無音がないか）。

    python3 audit_cuts.py EDIT.fcpxml PINMIC.wav [OUT.json]

- スパインのマルチカム（mc-clip）の start は、ピンマイク音声の時刻と同じ（同期済み）。
- 声の有無は 10ms ごとの音量（ノイズの床から +14dB 以上を声とみなす）。
- 調べること（編集点ごと）:
  cut_in_word  前のカットの終わり / 次のカットの頭が声の途中（素材ではその先も声が続いている）
  silence      前のカットの終わりの無音 ＋ 次のカットの頭の無音（この合計が長いと「間延び」）
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

import numpy as np

SR = 16000
HOP = 0.01


def T(s):
    s = (s or '0s').rstrip('s')
    if '/' in s:
        a, b = s.split('/')
        return Fraction(int(a), int(b))
    return Fraction(s)


def main():
    edit, wav = sys.argv[1:3]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', wav, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                         capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = len(a) // int(SR * HOP)
    rms = np.sqrt((a[:n * int(SR * HOP)].reshape(n, -1) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    floor = np.percentile(db, 10)
    voiced = db > floor + 14

    def v(t):  # 素材の時刻 t（秒）の声の有無
        i = int(t / HOP)
        return bool(voiced[i]) if 0 <= i < n else False

    def sil_back(t, lim=3.0):  # t から前に何秒無音が続くか
        k = 0
        while k * HOP < lim and not v(t - HOP * (k + 1)):
            k += 1
        return k * HOP

    def sil_fwd(t, lim=3.0):
        k = 0
        while k * HOP < lim and not v(t + HOP * k):
            k += 1
        return k * HOP

    r = ET.parse(edit).getroot()
    p = [p for p in r.iter('project') if p.get('name') == '本編'][0]
    sp = [e for e in p.find('sequence/spine')]
    rows = []
    for x, y in zip(sp, sp[1:]):
        if x.tag != 'mc-clip' or y.tag != 'mc-clip':
            continue
        xe = float(T(x.get('start')) + T(x.get('duration')))   # 前のカットの終わり（素材の時刻）
        ys = float(T(y.get('start')))                          # 次のカットの頭
        t_tl = float(T(y.get('offset')))
        contiguous = abs(xe - ys) < 0.02
        # 声の途中で切っている: 終わりの直前 30ms が声 かつ 素材ではその直後も声
        tail_cut = all(v(xe - HOP * k) for k in (1, 2, 3)) and v(xe + HOP)
        head_cut = all(v(ys + HOP * k) for k in (0, 1, 2)) and v(ys - HOP * 2)
        s_tail, s_head = sil_back(xe), sil_fwd(ys)
        rows.append({'t': round(t_tl, 3), 'src_out': round(xe, 3), 'src_in': round(ys, 3), 'contiguous': contiguous,
                     'tail_cut': tail_cut and not contiguous, 'head_cut': head_cut and not contiguous,
                     'silence': round(s_tail + s_head, 2) if not contiguous else None,
                     's_tail': round(s_tail, 2), 's_head': round(s_head, 2)})
    cuts = [x for x in rows if not x['contiguous']]
    bad_word = [x for x in cuts if x['tail_cut'] or x['head_cut']]
    sil = sorted(x['silence'] for x in cuts)
    print(f'編集点 {len(rows)}（素材がつながっていない本当の編集点 {len(cuts)}）')
    print(f'発言の途中で切っている疑い: {len(bad_word)}')
    if sil:
        print('編集点の無音（前の終わり＋次の頭）: 中央値 %.2f 秒 / 90%% %.2f 秒 / 最大 %.2f 秒' % (
            sil[len(sil) // 2], sil[int(len(sil) * .9)], sil[-1]))
        print('0.5 秒以上:', sum(1 for s in sil if s >= .5), ' 1 秒以上:', sum(1 for s in sil if s >= 1))
    if out:
        json.dump(rows, open(out, 'w'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
