"""インサート素材の動きを調べ、NG 区間（喋り・ガム・ポケット探し・服や髪を直す）と使える区間を出す。

    python3 analyze_motion.py CLIP_DIR MODELS_DIR

CLIP_DIR には fetch で作ったコマ: h/（8fps・1920 幅、人が映る素材）か f/（4fps・480 幅）。結果は CLIP_DIR/motion.json。
判定（RULES.md の 6）:
  - 口: 顔の jawOpen が 1 秒の中で揺れ続ける（標準偏差が大きい）→ 喋り・ガム
  - 髪: 手首が肩より上で、頭（鼻）の近く
  - ポケット: 手首が腰の高さで腰に近く、しかも動いている
  - 服: 手首が胴体の前で大きく動いている（要確認）
  - カメラ: 画面全体が大きく動く（ズーム・パン・揺れ）
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision


def load(models):
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=os.path.join(models, 'face_landmarker.task')),
        output_face_blendshapes=True, num_faces=1, min_face_detection_confidence=0.4))
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=os.path.join(models, 'pose_landmarker_full.task')), num_poses=1))
    return face, pose


def merge(flags, fps, pad=0.5, min_len=0.25):
    """フレームごとの真偽を、前後 pad 秒を足した区間 [(秒, 秒)] にまとめる。"""
    out = []
    for k, f in enumerate(flags):
        if not f:
            continue
        a, b = max(0, k / fps - pad), (k + 1) / fps + pad
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(round(a, 2), round(b, 2)) for a, b in out if b - a >= min_len]


def main():
    d, models = sys.argv[1:3]
    sub = 'h' if os.path.isdir(os.path.join(d, 'h')) and os.listdir(os.path.join(d, 'h')) else 'f'
    fps = 8.0 if sub == 'h' else 4.0
    frames = sorted(glob.glob(os.path.join(d, sub, '*.jpg')))
    face, pose = load(models)
    rows, prev = [], None
    for p in frames:
        im = np.asarray(Image.open(p).convert('RGB'))
        mi = mp.Image(image_format=mp.ImageFormat.SRGB, data=im)
        r = {'jaw': None, 'face': False, 'pose': None}
        fr = face.detect(mi)
        if fr.face_blendshapes:
            bs = {c.category_name: c.score for c in fr.face_blendshapes[0]}
            r['jaw'] = bs.get('jawOpen', 0.0)
            r['mouth'] = bs.get('mouthClose', 0.0)
            r['face'] = True
        pr = pose.detect(mi)
        if pr.pose_landmarks:
            L = pr.pose_landmarks[0]
            pt = lambda i: (L[i].x, L[i].y, L[i].visibility)  # noqa: E731
            r['pose'] = {'nose': pt(0), 'ls': pt(11), 'rs': pt(12), 'lw': pt(15), 'rw': pt(16), 'lh': pt(23), 'rh': pt(24)}
        g = np.asarray(Image.open(p).convert('L').resize((96, 54)), dtype=np.float32)
        r['motion'] = float(np.mean(np.abs(g - prev))) if prev is not None else 0.0
        prev = g
        rows.append(r)

    n = len(rows)
    jaw = np.array([r['jaw'] if r['jaw'] is not None else np.nan for r in rows])
    w = int(fps)  # 1 秒
    talk = np.zeros(n, bool)
    for k in range(n):
        seg = jaw[max(0, k - w // 2):k + w // 2 + 1]
        seg = seg[~np.isnan(seg)]
        if len(seg) >= max(3, w // 2) and (np.std(seg) > 0.06 or (np.max(seg) - np.min(seg)) > 0.18):
            talk[k] = True

    hair = np.zeros(n, bool)
    pocket = np.zeros(n, bool)
    clothes = np.zeros(n, bool)
    wpos = [None] * n
    for k, r in enumerate(rows):
        q = r['pose']
        if not q:
            continue
        sh_y = (q['ls'][1] + q['rs'][1]) / 2
        hip_y = (q['lh'][1] + q['rh'][1]) / 2
        torso = max(1e-3, hip_y - sh_y)
        sw = max(1e-3, abs(q['ls'][0] - q['rs'][0]))
        wpos[k] = [(q[w_][0], q[w_][1]) if q[w_][2] > 0.5 else None for w_ in ('lw', 'rw')]
        for w_, h_ in (('lw', 'lh'), ('rw', 'rh')):
            x, y, v = q[w_]
            if v < 0.5:
                continue
            nx, ny = q['nose'][0], q['nose'][1]
            if y < sh_y and np.hypot(x - nx, y - ny) < 1.2 * sw:
                hair[k] = True
            if abs(y - q[h_][1]) < 0.25 * torso and abs(x - q[h_][0]) < 0.6 * sw:
                pocket[k] = True  # 動きと合わせて後で判定
            if sh_y + 0.1 * torso < y < hip_y - 0.1 * torso and min(abs(x - q['ls'][0]), abs(x - q['rs'][0])) < 1.2 * sw:
                clothes[k] = True
    # 手首の速さ（胴体の長さあたり / 秒）
    speed = np.zeros(n)
    for k in range(1, n):
        if wpos[k] and wpos[k - 1]:
            s = [np.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(wpos[k], wpos[k - 1]) if a and b]
            if s:
                speed[k] = max(s) * fps
    moving = speed > 0.25
    pocket &= moving
    clothes &= speed > 0.4
    cam = np.array([r['motion'] for r in rows])
    cam_flag = cam > max(6.0, np.percentile(cam, 95) if n else 6.0)

    res = {
        'fps': fps, 'frames': n, 'dur': round(n / fps, 2), 'face_ratio': round(float(np.mean([r['face'] for r in rows])) if n else 0, 2),
        'ng': {'talk_gum': merge(talk, fps), 'hair': merge(hair, fps), 'pocket': merge(pocket, fps)},
        'check': {'clothes': merge(clothes, fps), 'camera': merge(cam_flag, fps, pad=0.25)},
        'series': {'jaw': [None if np.isnan(x) else round(float(x), 3) for x in jaw], 'wrist_speed': [round(float(x), 3) for x in speed],
                   'motion': [round(float(x), 2) for x in cam]},
    }
    bad = np.zeros(n, bool)
    for iv in res['ng'].values():
        for a, b in iv:
            bad[int(a * fps):int(b * fps) + 1] = True
    ok, s0 = [], None
    for k in range(n + 1):
        if k < n and not bad[k]:
            s0 = k if s0 is None else s0
        elif s0 is not None:
            if (k - s0) / fps >= 2.0:
                ok.append((round(s0 / fps, 2), round(k / fps, 2)))
            s0 = None
    res['usable'] = ok
    json.dump(res, open(os.path.join(d, 'motion.json'), 'w'))
    print(os.path.basename(d.rstrip('/')), 'dur', res['dur'], 'face', res['face_ratio'], 'NG', {k: len(v) for k, v in res['ng'].items()},
          'usable', sum(b - a for a, b in ok))


if __name__ == '__main__':
    main()
