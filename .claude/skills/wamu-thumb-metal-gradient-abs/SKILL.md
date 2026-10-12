---
name: wamu-thumb-metal-gradient-abs
description: サムネの銀・金属・金のグラデの文字を、1 字ずつのレイヤーでも行全体で 1 本のグラデとして描くときに使う。
---
# 行全体で 1 本のグラデ（fill_abs）

- text の `"fill": "linear-gradient(180deg, …)"` に `"fill_abs": [x0, y0, x1, y1]`（画面の絶対座標）を足すと、グラデをその矩形に張る。1 字ずつ分けた字すべてに同じ fill と fill_abs を書けば、行全体で 1 本のグラデになる（MZmT の BEST11 は 23 段を字ごとに換算していた）。
- 矩形は元の行の外接矩形（ext.py）。段の位置は、行の縦の明るさを画素で取って % にする（銀は 暗→明→暗→明 の 3〜5 段）。
- 光彩は text にも `"glow": [px, 色, 回数]`。
- 10/12: 斜体のグラデ文字で、字の右上がグラデの範囲から欠けて縁の色が見えていたのを直した（塗りの層に左右 0.25em の余白）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
