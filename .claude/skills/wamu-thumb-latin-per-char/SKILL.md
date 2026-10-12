---
name: wamu-thumb-latin-per-char
description: サムネの英字の行（ABEMA Prime、UNIQLO:C 2025SS など）を 1 文字ずつに分けて幅を合わせるときに使う。
---
# 英字も 1 文字ずつ

- 英字の行も 1 行のままだと字間（カーニング）が元とずれる。`helpers/split.py` で 1 文字ずつに分けてから `helpers/tune.py` → +10〜+24（5周目 high_0）。
- 60〜80 点の枚でも 1 行のまま残っている見出し・副題が多い。まず 1 行のままのレイヤーを探す。
- 候補書体: MPLUS1p 900 / ZenKakuGothicNew 900 / NotoSansJP 700・800。
- 「I」「L」「,」は tune で縮んだり隣に重なったりする → 元の画素の矩形に戻す。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
