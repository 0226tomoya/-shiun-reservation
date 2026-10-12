---
name: wamu-thumb-shapes-cv2
description: サムネの矢印・丸囲み・弧の下線・集中線などの図形を cv2 で描いて透過 PNG にするときに使う。
---
# 図形を cv2 で描く

- 元のサムネから切り抜くのは禁止。cv2 で 1280×720 の透過キャンバスに描いて、図形の外接矩形で切り出し `editing/thumbs/assets/shapes/種類_IDの先頭4文字.png` に保存する。
- 矢印: `cv2.polylines` で軸（太さは元を measure.py で測る）、先端は `cv2.fillPoly` の三角。白縁付きなら白で太く描いてから色で細く重ねる。
- 丸囲み: `cv2.ellipse`（少し傾ける、終わりを 10〜20° 開けると手描きらしい）。
- 弧の下線: `cv2.ellipse` の一部（0〜180° の一部）を太さ 6〜10px で。
- `cv2.LINE_AA` を必ず付ける（ギザギザだと形の点が落ちる）。
- 仕様には `{"type":"image","src":"assets/shapes/...png","x":..,"y":..}` で貼る。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
