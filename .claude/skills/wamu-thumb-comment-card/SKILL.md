---
name: wamu-thumb-comment-card
description: サムネの視聴者コメント・Instagram コメント風のカード、ブランドの札（文字入りの白い札）を作る・再現するときに使う。
---
# コメントカード・ブランドの札

- カードは rect（白 #ffffff、radius 12〜20、薄い影）＋ text（黒、NotoSansJP 500〜700、小さめ）＋ アイコンの丸（rect radius 50%）。区切りは line。
- 中の文字も text で打ち直す（切り抜き禁止）。7Mrq は 85.8→75.8 に下がったが正しい。
- ブランドの札は札を rect、ロゴだけをその回から字の形で切り直して（背景透過）上に貼る。
- 複数枚並べるときは同じ大きさ・同じ間隔で、少しずつ傾ける（±3°）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
