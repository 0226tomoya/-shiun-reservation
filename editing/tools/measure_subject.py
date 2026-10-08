"""メインカメラの各カットで、話している人（わむう）の位置と大きさを測る（構図をカットごとに合わせるため）。

    python3 measure_subject.py EDIT.fcpxml PROXY_DIR MODELS_DIR OUT.json

各 mc-clip の真ん中のコマ（素材そのまま。構図の拡大前）で姿勢推定し、画面に対する比率で
鼻・両肩・両腰・両足首の位置を記録する。
"""
import glob
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

import numpy as np
from PIL import Image
import io

import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision


def T(s):
    return Fraction((s or '0s').rstrip('s'))


def main():
    edit, pdir, models, out = sys.argv[1:5]
    root = ET.parse(edit).getroot()
    res = {e.get('id'): e for e in root.find('resources')}
    proj = [p for p in root.iter('project') if p.get('name') == '本編'][0]
    spine = proj.find('sequence/spine')
    proxies = {}
    for p in glob.glob(os.path.join(pdir, '*.mp4')):
        if os.path.exists(p + '.start'):
            name = os.path.basename(p).rsplit('_', 1)[0]
            s = float(open(p + '.start').read())
            d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                     capture_output=True, text=True).stdout)
            proxies.setdefault(name, []).append((s, s + d, p))
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=os.path.join(models, 'pose_landmarker_full.task')), num_poses=1))
    maps = {}
    rows = []
    for e in spine:
        if e.tag != 'mc-clip':
            continue
        if e.get('ref') not in maps:
            mc = res[e.get('ref')].find('multicam')
            ang = next(a for a in mc.findall('mc-angle') if any(c.tag == 'asset-clip' and res[c.get('ref')].get('hasVideo') == '1' for c in a))
            maps[e.get('ref')] = [(T(c.get('offset')), T(c.get('duration')), T(c.get('start') or res[c.get('ref')].get('start')), c.get('name'))
                                  for c in ang if c.tag == 'asset-clip']
        off, du = T(e.get('offset')), T(e.get('duration'))
        tau = T(e.get('start')) + du / 2
        row = {'offset': float(off), 'dur': float(du), 'src': None}
        for o, d, st, name in maps[e.get('ref')]:
            if o <= tau < o + d:
                ts = float(st + tau - o)
                row['src'], row['src_t'] = name, round(ts, 3)
                pp = next((x for x in proxies.get(name, []) if x[0] <= ts <= x[1]), None)
                if pp:
                    img = subprocess.run(['ffmpeg', '-loglevel', 'error', '-ss', f'{ts - pp[0]:.3f}', '-i', pp[2], '-frames:v', '1',
                                          '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
                    if img:
                        im = np.asarray(Image.open(io.BytesIO(img)).convert('RGB'))
                        r = pose.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=im))
                        if r.pose_landmarks:
                            L = r.pose_landmarks[0]
                            row['lm'] = {k: (round(L[i].x, 4), round(L[i].y, 4), round(L[i].visibility, 2))
                                         for k, i in (('nose', 0), ('le', 7), ('re', 8), ('ls', 11), ('rs', 12), ('lh', 23), ('rh', 24),
                                                      ('lk', 25), ('rk', 26), ('la', 27), ('ra', 28))}
                break
        rows.append(row)
        if len(rows) % 100 == 0:
            print(len(rows), flush=True)
    json.dump(rows, open(out, 'w'))
    print('done', len(rows), sum(1 for r in rows if 'lm' in r))


if __name__ == '__main__':
    main()
