---
name: wamu-thumb-regroup
description: サムネ再現で、前の回に 1 字ずつに分けた字（grp の無いもの）を行ごとにまとめ直して tune_group を使えるようにするときに使う。
---
# 行のまとめ直し（regroup）

- `python3 helpers/regroup.py ID`（案を表示）→ `--apply` で "grp": "R0"… を付ける。
- 同じ行の判定: 1 字の text で、回転・斜体・縦書きが同じ、大きさの差 5 割以内（かなの縮小も同じ行）、行の高さの差が字の 0.6 倍以内、隣の字との距離が字の 2.2 倍以内、レイヤーの並びが続いている。
- 付けた後: `python3 helpers/tune_group.py ID --grp R1 --apply`。
- 7周目 high_0 では、字ごと tune で散っていない枚には効果が無かった（同点〜−0.1）。字が散った・空いた行にだけ使う。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
