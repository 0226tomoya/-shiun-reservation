"""Paste（com.wiheads.paste）のデータベースから FCP のクリップボード項目を取り出して解析する。

使い方:
    python3 paste_db.py db.sqlite OUT_DIR
      -> OUT_DIR/items/*.bplist（FCP のクリップボードデータ）と OUT_DIR/items.json（解析結果）を作り、一覧を表示する

対応形式:
    - 新形式 db.sqlite: ZITEMDATAENTITY.ZRAWPASTEBOARDITEMS = 0x01 + raw deflate の JSON
      （0x02 + UUID のときは .db_SUPPORT/_EXTERNAL_DATA/UUID に raw deflate の JSON）
    - FCP のデータ: com.apple.flexo.proFFPasteboardUTI = bplist（ffpasteboardobject に NSKeyedArchiver）
      タイトルの設定は FFMotionEffectValue に Motion の ozml として丸ごと入っている
"""
class Arch:
    def __init__(s,path):
        outer=plistlib.loads(open(path,'rb').read())
        s.outer=outer
        inner=plistlib.loads(outer['ffpasteboardobject'])
        s.objs=inner['$objects']; s.top=inner['$top']
    def cls(s,o):
        return s.objs[o['$class'].data]['$classname'] if isinstance(o,dict) and '$class' in o else None
    def get(s,u):
        return s.objs[u.data] if isinstance(u,plistlib.UID) else u
    def val(s,u,depth=0):
        o=s.get(u)
        c=s.cls(o)
        if c in('NSArray','NSMutableArray','NSSet','NSMutableSet'): return [s.val(x,depth+1) for x in o['NS.objects']]
        if c in('NSDictionary','NSMutableDictionary'): return {s.val(k):s.val(v,depth+1) for k,v in zip(o['NS.keys'],o['NS.objects'])}
        if c in('NSMutableString','NSString'): return o['NS.string']
        if c=='NSURL': return s.val(o['NS.relative'])
        if c in('NSMutableData','NSData'): return o['NS.data']
        if c=='NSDate': return o.get('NS.time')
        if o=='$null': return None
        return o
import sys, glob, re, json, os, sqlite3, plistlib
import xml.etree.ElementTree as ET

def rng(s):
    m=re.match(r'\{\((-?\d+)/(\d+)\),\((\d+)/(\d+)\)\}',s or '')
    if not m: return None
    a,b,c,d=map(int,m.groups()); return (a/b, c/d)

def ozml_title(x):
    x=x.decode('utf8','replace') if isinstance(x,bytes) else x
    out={}
    out['texts']=[t.strip() for t in re.findall(r'<text>(.*?)</text>',x,re.S)]
    styles=[]
    for st in re.finditer(r'<style name="[^"]*" id="\d+" factoryID="\d+">(.*?)</style>',x,re.S):
        b=st.group(1)
        f=re.search(r'<parameter name="フォント"[^>]*>\s*<font>([^<]*)</font>',b)
        sz=re.search(r'<parameter name="サイズ"[^>]*value="([^"]+)"',b)
        styles.append((f.group(1) if f else None, round(float(sz.group(1)),1) if sz else None))
    out['styles']=sorted(set(styles),key=str)
    # scenenode position (last 情報/変形/位置)
    pos=re.findall(r'<parameter name="位置" id="101"[^>]*>.*?name="X"[^>]*value="([^"]+)".*?name="Y"[^>]*value="([^"]+)"',x,re.S)
    if pos: out['pos']=[round(float(pos[-1][0]),1),round(float(pos[-1][1]),1)]
    sc=re.findall(r'<parameter name="調整" id="105"[^>]*>.*?name="X"[^>]*value="([^"]+)".*?name="Y"[^>]*value="([^"]+)"',x,re.S)
    if sc: out['scale']=[round(float(sc[-1][0]),2),round(float(sc[-1][1]),2)]
    return out

def ozml_xform(x):
    x=x.decode('utf8','replace') if isinstance(x,bytes) else x
    o={}
    for nm in ('位置','調整','回転','アンカーポイント'):
        m=re.search(r'<parameter name="%s"[^>]*>(.*?)</parameter>'%nm,x,re.S)
        if m:
            vals=re.findall(r'name="([XYZ])"[^>]*value="([^"]+)"',m.group(1))
            v={k:round(float(val),3) for k,val in vals}
            if any(abs(val-(1 if nm=='調整' else 0))>1e-6 for val in v.values()): o[nm]=v
        else:
            m=re.search(r'<parameter name="%s"[^>]*value="([^"]+)"'%nm,x)
            if m and float(m.group(1))!=0: o[nm]=float(m.group(1))
    return o

