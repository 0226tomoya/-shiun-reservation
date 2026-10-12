---
name: wamu-thumb-logo-check
description: サムネのロゴ画像が、その回のサムネから切ったものか（他の回の流用でないか）を調べるときに使う。
---
# ロゴの流用を調べる（logo_check）

- `python3 helpers/logo_check.py [ID…]`（省略で全 spec）。ロゴの不透明な画素と、元のサムネの同じ位置の色の差（deltaE の中央値）と、同じ画像を使っている回を出す。
- 同じ画像を複数の回が使っていて、deltaE が 0 でない側は流用 → その回から切り直す（AzNo の AURALEE は切り直しで 80→89）。
- deltaE が大きい（25 以上）ものは位置ずれか別物。
- 回転したロゴは参考値。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
