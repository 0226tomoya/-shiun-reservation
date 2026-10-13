"""タスクプレビューの「詳細ログ」用に、作業中のログを時刻つきの 1 行ずつにまとめる。python3 detail_log.py → detail_log.json（board.json に足す）"""
import os, glob, json, time, subprocess, re
S = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad'
SS = S + '/short_src'
lines = []
def add(ts, src, text):
    lines.append({'at': int(ts * 1000), 'src': src, 'text': text[:200]})
def mtime(p): return os.path.getmtime(p) if os.path.exists(p) else time.time()
# 見張り役
for l in open(S + '/status/watchdog.log', encoding='utf-8', errors='ignore') if os.path.exists(S + '/status/watchdog.log') else []:
    m = re.match(r'(\d\d):(\d\d):(\d\d) (.*)', l.strip())
    if m:
        t = time.mktime(time.strptime(time.strftime('%Y-%m-%d ') + ':'.join(m.groups()[:3]), '%Y-%m-%d %H:%M:%S')); add(t, '見張り', m.group(4))
# 取り出し
for l in open(SS + '/pull.log', encoding='utf-8', errors='ignore') if os.path.exists(SS + '/pull.log') else []:
    m = re.match(r'done (\d+) (\d\d:\d\d:\d\d)', l.strip())
    if m:
        t = time.mktime(time.strptime(time.strftime('%Y-%m-%d ') + m.group(2), '%Y-%m-%d %H:%M:%S')); add(t, '取り出し', f'DSCF00{m.group(1)} を作業用の動画にした')
for p in glob.glob(SS + '/pull_*.log'):
    for l in open(p, encoding='utf-8', errors='ignore'):
        f = l.split()
        if len(f) >= 4 and f[0].isdigit() and int(f[0]) > 0:
            add(mtime(p), '取り出し', f'zip の中を通過: {f[3]}（{int(f[0])/1e9:.2f}GB）' + (' → 取り出した' if 'GET' in l else ''))
# 今の取り出しの読み進み
pid = subprocess.run(['pgrep', '-f', 'zipstream.py get'], capture_output=True, text=True).stdout.split()
if pid:
    try:
        io = open(f'/proc/{pid[0]}/io').read(); rc = int(re.search(r'rchar: (\d+)', io).group(1))
        add(time.time(), '取り出し', f'いま zip を読んでいる位置: {rc/1e9:.2f}GB / 11.6GB')
    except Exception: pass
if subprocess.run(['pgrep', '-f', 'libx264'], capture_output=True).returncode == 0:
    add(time.time(), '変換', '作業用の動画に変換中（ffmpeg）')
# 文字起こし
for p in sorted(glob.glob(SS + '/asr/*.log')):
    b = os.path.basename(p)[5:16]
    ls = [l.strip() for l in open(p, encoding='utf-8', errors='ignore') if re.match(r'\s*\d+\.\d+-', l)]
    done = os.path.exists(p[:-4] + '.json')
    if ls:
        add(mtime(p), '文字起こし', f'{b}: {"完了" if done else "進行中"} {len(ls)} 文。最後「{ls[-1].split(" ",2)[-1][:40]}」（{ls[-1].split()[0]}）')
# 音合わせ
for p in sorted(glob.glob(SS + '/sync/*.json')):
    try:
        j = json.load(open(p))
        add(mtime(p), '音合わせ', f'{os.path.basename(p)[:-5]}: ' + (f'{os.path.basename(j["mic"])[5:11]} と一致、ずれ {j["offset"]:+.4f} 秒・変化 {j["drift_ms"]}ms' if j.get('mic') else '一致するマイクなし'))
    except Exception: pass
# マシン
la = open('/proc/loadavg').read().split()[0]
df = subprocess.run(['df', '-h', '/'], capture_output=True, text=True).stdout.splitlines()[-1].split()
add(time.time(), 'マシン', f'負荷 {la}（4 コア）・空き容量 {df[3]}')
lines.sort(key=lambda x: x['at'], reverse=True)
seen=set(); lines=[l for l in lines if not ((l['src'],l['text']) in seen or seen.add((l['src'],l['text'])))]
json.dump(lines[:200], open(S + '/status/detail_log.json', 'w'), ensure_ascii=False)
print(len(lines))
