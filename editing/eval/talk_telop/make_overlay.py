import json, glob, sys
S = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/a29v2'
fix = json.load(open(S + '/fixes.json')) if len(sys.argv) > 1 else {}
subs = []
for f in sorted(glob.glob(S + '/subs_c0*.json')):
    subs += json.load(open(f))
subs.sort(key=lambda r: r['start'])
pins = []
out = []
for r in subs:
    k = f"{r['start']:.2f}"
    t = fix.get(k, r['text'])
    if t is None:
        continue
    out.append({'start': round(r['start'], 3), 'end': round(r['end'], 3), 'text': t.replace('？？', '？')})
# 次のテロップの頭まで（間 2 秒以内）。重なりは前を切る
for i in range(len(out) - 1):
    if out[i]['end'] > out[i + 1]['start']:
        out[i]['end'] = out[i + 1]['start']
END = 1612.8
mk = [149.38, 547.26, 703.44, 974.79, 1232.31, 1272.72, 1340.51, 1498.56, END]
names = ['①服の悩み', '②お直しもいらない', '③shiunはダサくない', '考える時間がなくなった', 'shiunの靴は安い', 'shiunは失敗がない', 'まとめ', '塚田さんのSNS']
ov = {
    'wamu': True,
    'title': {'start': 149.38, 'line1': '塚田さんに聞いてみた', 'line2': 'shiunを買い続ける理由'},
    'topics': [{'start': mk[i], 'end': mk[i + 1], 'text': names[i]} for i in range(len(names))],
    'name_card': {'start': 11.18, 'role': 'shiun XSのスナップ担当', 'name': '塚田', 'honorific': 'さん'},
    'subs': out,
    'eyecatch': {'at': [149.38, 547.26, 703.44, 974.79, 1272.72, 1340.51],
                 'src': 'file:///Users/modantaimusu/Downloads/A29%20%E9%9D%92%E6%9F%B3%E3%81%95%E3%82%93XS%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6/%E3%82%8F%E3%82%80%E3%81%86%E3%82%A2%E3%82%A4%E3%82%AD%E3%83%A3%E3%83%83%E3%83%81.mp4'},
    'pins': [{'at': 11.18, 'note': 'ゲストの名前: 話の中では「塚田さん」「つかにー」。ファイル名は「青柳さん」。名前カード・見出しは「塚田さん」にした'}] + sorted(json.load(open(S + '/pins_extra.json')), key=lambda p: p['at']),
}
json.dump(ov, open(S + '/overlay_v2.json', 'w'), ensure_ascii=False, indent=1)
print('subs', len(out), 'pins', len(ov['pins']), 'max len', max(len(x['text']) for x in out))
