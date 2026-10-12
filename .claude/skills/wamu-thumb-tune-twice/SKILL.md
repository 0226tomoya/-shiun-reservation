---
name: wamu-thumb-tune-twice
description: サムネ再現で tune.py をかける回数・かけた後の確認のしかたを決めるときに使う。
---
# tune は 2 回、その後に目で確かめる

- 1 文字ずつのレイヤーに分けた後、`helpers/tune.py` を 2 回かける（1 回目で大きくずれを直し、2 回目で縦位置が合う）。
- 帯・ロゴ・白い服の近くの文字は、tune が背景を文字と取り違えて崩すことがある。比較画像（th/out の compare）で確かめ、崩れた文字は tune 前の位置に戻して lock する。
- 点が上がっても見た目が崩れたら戻す（点を上げるためだけの変形はしない）。
- tune の前に書体（ファミリー・太さ・長体）を決めておく。書体が違うまま tune すると位置だけで合わせようとして崩れる。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
