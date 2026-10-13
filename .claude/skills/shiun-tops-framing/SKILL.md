---
name: shiun-tops-framing
description: ラインナップ動画でトップスを紹介している場面の画角を決めるときに使う。
---
# トップスの画角（A18 の修正）

- トップスの紹介中は全身の引きを使わない。拡大して、ラックの服と着用した上半身を大きく（膝上まで、足元は切る、椅子は端に少し）。
- 全身の引きはパンツ・シューズ・シルエットの場面に使う。
- 商品テロップの位置は変えない。
出典: `editing/knowledge/編集ルール集_わむうsns_1年分.md`（原文は `editing/knowledge/slack_wamu_sns/`）。

## 道具（10/13 A24 再現ループ 9 周目）
- `assemble_lineup.py` は商品の種類で画角を決める（plan.framing.by_category、既定は true）: 商品名に TROUSERS・PANTS・DENIM など → 中、LOAFER・BOOTS・BELT など小物 → 全身の引き、それ以外（トップス・アウター）→ 寄り。
- 寄りは姿勢（鼻・腰・膝）から「頭の上に余白、下は太ももの中ほど（腰と膝の間）」になる拡大を出す（A24 は約 2.0 倍。修正版も 2.05）。
