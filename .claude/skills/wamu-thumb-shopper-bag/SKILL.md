---
name: wamu-thumb-shopper-bag
description: サムネで人物が持つ紙袋（ショッパー）にブランドロゴが付いている型を作る・再現するときに使う。
---
# 紙袋（ショッパー）の型

- 紙袋は写真なので切り抜かない。rect で描く（UNIQLO=白地に赤ロゴ、GU=紺、MUJI=クラフト茶 #b08a5c 前後）。角は radius 2〜4、傾きは css_transform の rotate。
- ロゴはその回のサムネから「ロゴの箱だけ」切り直して紙袋の rect の上に貼る。
- 人物の手・腕が紙袋の手前にあるなら front で戻す。
- 写真の切り抜きを rect に変えると点は 5〜6 下がる（xq6q 88→82）が、これが正しい再現。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
