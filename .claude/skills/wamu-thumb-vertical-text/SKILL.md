---
name: wamu-thumb-vertical-text
description: サムネの縦書き（右端の肩書き「低身長ディレクターが解説」など）を作る・再現するときに使う。
---
# 縦書き

- 右端に縦書きで肩書き・つぶやき: `"vertical":true, "anchor":"ct"`、KleeOne 600 か YuseiMagic、size 50〜60。例 sX47JbCnMmQ「低身長のカリスマ」（x 1228, y 26, KleeOne 600, 56px）。
- 一番言いたい語を一番太く・大きく・黄色にすることもある（w6XyOjl97X0）。
- split は縦書きに効かない → 1 文字ずつのレイヤーを手で縦に並べる。
- 斜めの縦書きは rotate で。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
