---
name: wamu-thumb-semi-transparent
description: サムネの半透明の大きい数字・灰色の半透明＋白縁の中抜き字を作る・再現するときに使う。
---
# 半透明の塗り＋縁（fill_opacity）

- text レイヤーに `"fill_opacity": 0.3〜0.6` と `"strokes": [[4, "#ffffff"]]` → 縁はそのまま、塗りだけ半透明（背景が透ける）。
- qiV5 の「28」、uFDK・2EnD の灰色の半透明＋白縁の字に使う。
- 塗りの色は、元の字の中の色と背景の色から逆算する（字の中の色 ≒ 背景×(1−α)＋塗り×α）。
- 形の採点（IoU）は不透明に近い所だけを数えるので、縁の太さと位置を正確に合わせることが大事。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
