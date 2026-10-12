---
name: wamu-thumb-white-on-white
description: サムネの白い壁・白い服の上にある白い字を合わせるときに使う。
---
# 白地の白字

- tune の的を文字の白だけにする: レイヤーに `"fit_color": "#ffffff", "fit_tol": 12` → tune.py（euYy 40.2→56.7）。
- erase の色の tol も 7〜12 に絞る（壁の白を拾わない）。
- 矩形を手で取ると壁まで入って崩れる（Kcpj −10）。画素の地図で字の影（暗い縁）から輪郭を読む。
- 白文字に薄い影があるなら、影の暗い縁の方が背景と区別しやすい → 影の位置から字の位置を決める。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
