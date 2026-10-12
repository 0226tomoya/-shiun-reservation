---
name: wamu-thumb-fit-color-tune
description: サムネ再現の tune で、白縁・白い光彩の色を的から外し、文字の色だけで合わせるときに使う。
---
# tune で文字の色だけを的にする（fit_color）

- レイヤーに `"fit_color": "#文字色"`（許容は `"fit_tol": 40`）を書くと、tune.py が元画像のその色の画素だけを的にする。
- 白い光彩・白縁の字で、tune が縁まで含めて合わせて字の間が空く・太るのを防ぐ。
- 黒縁の字で黒い服・髪を拾うときも、文字色を fit_color に書く。
- 黒・濃灰の字も tune にかける（autotune.sh は暗い色の字を飛ばすので、tune.py を直接呼ぶ。59Ou +12.3、CoMY +5.3）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
