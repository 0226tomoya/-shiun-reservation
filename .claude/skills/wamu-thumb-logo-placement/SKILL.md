---
name: wamu-thumb-logo-placement
description: サムネにブランドロゴを置く（位置・大きさ・並べ方）ときに使う。
---
# ロゴの置き方

- **正方形のロゴを左上（か右上）の角**、端から 8〜30px、一辺 110〜185px。
- 複数は同じ大きさで横一列、間 10〜40px（ロゴ幅の約 25%）。2 ブランドなら左上と右上に分ける。
- 右下に白いずらし影（10〜12px）を付けることが多い。
- 大人型は文字の上下に中央揃え。ロゴを見出しの行に混ぜる（「全身［UNIQLO］コーデ」）。
- 素材は `editing/thumbs/assets/logos/`（元のサムネから 1 枚ずつ透過で切り抜いたもの。2 枚組を背景ごと切り抜かない）。
- 例: 33iLCpREnKQ（91 点、GU 2 枚 197px）/ FF3fyJYMuMU / bDfdjlubSVY
- **ロゴは回ごとに元のサムネから切り抜き直す**（同じ UNIQLO でも回ごとに大きさ・影・色味が違う。他の回の切り抜きを使い回すと形の点が落ちる）。保存名は `ブランド_IDの先頭4文字.png`。
- tune はロゴの近くの文字を引き寄せて崩すことがある。ロゴ際の文字は tune の後に目で確かめる。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
