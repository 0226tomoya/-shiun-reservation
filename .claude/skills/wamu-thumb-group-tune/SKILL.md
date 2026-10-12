---
name: wamu-thumb-group-tune
description: サムネ再現で、1 字ずつに分けた行を字間・並びを保ったまま合わせる（tune で字の間が空く・重なる・縮むのを防ぐ）ときに使う。
---
# 行ごとに合わせる（字間の制約）

- `python3 helpers/tune_group.py ID --grp L5 --apply`（split.py が付けた "grp" ごと。複数行は L5・L5_1…）／`--layers 3,4,5` でも可。
- 行全体で 大きさ s・字間 k（行の向きに沿った中心間隔の倍率）・位置 だけを探す → 字の並び・高さは崩れない。回転した行は向きを自動で取る。`--rots -2,0,2` で行の傾きも、`--spacing-only` で大きさを固定して字間だけ。
- `--fine` で最後に各字を ±2px（FINE）だけ個別に。
- おすすめの順: split → tune_group → 狭い字ごと tune（`PAD=8 S0=0.96 S1=1.041 X0=0.96 X1=1.041 python3 helpers/tune.py ID --apply --layers …`）。点は字ごと tune とほぼ同じ（±0.3）で、字間が崩れない。字ごと tune で字が散った・空いたときはこれに替える。
- tune.py は 10/12 に採点の偏り（置いた箱の中だけで元の文字を数え、縮めるほど得をする）を直した。旧の動きは `OLDIOU=1`。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
