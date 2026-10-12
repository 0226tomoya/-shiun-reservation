---
name: wamu-thumb-tune-limits
description: サムネ再現で tune.py を使ってはいけない文字（帯・札の中、by:layers の erase）を見分けるときに使う。
---
# tune を使えない文字

- erase が "full" の帯・札の中の文字: 目標が帯全体になり、文字が帯の大きさまで広がって崩れる。
- erase が "by":"layers" の文字: 文字と一緒に消す範囲も動くので崩れる（CViC 73→52）。
- この 2 つは measure.py で測って手で置く。
- tune の後は拡大して「〜」「,」「I」「L」「‼」を確認（縮む・重なって消える）。点がわずかに下がっても字がそろう方を採る。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
