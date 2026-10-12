---
name: wamu-thumb-notune-lock
description: サムネ再現で、手で直した字を自動の tune・tune_group に動かされないように固定するときに使う。
---
# 手で直した字を固定する（notune）

- レイヤーに `"notune": true` を書くと、tune.py・tune_group.py・autotune.sh・auto2.sh が動かさない。
- 前の回で手で直した字（GU2O の「か」「も」、my19 の「作」、naaE の「3」など）が、次の自動 tune でまた同じように崩れるのを防ぐ。
- 手で box.py や ext.py の矩形に戻した字には、必ず notune を付ける。
- fit.py の `lock`（動かさない値のリスト）とは別物。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
