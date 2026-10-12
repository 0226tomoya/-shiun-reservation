---
name: wamu-thumb-measure-helpers
description: サムネの再現で元の文字の位置・大きさを測る道具（measure.py・chars.py・snap・tune・split）を使うときに使う。
---
# 測る道具（editing/thumbs/）

- `measure.py ID x y w h '#色' [tol]`: 色の外接矩形と横のかたまり
- `helpers/chars.py ID y0 y1 x0 x1 thr k [white|black]`: 開処理してから列ごとの外接矩形（1 文字ずつの目標）
- `helpers/snap_b16.py`・`snap_b11.py`: 描いた形の外接矩形を目標に合わせる（fit より軽い）
- `helpers/split.py ID i`: 1 文字ずつのレイヤーに分ける
- `helpers/tune.py ID --apply`: 1 文字ずつ位置・大きさ・横幅・フォント・傾きを探す
- 白以外の文字はしきい値で測る（黄: R>200・G>140・B<90、赤: R>150・G<70・B<80）。
- 拡大画像を目で読んだ座標は倍率でずれるので、必ず画素で測る。
- `fit.py` は重く、同じ色の服を拾って崩れやすい（混んでいるときは使わない）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
