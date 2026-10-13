---
name: shiun-insert-explain-visual
description: 話している内容が画で見えるようにインサートを選ぶ（脚長効果・ディテール・股上股下・サイズの話）ときに使う。
---
# 話を画で見せる

- 「脚長効果」→全身の着用、「ディテール（地襟・ウエストベルト・裏地）」→物撮りか寄り（暗く小さいと伝わらない）。
- 股上・股下→パンツの画像で場所を示す。サイズの話の間は shiun のサイズ表を出しておく。
- Q&A の数値トーク（股下 70〜72cm）を顔アップだけで流さない。
- 素材の違い（スムース／シュリンク）→接写にラベルを付けて 2 分割。
出典: `editing/knowledge/編集ルール集_わむうsns_1年分.md`（原文は `editing/knowledge/slack_wamu_sns/`）。

## 寄り写真を足したとき（10/13）
- 後から届いた写真（A24 は「色調整済み」140 枚）は、1 枚ずつ映っている部位（toe・saddle・stitch・heel・sole・outsole・sole_edge・opening・inside・top・worn など）を `plans/A24_insert_ledger.json` の photos に書き、plan の商品の photos_more にフォルダを足す。`auto_insert.py` が発言の言葉（KW）と部位を合わせて選ぶ。
- 紹介イン・価格の背景は、これまでどおり SNS 用高画質（photos）から。寄り写真は説明の所だけ。
