---
name: wamu-thumb-split-exceptions
description: サムネ再現で split（1 字ずつに分ける）をしてはいけない行を見分けるときに使う。
---
# split すると崩れる行

- ~~回転した行~~ → 10/12 から split.py が回転・斜体のまま分けられる（分けた直後の点は変わらない）。分けた後は tune_group.py で行ごとに合わせる。
- 価格・日付・記号入りの行（¥1,990 の「1」「,」が縮む）。
- 細い欧文の見出し（CLOSET TOUR、BEST BUY）。
- 遠近の付いた金文字（css_transform）。
- 斜体の行 → 上と同じく split.py で分けられる（skew を保ったまま 1 字ずつ）。
- これらは点が +10 上がっても字が崩れるので採らない。1 行のまま字間（spacing）・scale_x・位置で合わせる。
- 字の散った小さい行は、1 行に組み直して split し、狭い範囲（PAD=12、倍率 0.94〜1.06）で tune するとそろう（eqws）。
- **10/12 から split.py が分けた後に元の行と形を照合する**（IoU 0.85 未満なら分けずに残す。MIN_IOU で変更、FORCE=1 で強制）。8周目で、回転した行（SX_j・uFDK・wIwm）や英字の行（「Wint er」）が崩れたのを受けて。
- 回転した行は 1 行のまま、英字の行は `--words`、が安全。
- tune.py・tune_group.py は erase に "by":"layers" があると動かない（字が自分の形を追いかけて偽の点になる。Wd_G 45→49 は偽物）。色の erase に替えてから。
- tune_group と tune は行ごとに採点して良い方だけ残す（全行まとめて採点すると 1 行の失敗で全部戻る）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
