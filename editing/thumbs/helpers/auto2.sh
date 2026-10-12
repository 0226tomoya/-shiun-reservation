#!/bin/bash
# auto.sh ID : tune all text layers up to twice, keep if score rises
cd /home/user/-shiun-reservation/editing/thumbs
S=${BAK:-/tmp/auto_bak}; mkdir -p $S
id=$1; shift
sc(){ bash run.sh $id | python3 -c 'import json,sys;print(json.load(sys.stdin)["score"])'; }
s0=$(sc); best=$s0; cp specs/$id.json $S/$id.best.json
for pass in 1 2; do
  timeout 300 python3 helpers/tune.py $id --apply "$@" > $S/$id.tune$pass.log 2>&1
  s=$(sc); echo "pass$pass $s"
  if python3 -c "import sys;sys.exit(0 if $s>$best else 1)"; then best=$s; cp specs/$id.json $S/$id.best.json; else cp $S/$id.best.json specs/$id.json; break; fi
done
cp $S/$id.best.json specs/$id.json; bash run.sh $id >/dev/null
echo "$id $s0 $best" | tee -a $S/auto.log
