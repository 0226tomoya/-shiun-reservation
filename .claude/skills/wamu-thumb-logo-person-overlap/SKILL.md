---
name: wamu-thumb-logo-person-overlap
description: サムネのロゴに人物（頭・髪・指）が重なっているときに、ロゴを人物抜きで作るときに使う。
---
# 人物が重なったロゴ

- ロゴをその回から切り直し、人物の部分は透過（アルファ 0）にする。
- 仕様の `front` に人物の多角形を入れて元の人物を上に戻す（人物はロゴの手前に見える）。
- 透過の縁に背景の埋め跡が出ることがある（nESP 48.5→44.4）→ front の多角形を 2〜3px 外へ広げて跡を隠す。
- 他の回のロゴを流用しない（CFzF で見つかった例）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
