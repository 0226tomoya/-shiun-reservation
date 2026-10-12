---
name: wamu-thumb-condensed-italic-latin
description: サムネの縦長で太い斜体の英字（BEST・数字・ブランド名）の書体を選ぶときに使う。
---
# 縦長の太い斜体の英字

- 候補（10/12 追加）: BarlowCondensedItalic 700/800/900、SairaExtraCondensed 700〜900（直立。skew -8〜-12 で斜体に）、RobotoCondensedItalic 800/900、Oswald 700、BarlowCondensed 900、BebasNeue、Anton。
- 本物の斜体書体（…Italic）は skew をかけた直立書体より字形が近い。両方を tune の候補にする: `--fonts 'BarlowCondensedItalic:900,RobotoCondensedItalic:900,SairaExtraCondensed:900,Anton:400'` と `SKEWS=0,-8,-12`。
- r47U はこれまでの 6 書体で全部下がった → 新しい書体で再挑戦。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
