---
name: wamu-thumb-vertical-split
description: サムネの縦書きの文字を 1 字ずつのレイヤーに分けて合わせるときに使う。
---
# 縦書きを 1 字ずつ

- `python3 helpers/vseg.py ID x0 x1 y0 y1 white|yellow|dark [thr]` で、縦書きの行を画素の切れ目で区切り、1 字ずつの矩形を出す（split.py は縦書き非対応）。
- 濁点・2 画に割れる字は矩形を手でまとめ、矩形の数を字の数に合わせる。
- 出た矩形に 1 字ずつ text レイヤーを置き、大きさを矩形の高さに合わせる。
- 例: w6Xy +10.7。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
