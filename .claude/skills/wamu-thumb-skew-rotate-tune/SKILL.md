---
name: wamu-thumb-skew-rotate-tune
description: サムネの斜体・傾いた文字を tune.py で合わせる（SKEWS / ROTS）ときに使う。
---
# 斜体・傾きを tune で選ぶ

- `SKEWS=-6,-10,-14 python3 helpers/tune.py ID --apply --layers N`（斜体）、`ROTS=-4,-2,2,4`（傾き）。
- w1dT +9、65za +9（5周目 high_0）。
- 縦書きは tune.py が飛ばす → 横書きの 1 文字ずつのレイヤーに置き換えて（helpers/vseg.py で矩形）から合わせる（iTah +18）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
