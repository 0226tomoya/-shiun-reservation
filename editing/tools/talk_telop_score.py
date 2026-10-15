"""フルテロップの評価: 作ったテロップと手本（画面から読み取った字幕）を比べる
点 = 出す・出さないの一致×30 ＋ 文の近さ（時刻で重なる手本の字幕との一致度）×50 ＋ 枚数の近さ×20"""
import json, sys, difflib, unicodedata, re
def norm(s): return re.sub(r'[\s、。,.!?！？「」（）()]', '', unicodedata.normalize('NFKC', s or '')).lower()
gold=json.load(open(sys.argv[1])); pred=json.load(open(sys.argv[2])); segs=[l.split('\t') for l in open(sys.argv[3]).read().splitlines()[1:]]
def over(xs,a,b): return [x for x in xs if min(b,x['end'])-max(a,x['start'])>0.35*min(b-a, x['end']-x['start'])]
agree=0; sims=[]; rows=[]
for s in segs:
    a,b=float(s[1]),float(s[2]); g=over(gold,a,b); p=over(pred,a,b)
    agree+= (bool(g)==bool(p))
    if g:
        gt=''.join(x['text'] for x in g); pt=''.join(x['text'] for x in p)
        r=difflib.SequenceMatcher(None,norm(gt),norm(pt)).ratio(); sims.append(r)
        rows.append((round(r,2),s[4],gt,pt))
skip=agree/len(segs); sim=sum(sims)/max(len(sims),1); cnt=1-min(1,abs(len(pred)-len(gold))/len(gold))
print(json.dumps({'点':round(skip*30+sim*50+cnt*20,1),'出す出さない':round(skip,3),'文の近さ':round(sim,3),'枚数':f'{len(pred)}/{len(gold)}'},ensure_ascii=False))
if '--detail' in sys.argv:
    for r in sorted(rows)[:25]: print(r)
