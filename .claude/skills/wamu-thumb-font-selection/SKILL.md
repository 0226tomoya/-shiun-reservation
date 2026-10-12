---
name: wamu-thumb-font-selection
description: サムネの文字のフォントを決める・元のサムネの書体を当てるときに使う。
---
# フォントの当て方（477 本で使った回数の多い順）

- 極太ゴシック: NotoSansJP 900（3012 レイヤー）。元が縦長なら MPLUS1p 900 か NotoSansJP 900＋scale_x 0.7〜0.85。さらに太いときは同じ色の縁 3〜6px を内側に足す。
- 太い明朝: ShipporiMinchoB1 800（365）/ ZenOldMincho 900（294）/ NotoSerifJP 900（205）/ KaiseiTokumin 800（丸い仮名）。**枚ごとに 1〜5 点入れ替わるので 3〜4 種試す**。shiun の極太明朝は NotoSerifJP 900＋skew -8 が近い。
- 字間の広い大人ゴシック: ZenKakuGothicNew 700 / NotoSansJP 700。
- 手書き風: YuseiMagic 400（注記）、KleeOne 600（shiun のペン字・縦書き）、Yomogi、ZenKurenaido。
- 欧文: 極太＝Montserrat 900 / Anton / ArchivoBlack、セリフ＝PlayfairDisplay / EBGaramond / CormorantGaramond / BodoniModa、細い長体＝Italiana、筆記体＝GreatVibes / Allura。
- 手元に無い（近似しかできない）: かすれた筆文字・勘亭流、くさび形セリフの極太欧文、Didone の細い長体、Helvetica 系、縦長の極太ゴの専用書体。
- **太さより先に種類（ゴシック／明朝／手書き）を正す**。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
