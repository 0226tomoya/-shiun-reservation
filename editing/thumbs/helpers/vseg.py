# vseg.py ID x0 x1 y0 y1 mode(white|yellow|dark) [thr] : vertical segments (rows), with x range per segment
import cv2,numpy as np,sys
I=sys.argv[1];x0,x1,y0,y1=map(int,sys.argv[2:6]);mode=sys.argv[6];thr=int(sys.argv[7]) if len(sys.argv)>7 else 235
im=cv2.imread('/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs/'+I+'.jpg').astype(int)
b,g,r=im[...,0],im[...,1],im[...,2]
m={'white':im.min(2)>thr,'yellow':(r>200)&(g>180)&(b<120),'dark':im.max(2)<thr}[mode][y0:y1,x0:x1]
m=cv2.morphologyEx(m.astype(np.uint8),cv2.MORPH_OPEN,np.ones((3,3),np.uint8))>0
rw=m.sum(1)>2;s=None
for i,v in enumerate(list(rw)+[False]):
    if v and s is None:s=i
    if not v and s is not None:
        xs=np.where(m[s:i].any(0))[0];print([x0+xs.min(),y0+s,x0+xs.max()+1,y0+i]);s=None
