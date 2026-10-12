---
name: wamu-thumb-renderer-spec
description: サムネの再現・作成に使う仕様（JSON）の書き方（text・rect・image・line、erase・front）を調べるときに使う。
---
# 仕様（render.py）

- `editing/thumbs/render.py` の先頭に全書式。主なもの:
  - text: text / runs（size_em・spacing・dy）/ font・weight・size / color か fill（グラデ）/ strokes [[太さ,色],…]（内側から）/ shadow / spacing / line / rotate・skew・skew_y・scale_x / vertical / hollow / palt / css_transform（遠近）/ anchor
  - rect（border・radius・opacity）・image（assets/logos）・line
  - erase: 元の文字の範囲（色で拾う。`colors`・`tol`・`grow`・`full`・`poly`）
  - front: 人物を手前に戻す多角形
- 採点・比較: `bash editing/thumbs/run.sh ID`（比較画像の右上に元の文字が残っていたら erase 不足）
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
