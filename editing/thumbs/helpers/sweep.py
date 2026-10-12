"""安くて効く 2 つの試しを自動でかけ、点が上がったときだけ残す（7周目 high_1 で分かったこと）。
  1. 文字の影（shadow）を外す: 全部外す → 層ごとに外す（元の黒いもやが背景に残るので、描いた影と二重になっている枚が多い）
  2. erase の広げ幅（grow）を 5・7・9 から選ぶ（11〜17 のままの枚が多く、小さい方が上のことが多い）
python3 sweep.py ID [ID ...] [--no-shadow] [--no-grow]
退避: $BAK（既定 /tmp/sweep_bak）。"notune" の層の影は触らない。
"""
import json, os, sys, subprocess, shutil, copy
TH = '/home/user/-shiun-reservation/editing/thumbs'
BAK = os.environ.get('BAK', '/tmp/sweep_bak'); os.makedirs(BAK, exist_ok=True)
args = [a for a in sys.argv[1:] if not a.startswith('--')]


def score(vid):
    out = subprocess.run(['bash', 'run.sh', vid], cwd=TH, capture_output=True, text=True).stdout.strip().splitlines()
    return json.loads(out[-1])['score']


for vid in args:
    sp = os.path.join(TH, 'specs', vid + '.json')
    shutil.copy(sp, os.path.join(BAK, vid + '.json'))
    spec = json.load(open(sp))
    best = score(vid); s0 = best; log = []

    def trial(new, what):
        global best, spec
        json.dump(new, open(sp, 'w'), ensure_ascii=False, indent=1)
        s = score(vid)
        if s > best + 0.05:
            best, spec = s, new; log.append(f'{what} {s}')
            return True
        json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
        return False

    if '--no-shadow' not in sys.argv:
        sh = [i for i, L in enumerate(spec['layers']) if L.get('type') == 'text' and L.get('shadow') and not L.get('notune')]
        if sh:
            new = copy.deepcopy(spec)
            for i in sh:
                new['layers'][i].pop('shadow', None)
            if not trial(new, '影を全部外す') and len(sh) > 1:
                for i in sh:
                    new = copy.deepcopy(spec); new['layers'][i].pop('shadow', None)
                    trial(new, f'L{i} の影を外す')
    if '--no-grow' not in sys.argv:
        cur = spec.get('grow', 11)
        for g in (5, 7, 9):
            if g != cur:
                new = copy.deepcopy(spec); new['grow'] = g
                trial(new, f'grow={g}')
        for k, e in enumerate(spec.get('erase', [])):  # 範囲ごとの grow（色の erase）
            if isinstance(e, dict) and not e.get('full') and e.get('by') != 'layers':
                for g in (5, 7):
                    new = copy.deepcopy(spec); new['erase'][k]['grow'] = g
                    trial(new, f'erase{k} grow={g}')
    json.dump(spec, open(sp, 'w'), ensure_ascii=False, indent=1)
    subprocess.run(['bash', 'run.sh', vid], cwd=TH, capture_output=True)
    print(f'{vid}\t{s0}\t{best}\t{"; ".join(log)}', flush=True)
