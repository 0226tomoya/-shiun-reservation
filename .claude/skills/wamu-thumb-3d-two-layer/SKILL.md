---
name: wamu-thumb-3d-two-layer
description: サムネの白と黒（や色違い）の 2 層を重ねた立体文字を再現するときに使う。
---
# 2 層の立体文字

- 手前の層だけを的にして合わせる（他の層を的から外さない設定 `EXCL=0` で tune）。
- 後ろの層は手前と同じ書体・大きさ・字間で、右下に数 px ずらして写す（位置は measure.py で測る）。
- 2 層を別々に tune すると大きさがずれて立体に見えなくなる。
- 例: 6BbQ（+5）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
