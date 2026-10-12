---
name: wamu-thumb-pixel-map
description: サムネの、くっついた字や濁点の切れ目を、画素の地図（#/. の印字）で読んで 1 字ずつの矩形を決めるときに使う。
---
# 画素の地図で字の切れ目を読む

- `python3 helpers/ext.py ID 235 x0 x1 y0 y1`（白）／`b60`（暗い色）／`#ffe600:20`（色＋許容）で、範囲ごとの正確な外接矩形を出す。
- くっついた字・濁点は、範囲を行ごとに `#`（文字）`.`（背景）で print した地図を見て、縦の切れ目を自分で決める。
- 矩形が決まったら `helpers/box.py` で 1 字ずつ合わせる。
- 白い服・紙袋・ニットの近くは tune が背景を拾うので、この方法で手で決める。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
