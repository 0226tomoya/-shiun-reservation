---
name: wamu-thumb-char-check
description: サムネ再現の tune・split の後に、細い字の縮み・字の順番の入れ替わり・重なりを見つけるときに使う。
---
# tune 後の字の確認（char_check）

- `python3 helpers/char_check.py [ID…]`（"grp" の付いた行が対象）。
- 細い字（1 i I l ! - ー ・ , .）の大きさが行の中央値から 15% 以上ずれている → tune で縮んだ・膨らんだ疑い。
- 縦書きで上→下、横書きで左→右の順番が逆 → split 後の入れ替わり（0cUM の例）。
- 隣の字と大きく重なっている → 片方が別の字の位置に吸われた。
- 見つかった字は、元の画素の連結成分から矩形を取って box.py で戻し、`"notune": true` で固定する。
- "!!" の 2 字は近いので「重なっている」と出やすい（目で確かめる）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
