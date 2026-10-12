"""box.py ID i x0 y0 x1 y1 [i x0 y0 x1 y1 ...]: snap layer i's drawn fill bbox to the given box (size, scale_x, x, y)."""
import json, os, sys
import numpy as np
TH='/home/user/-shiun-reservation/editing/thumbs'; sys.path.insert(0,TH); os.chdir(TH)
import render as R
vid=sys.argv[1]; a=sys.argv[2:]
sp=f'specs/{vid}.json'; s=json.load(open(sp))
from playwright.sync_api import sync_playwright
def bbox(page,L):
    L2={k:v for k,v in L.items() if k not in('strokes','shadow','hollow','opacity')}
    L2['color']='#ff0000'; L2.pop('fill',None)
    im=R.render_layers({'id':vid,'layers':[L2]},page); m=im[:,:,3]>128
    ys,xs=np.where(m); return xs.min(),ys.min(),xs.max()+1,ys.max()+1
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args=['--allow-file-access-from-files'])
    page=b.new_page(viewport={'width':R.W,'height':R.H})
    for k in range(0,len(a),5):
        i=int(a[k]); X0,Y0,X1,Y1=map(float,a[k+1:k+5]); L=s['layers'][i]
        for it in range(4):
            x0,y0,x1,y1=bbox(page,L)
            fs=(Y1-Y0)/(y1-y0); L['size']=round(L['size']*fs,1)
            x0,y0,x1,y1=bbox(page,L)
            L['scale_x']=round(L.get('scale_x',1)*(X1-X0)/(x1-x0),3)
            x0,y0,x1,y1=bbox(page,L)
            L['x']=round(L['x']+(X0-x0),1); L['y']=round(L['y']+(Y0-y0),1)
        print(i,bbox(page,L),L['size'],L['scale_x'])
    b.close()
json.dump(s,open(sp,'w'),ensure_ascii=False)
