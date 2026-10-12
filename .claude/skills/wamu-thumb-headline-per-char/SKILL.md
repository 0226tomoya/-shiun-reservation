---
name: wamu-thumb-headline-per-char
description: サムネの大見出しを 1 文字ずつのレイヤーに分けて元に合わせる（再現の点が一番上がる方法）ときに使う。
---
# 1 文字ずつ合わせる（2 周目で 20 枚が平均 34→56 点）

1. `python3 editing/thumbs/helpers/chars.py ID y0 y1 x0 x1 thr k [white|black]` で元の文字の列ごとの外接矩形を出す（開処理 k で細い線を消す）。
2. 切れ目の数と字数を必ず数え合わせる。くっついた 2〜3 文字は列ごとの画素数の谷で切る。濁点・「ル・い・小」は 1 文字が 2 つに割れるので注意。**等間隔の推測は禁止**（1 文字隣にずれる事故が多かった）。
3. `python3 editing/thumbs/helpers/split.py ID i` で描いた位置のまま 1 文字ずつのレイヤーに分ける。
4. `python3 editing/thumbs/helpers/tune.py ID --apply --layers …`（位置・大きさ・横幅・傾き。`--fonts 'NotoSansJP:900,ZenOldMincho:900'` でフォントも比べる）か `snap_b16.py` で目標の矩形に合わせる。
5. 隣の文字が取った画素は的から除く（除かないと 2 文字が重なって 1 文字が消える）。比較画像で字が消えていないか必ず見る。
6. 縁取りのある文字は目標の矩形を縁の太さぶん内側にする。
- 英字の単語・日付は分けずに 1 行のまま。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
