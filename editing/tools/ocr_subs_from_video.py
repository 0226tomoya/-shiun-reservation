import subprocess, numpy as np, json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/ai2/ocrjp')
from ocrjp import read_line
src,y0,y1,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
W=int(sys.argv[5]) if len(sys.argv)>5 else 1080
fps=10; H=y1-y0
raw=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',src,'-vf',f'fps={fps},crop={W}:{H}:0:{y0},format=gray','-f','rawvideo','-'],capture_output=True).stdout
fr=np.frombuffer(raw,np.uint8).reshape(-1,H,W)
ev=[]; cur=None; prev=None
for i in range(len(fr)):
    m=fr[i]>200
    if prev is None or (m^prev).mean()>0.003:
        t=read_line(fr[i])
        if not (cur and cur['text']==t):
            if cur: cur['end']=round(i/fps,2); ev.append(cur)
            cur={'start':round(i/fps,2),'text':t}
    prev=m
if cur: cur['end']=round(len(fr)/fps,2); ev.append(cur)
ev=[e for e in ev if e['text'] and e['end']-e['start']>=0.2]
json.dump(ev,open(out,'w'),ensure_ascii=False,indent=1)
print(len(ev))
for e in ev: print(e['start'],e['end'],e['text'])
