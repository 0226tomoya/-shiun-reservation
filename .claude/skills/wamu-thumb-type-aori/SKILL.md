---
name: wamu-thumb-type-aori
description: わむうのサムネで一番多い「煽り型」（UNIQLO・GU・MUJI の購入品、マストバイ、ランキング、失敗談）を作る・再現するときに使う。
---
# 煽り型（477 本の大半）

- 画面の**下 1/3〜1/2 に、画面幅いっぱいの特大見出し 1〜2 行**。左右の余白は 10〜30px、下端は y≒700。
- 2 行のとき: 上段＝中見出し（文字の高さ 100〜150px、size 110〜160）、下段＝特大（高さ 190〜300px、size 200〜300）。下段が結論の語（「マストバイ」「絶対買い」「全て分かる!!」）。
- 書体は NotoSansJP 900（元は少し縦長: scale_x 0.78〜0.95、字間 -0.03〜-0.07、palt）。強調の行は右に少し傾ける（skew -6〜-8）。
- 色は白＋黒ぼかし影が基本、結論の 1 語か数字だけ黄 / 金 / 赤（`wamu-thumb-color-*`）。
- 左上（か右上）に正方形のブランドロゴ（`wamu-thumb-logo-placement`）。
- 人物は中央〜右。見出しは顔より下、人物の手前に重ねてよい。
- 手書き風の注記を 1 つ（`wamu-thumb-handwritten-note`）。
- 例（点の高い再現）: 7Mrqw2dPfbo / NhknLPBvx6I / Df9CmIZ8EFA / SVONMVzPGEM（GU「絶対 買い」黄の 2 語＋白の下段）
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
