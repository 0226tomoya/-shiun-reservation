---
name: wamu-thumb-arrows-lines-callouts
description: サムネの矢印・下線・吹き出し・ラベル（赤い曲がり矢印、白い角丸ラベル、斜めの白帯）を作る・再現するときに使う。
---
# 矢印・線・吹き出し

- 赤い曲がり矢印はロゴ素材（assets/logos/arrow_red_curve_*.png）を使い回す。直線は `line`。
- 白い角丸ラベル（ワイドパンツ等）: rect＋radius、黒字。斜めの白帯＋黒字の説明文（-2°）。
- 下線は弧が多いが、今は line を短くつないで近似（弧の部品が無い）。
- 吹き出しは rect の radius で近似（尻尾は描けない）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
