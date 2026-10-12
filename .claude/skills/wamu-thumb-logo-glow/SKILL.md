---
name: wamu-thumb-logo-glow
description: サムネのロゴ（image）に白い光彩・ぼかし縁を付けるときに使う。
---
# ロゴの光彩（glow）

- image レイヤーに `"glow": [ぼかし px, 色, 重ねる回数]`（例 `[8, "#ffffff", 2]`）。CSS の drop-shadow を重ねる。
- ロゴを切り直すと、元にあった白い光彩が消えて点が落ちる → glow で戻す（rect の radial-gradient で代用していたもの: _Gnn 62.6→67.4）。
- 光彩の広さは元画像で、ロゴの端から白が消えるまでの距離を測って決める（6〜12px が多い）。
- 字だけのロゴは erase も full から色指定に替えると落ち幅が小さい（Cl-J −6.6→−2.2）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
