#!/bin/bash
# autotune.sh ID [fonts] : tune all text layers; keep if better
cd /home/user/-shiun-reservation/editing/thumbs
S=${BAK:-/tmp/autotune_bak}; mkdir -p $S
ID=$1; F=$2
cp specs/$ID.json $S/$ID.at.json
old=$(timeout 60 bash run.sh $ID | tail -1 | python3 -c "import json,sys;print(json.loads(sys.stdin.read())['score'])")
N=$(python3 -c "
import json;s=json.load(open('specs/$ID.json'));print(','.join(str(i) for i,L in enumerate(s['layers']) if L['type']=='text' and not L.get('vertical') and not ((L.get('color') or '#fff').startswith('#') and len(L.get('color') or '#fff')==7 and sum(int(L['color'][k:k+2],16) for k in (1,3,5))<240 and not L.get('fill'))))")
if [ -n "$F" ]; then PAD=${PAD:-20} timeout 170 python3 helpers/tune.py $ID --apply --layers $N --fonts "$F" >/dev/null 2>&1; else PAD=${PAD:-20} timeout 170 python3 helpers/tune.py $ID --apply --layers $N >/dev/null 2>&1; fi
new=$(timeout 60 bash run.sh $ID | tail -1 | python3 -c "import json,sys;print(json.loads(sys.stdin.read())['score'])")
echo "autotune $ID old $old new $new"
python3 -c "import sys;sys.exit(0 if $new>$old else 1)" || { cp $S/$ID.at.json specs/$ID.json; timeout 60 bash run.sh $ID >/dev/null; echo reverted; }
