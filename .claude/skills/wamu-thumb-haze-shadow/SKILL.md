---
name: wamu-thumb-haze-shadow
description: サムネの元の文字の周りに広い黒いもや（ぼかし影）があるとき、再現側の影をどうするか決めるときに使う。
---
# 広い黒いもやは背景に残す

- 元の字に広い黒いもやがあると、再現で影を描く → erase がもやごと消す → 二重になって崩れる。
- **再現の文字の影を外す**と、元のもやが背景に残って合う。描画 2 回（影あり／なし）で比べるだけなので安い。
- 7周目 mid_1 で 11 枚上がった（r6Jx +8.3、Bm2x +6.2）。
- erase に「影・もやは消さない」指定は無い（足りない機能）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
