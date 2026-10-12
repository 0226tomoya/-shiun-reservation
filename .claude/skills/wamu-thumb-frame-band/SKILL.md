---
name: wamu-thumb-frame-band
description: サムネの白い細枠・半透明の黒帯・白帯を作る・再現するときに使う。
---
# 枠・帯

- 白い細枠: `{"type":"rect","x":12,"y":12,"w":1256,"h":696,"fill":"transparent","border":[5,"#ffffff"]}`（大人型・shiun）。
- 半透明の黒帯: `"fill":"#000000","opacity":0.51`（0.5 だと形の採点に入らない）。見出しの下半分に重ねる。
- 白帯＋黒字（字間 0.3em）、黒帯＋白字のラベル。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
