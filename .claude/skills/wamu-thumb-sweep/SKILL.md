---
name: wamu-thumb-sweep
description: サムネ再現で、影を外す・erase の広げ幅（grow）を小さくする、という安くて効く試しをまとめて自動でかけるときに使う。
---
# 影外しと grow の自動の試し（sweep）

- `BAK=退避先 python3 helpers/sweep.py ID [ID…]`。点が上がったときだけ残す。
- 影: 全部外す → だめなら層ごとに外す。7周目 high_1 では 65 枚中 48 枚で影なしが上（+0.3〜+2.5、pSlZ 91.9→94.4）。元の黒いもやが背景に残るので、描いた影と二重になる。白い手書き字＋暗いぼかしの層だけは影が要る。
- grow: spec 全体の grow を 5・7・9 から、色の erase ごとの `"grow"` を 5・7 から選ぶ（10/12 から erase ごとの grow が効くようにした）。66/107 枚で小さい方が上。
- 終わったら比較画像で消し残しが無いか見る。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
