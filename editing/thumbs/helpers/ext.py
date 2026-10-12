# ext.py ID mode(thr or #hex:tol) x0 x1 y0 y1 [...] -> prints exact pixel bbox (x0 y0 x1 y1 exclusive) per region
import sys,cv2,numpy as np
im=cv2.imread('/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs/'+sys.argv[1]+'.jpg')
mode=sys.argv[2]
if mode.startswith('#'):
    c,t=mode.split(':'); c=c.lstrip('#'); bgr=np.uint8([[[int(c[4:6],16),int(c[2:4],16),int(c[0:2],16)]]])
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(float); cl=cv2.cvtColor(bgr,cv2.COLOR_BGR2LAB).astype(float)[0,0]
    m=np.linalg.norm(lab-cl,axis=2)<float(t)
elif mode.startswith('b'): m=im.max(2)<int(mode[1:])
else: m=im.min(2)>int(mode)
m=cv2.morphologyEx(m.astype(np.uint8),cv2.MORPH_OPEN,np.ones((3,3),np.uint8))>0
a=list(map(int,sys.argv[3:])); out=[]
for k in range(0,len(a),4):
    x0,x1,y0,y1=a[k:k+4]; ys,xs=np.where(m[y0:y1,x0:x1])
    out.append(f'{x0+xs.min()} {y0+ys.min()} {x0+xs.max()+1} {y0+ys.max()+1}')
print('\n'.join(out))
