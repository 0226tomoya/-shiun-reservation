---
name: wamu-thumb-hand-font-guard
description: サムネ再現で、手書き・筆記体の文字の層に書体候補つき tune を掛けてしまう失敗を防ぐときに使う。
---
# 手書きの層に書体候補を掛けない

- 書体候補つき tune を手書きの層に掛けると、太いゴシックが勝って混ざる（VzuD）。
- tune.py は 10/12 から、層の書体が手書き・筆記体（KleeOne・YuseiMagic・ZenKurenaido・Yomogi・HachiMaruPop・Caveat・PermanentMarker・DancingScript など）なら --fonts を自動で無視する。
- 手書きの層の書体を替えたいときは、手書き系の中だけで比べる（ほぼ YuseiMagic が一番近い）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
