---
name: wamu-thumb-scoring-loop
description: サムネの再現の評価ループ（採点・比較・直す・全体の集計）を回すときに使う。
---
# 評価ループ

- 1 枚: `bash editing/thumbs/run.sh ID` → 比較画像（左上 元／右上 文字を消した背景／左下 再現／右下 差）を見る → 一番大きい差を直す → 点が上がり**見た目も近づいた変更だけ残す**。
- 点数 = 50×形の一致（IoU）＋50×文字の範囲の一致（SSIM・色）。iou_tol（にじみ 2px 許容）も参考。
- 全体: `python3 editing/thumbs/aggregate.py [--rerender]` → `summary.tsv` と分布。
- 直す順: ①フォントの種類 ②1 文字ずつの位置 ③縦位置（8px で 9 点上がった例）④erase の tol ⑤色（画素で測る）⑥縁・影の太さ。
- 禁止: 元の写真・カードの切り抜きを貼る（ロゴだけ可）。
- 結果: 2 年 477 本、平均 58.5 点（2026-10-12 10:15 時点）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
