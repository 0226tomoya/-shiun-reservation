---
name: wamu-thumb-front-person
description: サムネで人物が文字の手前に来る（文字が人物の後ろに回る）ところを再現するときに使う。
---
# 人物を文字の手前に戻す（front）

- 人物の頭・腕・服が文字に重なって手前にある場合は、仕様の `front` に多角形を入れて元の画素を上に戻す。
- 付け忘れが多い（5周目 mid_0 で 5 枚、+0.6〜+1.3）。比較画像で文字が人物の上に乗っていたら付ける。
- 3 層型（人物の後ろに濃灰の巨大 2 文字）は必ず front が要る（wamu-thumb-text-behind-person）。
- 字の形で背景を切り抜く（靴に重なる所だけ白く抜く等、GjAV「5.5cmUP」）は、今の render.py ではできない（未解決）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
