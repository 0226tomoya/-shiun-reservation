---
name: wamu-thumb-italic-numbers
description: サムネの斜体の大きい数字（20・BEST7 など）を合わせるときに使う。
---
# 斜体の数字

- 数字は skew -8 前後を手で入れて、元の外接矩形（helpers/ext.py）に合わせる（Famd の「20」+4.9）。
- tune の SKEWS 自動選択は 0〜-2 を選びがちで効かない → skew は手で決めてから tune で位置だけ。
- 直しの矩形は半分の大きさの比較画像で目測しない。元画像の列の切れ目（ext.py / 画素の地図）から取る。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
