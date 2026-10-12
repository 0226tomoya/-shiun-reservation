---
name: wamu-thumb-color-misread
description: サムネの文字色・縁・光彩を読み違えていないか確かめるときに使う。
---
# 色の読み違い

- 縮小表示では「白＋黒縁」に見えて、実は「濃い灰＋白い光彩」（8PeJ の小さい行）のことがある。
- 黒に見えて濃紺・こげ茶の縁、白に見えてクリーム（#fcf5ee）。
- 確かめ方: 元画像を 4 倍に拡大して文字の中心・縁・外側の画素を 3 点拾う。
- 読み違いを直すと +5 以上上がることが多い。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
