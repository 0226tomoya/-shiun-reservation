---
name: wamu-thumb-text-behind-person
description: サムネで文字やロゴが人物の後ろに回る（頭・手が文字の手前に来る）ときに作る・再現する。
---
# 文字の後ろに人物

- 仕様の `"front": [[[x,y],…]]` に人物（頭・手）の輪郭の多角形を書くと、その中は元の画素が文字の上に戻る。
- 頭だけ見出しの手前に出す型、ロゴに人物の頭が重なる型、巨大な背景文字の型（`wamu-thumb-type-back-giant-text`）。
- 例: h3pdi0qvi94（多角形 19 点）/ F-I_ws2h6VE（手）/ umXcj756V9s
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
