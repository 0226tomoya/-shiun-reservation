# usage: chars.py ID y0 y1 x0 x1 thr k  : columns (after opening k) with each column's top/bottom
import cv2,numpy as np,sys
I=sys.argv[1]; y0,y1,x0,x1=map(int,sys.argv[2:6]); thr=int(sys.argv[6]); k=int(sys.argv[7])
mode=sys.argv[8] if len(sys.argv)>8 else 'white'
im=cv2.imread('/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs/'+I+'.jpg').astype(int)[y0:y1,x0:x1]
m=(im.min(2)>thr) if mode=='white' else (im.max(2)<thr)
m=cv2.morphologyEx(m.astype(np.uint8),cv2.MORPH_OPEN,np.ones((k,k),np.uint8))>0
ch=m.any(0); s=None; out=[]
for i,v in enumerate(list(ch)+[False]):
    if v and s is None: s=i
    if not v and s is not None:
        ys=np.where(m[:,s:i].any(1))[0]; out.append((x0+s,x0+i-1,y0+ys.min(),y0+ys.max())); s=None
for o in out: print(o)