def walk(a):
    nodes=[]; seen=set()
    def effects_of(es):
        es=a.get(es); res={'custom':None,'filters':[],'xform':None}
        if not isinstance(es,dict): return res
        ce=a.get(es.get('customEffect'))
        if isinstance(ce,dict) and a.cls(ce):
            d={'class':a.cls(ce),'name':a.val(ce.get('displayName')),'id':a.val(ce.get('effectID'))}
            if a.cls(ce)=='FFMotionEffect':
                for ev in a.val(ce.get('effectValues')) or []:
                    ev=a.get(ev)
                    data=a.val(ev.get('data'))
                    if isinstance(data,bytes) and b'<ozml' in data[:200]: d.update(ozml_title(data))
            res['custom']=d
        for key in ('effects','userEffects','filterEffects','videoEffects'):
            for e in a.val(es.get(key)) or []:
                e=a.get(e)
                if isinstance(e,dict) and a.cls(e):
                    res['filters'].append({'class':a.cls(e),'name':a.val(e.get('displayName')),'id':(a.val(e.get('effectID')) or '')[-80:]})
        for e in a.val(es.get('intrinsicEffects')) or []:
            e=a.get(e)
            if a.cls(e)=='FFHeXForm3DEffect':
                cd=a.val(e.get('channelData'))
                if isinstance(cd,bytes): res['xform']=ozml_xform(cd) or None
            if a.cls(e) in('FFHeCropEffect','FFHeBlendEffect'):
                cd=a.val(e.get('channelData'))
                res.setdefault('intrinsic',[]).append(a.cls(e))
            if a.cls(e)=='FFHeColorEffect':
                inner=[a.val(a.get(x).get('displayName')) for x in (a.val(e.get('effects')) or []) if isinstance(a.get(x),dict)]
                if inner: res['filters']+= [{'class':'color','name':n,'id':''} for n in inner]
        return res
    def media(o):
        urls=[]
        def rec(u,d=0):
            if d>6: return
            x=a.get(u)
            if a.cls(x)=='NSURL': urls.append(a.val(x)); return
            if isinstance(x,dict):
                for k,v in x.items():
                    if k in('$class','persistedAnchoredObject'): continue
                    if isinstance(v,plistlib.UID): rec(v,d+1)
        rec(o.get('assetRef')) if 'assetRef' in o else None
        rec(o.get('clipRef')) if 'clipRef' in o else None
        return [u for u in urls if u and not u.endswith('.moti') and 'PETemplates' not in u]
    def visit(u,depth,parent_lane):
        o=a.get(u)
        if not isinstance(o,dict): 
            if isinstance(o,(list,)): 
                for x in o: visit(x,depth,parent_lane)
            return
        key=id(o)
        if key in seen: return
        seen.add(key)
        c=a.cls(o)
        if c and c.startswith('FFAnchored'):
            r=rng(a.val(o.get('clippedRange'))); us=rng(a.val(o.get('unclippedStart'))) if 'unclippedStart' in o else None
            n={'depth':depth,'class':c.replace('FFAnchored',''),'name':a.val(o.get('displayName')),'lane':o.get('anchoredLane'),'dur':round(r[1],2) if r else None}
            if 'effectStack' in o: n.update({k:v for k,v in effects_of(o['effectStack']).items() if v})
            m=media(o)
            if m: n['media']=[os.path.basename(x) for x in m]
            nodes.append(n)
            depth+=1
        for k,v in o.items():
            if k in('$class','persistedAnchoredObject','effectStack'): continue
            if isinstance(v,list):
                for y in v:
                    if isinstance(y,plistlib.UID): visit(y,depth,None)
                continue
            if isinstance(v,plistlib.UID):
                x=a.get(v)
                c2=a.cls(x)
                if c2 in('NSArray','NSMutableArray','NSSet','NSMutableSet'):
                    for y in x['NS.objects']: visit(y,depth,None)
                elif c2 and (c2.startswith('FFAnchored') or c2 in('NSDictionary','NSMutableDictionary')):
                    visit(v,depth,None)
    visit(a.top['root'],0,None)
    return nodes

def extract(db, outdir):
    import zlib, base64
    os.makedirs(os.path.join(outdir, 'items'), exist_ok=True)
    ext = os.path.join(os.path.dirname(db), '.db_SUPPORT', '_EXTERNAL_DATA')
    c = sqlite3.connect(db)
    for pk, b in c.execute('select ZITEM, ZRAWPASTEBOARDITEMS from ZITEMDATAENTITY'):
        if b is None:
            continue
        if b[:1] == b'\x02':
            b = open(os.path.join(ext, b[1:].split(b'\x00')[0].decode()), 'rb').read()
            raw = zlib.decompress(b, -15)
        else:
            try:
                raw = zlib.decompress(b[1:], -15)
            except zlib.error:
                raw = b
        try:
            items = json.loads(raw)
        except ValueError:
            continue
        for k, x in enumerate(items):
            v = x.get('dataByType', {}).get('com.apple.flexo.proFFPasteboardUTI')
            if v:
                open(os.path.join(outdir, 'items', f'{pk}_{k}.bplist'), 'wb').write(base64.b64decode(v))


if __name__ == '__main__':
    db, outdir = sys.argv[1:3]
    extract(db, outdir)
    itemdir = os.path.join(outdir, 'items')
    out = os.path.join(outdir, 'items.json')
    c = sqlite3.connect(db)
    meta = {r[0]: r[1:] for r in c.execute('select i.Z_PK,l.ZNAME,i.ZTITLE,i.ZDISPLAYORDERINPINBOARD,i.ZCREATEDAT from ZITEMENTITY i left join ZLISTENTITY l on l.Z_PK=i.ZLIST')}
    res = []
    for p in sorted(glob.glob(itemdir + '/*.bplist')):
        pk = int(os.path.basename(p).split('_')[0])
        a = Arch(p)
        m = meta.get(pk, (None, None, None, None))
        res.append({'pk': pk, 'board': m[0], 'title': m[1], 'order': m[2], 'nodes': walk(a)})
    res.sort(key=lambda r: (str(r['board']), r['order'] or 0))
    json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
    for r in res:
        print(f"\n### [{r['board']}] {r['title']} (pk {r['pk']})")
        for n in r['nodes']:
            s = '  ' * n['depth'] + f"{n['class']} '{n['name']}' L{n['lane']} {n['dur']}s"
            cu = n.get('custom')
            if cu:
                s += f" | {cu['name']} {cu.get('texts', '')} {cu.get('styles', '')} pos={cu.get('pos', '')}"
            if n.get('filters'):
                s += f" | F={[f['name'] for f in n['filters']]}"
            print(s[:400])
