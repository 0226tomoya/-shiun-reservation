"""ロゴ画像がその回のサムネと合っているか調べる（他の回からの流用・人物の写り込みを見つける）。
python3 logo_check.py [ID ...]   （省略時は全 spec）
各 image レイヤーについて、ロゴの不透明な画素と、元のサムネの同じ位置の色の差（Lab の平均 deltaE）を出す。
差が大きい（既定 25 以上）か、同じ画像を複数の回が使っているものに印を付ける。
"""
import json, os, sys, glob, collections
import cv2, numpy as np
TH = '/home/user/-shiun-reservation/editing/thumbs'
ORIG = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs'
LIM = float(os.environ.get('LIM', 25))
ids = sys.argv[1:] or [os.path.basename(f)[:-5] for f in sorted(glob.glob(os.path.join(TH, 'specs', '*.json')))]
users = collections.defaultdict(set)
for f in glob.glob(os.path.join(TH, 'specs', '*.json')):
    for L in json.load(open(f)).get('layers', []):
        if L.get('type') == 'image':
            users[L['src']].add(os.path.basename(f)[:-5])
for vid in ids:
    spec = json.load(open(os.path.join(TH, 'specs', vid + '.json')))
    o = cv2.imread(os.path.join(ORIG, vid + '.jpg'))
    if o is None:
        continue
    o = cv2.resize(o, (1280, 720))
    lab_o = cv2.cvtColor(o, cv2.COLOR_BGR2LAB).astype(np.float32)
    for L in spec.get('layers', []):
        if L.get('type') != 'image' or 'shapes/' in L['src']:
            continue
        p = L['src'] if os.path.isabs(L['src']) else os.path.join(TH, L['src'])
        im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if im is None:
            print(vid, L['src'], 'MISSING'); continue
        w = int(round(L['w'])); h = int(round(L['h'])) if not isinstance(L.get('h'), str) and L.get('h') else int(round(L['w'] * im.shape[0] / im.shape[1]))
        im = cv2.resize(im, (max(1, w), max(1, h)))
        a = im[:, :, 3] > 200 if im.shape[2] == 4 else np.ones(im.shape[:2], bool)
        x, y = int(round(L['x'])), int(round(L['y']))
        x0, y0, x1, y1 = max(0, x), max(0, y), min(1280, x + w), min(720, y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        sub = im[y0 - y:y1 - y, x0 - x:x1 - x, :3]; m = a[y0 - y:y1 - y, x0 - x:x1 - x]
        if m.sum() < 20:
            continue
        lab_l = cv2.cvtColor(np.ascontiguousarray(sub), cv2.COLOR_BGR2LAB).astype(np.float32)
        d = np.linalg.norm(lab_l - lab_o[y0:y1, x0:x1], axis=2)[m]
        de = float(np.median(d))
        flag = []
        if de >= LIM:
            flag.append('色が合わない')
        if len(users[L['src']]) > 1:
            flag.append('共有:' + ','.join(sorted(users[L['src']]))[:60])
        if L.get('rotate'):
            flag.append('回転あり(参考値)')
        if flag or len(sys.argv) > 1:
            print(f"{vid}\t{L['src']}\tdeltaE={de:.1f}\t{' / '.join(flag)}")
