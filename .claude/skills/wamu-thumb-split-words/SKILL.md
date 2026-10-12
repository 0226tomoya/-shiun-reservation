---
name: wamu-thumb-split-words
description: サムネの小さい英字の行（size 40 未満、日付・Release 表記など）を語ごとに分けて合わせるときに使う。
---
# 語ごとに分ける（split --words）

- `python3 helpers/split.py ID N --words` で、空白で区切った語ごとのレイヤーに分ける（"grp" 付き）。
- 小さい英字の行は 1 字ずつに分けると崩れる。語ごとなら字間が保たれたまま、語の位置だけ合わせられる。
- 続けて `python3 helpers/tune_group.py ID --grp LN --apply`（行全体）→ 必要なら語ごとに狭い tune。
- 例: 「24 Essential Collection　2024.07.20 sat. 22:00 - Release」→ 8 語。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
