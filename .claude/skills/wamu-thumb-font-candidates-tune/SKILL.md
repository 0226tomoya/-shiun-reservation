---
name: wamu-thumb-font-candidates-tune
description: サムネ再現で文字ごとに書体の候補を付けて tune し、明朝・ゴシック・斜体を自動で選ぶときに使う。
---
# 書体の候補つき tune

- `bash helpers/autotune.sh ID "候補"`（点が上がった時だけ残す。下がれば自動で戻す）。中身は `helpers/tune.py ID --apply --layers N --fonts 候補`。
- 明朝の候補: `ZenOldMincho:900,NotoSerifJP:900,ShipporiMinchoB1:800,KaiseiTokumin:800`
- ゴシックの候補: `NotoSansJP:900,MPLUS1p:900,ZenKakuGothicNew:900`
- 斜体は `SKEWS=-6,-10,-14` を付けると傾きも一緒に選ぶ。
- 1 回かけるだけで +3〜+10 の枚が多い（5周目 mid_0、103 枚）。
- 白い服・白縁・帯の近く・細い手書きの字は崩れることがある → 比較画像で崩れた字だけ戻す。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
