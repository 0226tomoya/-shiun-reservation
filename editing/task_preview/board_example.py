"""タスクプレビュー（artifact の db: boards/shiun-short）に書く中身を、今のファイルの状態から作る。python3 board.py → board.json"""
import os, glob, json, time
S = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad'
SS = S + '/short_src'
names = ['DSCF0030', 'DSCF0031', 'DSCF0032', 'DSCF0034', 'DSCF0035', 'DSCF0036']
prox = [n for n in names if os.path.exists(f'{SS}/proxy/{n}.mp4') and os.path.getsize(f'{SS}/proxy/{n}.mp4') > 10**6 and not os.path.exists(f'{SS}/raw/本編/{n}.MOV')]
mats = json.load(open(SS + '/materials.json')) if os.path.exists(SS + '/materials.json') else {}
talk = [n for n in prox if mats.get(n, {}).get('kind') in ('talk', 'broll')]
wav_total = 5  # MIC037 は 0.85 秒なので数えない
asr_done = len([p for p in glob.glob(SS + '/asr/*.json') if 'MIC037' not in p])
extra = json.load(open(S + '/status/board_extra.json')) if os.path.exists(S + '/status/board_extra.json') else {}
st = lambda done, total: 'done' if done >= total else ('doing' if done > 0 else 'todo')
tasks = [
    {'name': '過去のショートの分析', 'state': 'done', 'progress': 100, 'detail': '編集データと完成動画 13 本 → 決まりとスキル 4 本'},
    {'name': '縦素材の取り出し', 'state': st(len(prox), 6), 'progress': round(len(prox) / 6 * 100), 'detail': f'動画 {len(prox)}/6 本（DSCF0033 は不要データ）・ピンマイク 6/6 本'},
    {'name': '映像とピンマイクの音合わせ', 'state': st(len(talk), 6), 'progress': round(len(talk) / 6 * 100), 'detail': '相互相関でサンプル単位まで。ずれの変化はカットごとに補正'},
    {'name': '文字起こし', 'state': st(asr_done, wav_total), 'progress': round(asr_done / wav_total * 100), 'detail': f'{asr_done}/{wav_total} 本'},
]
tasks += extra.get('tasks', [
    {'name': '使うテイクを選んで構成を決める', 'state': 'todo', 'progress': 0},
    {'name': 'カット編集（ジェットカット）', 'state': 'todo', 'progress': 0},
    {'name': '字幕・商品名カード・価格・発売日・BGM', 'state': 'todo', 'progress': 0},
    {'name': '評価ループ（90 点以上まで）', 'state': 'todo', 'progress': 0},
    {'name': 'FCPXML の出力', 'state': 'todo', 'progress': 0},
])
board = {'project': 'shiun 新作ショート（新谷さんの縦素材 10/12）', 'title': 'デニムほか 新作紹介ショートの編集',
         'status_line': extra.get('status_line', '縦素材を取り出しながら、文字起こしと音合わせを進めています。'),
         'updated_at': int(time.time() * 1000), 'tasks': tasks, 'activity': extra.get('activity', [])}
json.dump(board, open(S + '/status/board.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({t['name']: t['progress'] for t in tasks}, ensure_ascii=False))
