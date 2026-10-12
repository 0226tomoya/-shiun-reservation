---
name: wamu-thumb-erase-colors
description: サムネ再現で erase の色リストを決める（暗い色で髪・服を消さない、ロゴは full）ときに使う。
---
# erase の色

- 色リストに暗い色（#222・#333）を入れると髪・服まで消える → 外す（b_AV +4.5）。
- ロゴの消しは色指定でなく "full"（F-I_ +2.5）。
- 白縁の文字は縁の白も入れる（OvZs +4.7）。
- 白い壁・白い服の近くは tol を 7〜16 に絞る。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
