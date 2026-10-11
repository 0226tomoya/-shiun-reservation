#!/bin/bash
# 使い方: bash run.sh 動画ID [fit]   → 採点と比較画像（$OUT/ID_compare.jpg）
cd "$(dirname "$0")"
export THUMB_ORIG=/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs
OUT=/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/th/out
[ "$2" = fit ] && python3 fit.py specs/$1.json
python3 render.py specs/$1.json --out $OUT
