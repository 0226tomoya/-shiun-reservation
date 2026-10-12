---
name: wamu-thumb-type-size-compare
description: shiun の「身長別サイズ徹底比較」サムネ（明朝の横一杯の見出し＋半分に重なる半透明の黒帯）を作る・再現するときに使う。
---
# 身長別サイズ比較の型

- 見出し「身長別サイズ徹底比較」を ShipporiMinchoB1 800 の白で画面幅いっぱい（1 文字 size 137〜153、scale_x 0.91〜0.95、回転 0.5〜1.5°、1 文字ずつのレイヤー）。
- 見出しの下半分に重なる半透明の黒帯: `{"type":"rect","x":15,"y":352,"w":1250,"h":55,"fill":"#000000","opacity":0.51}`（opacity は 0.51 以上でないと形の採点に数えられない）。
- 下に「shiun 26 Summer ○○ Collection」と「日付 sat 10pm - Release」をコンデンスのセリフ英字で中央寄せ。
- 例: zegi2G4CpmQ（74 点）/ srX4M-d0DUk（72 点）
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
