---
name: wamu-thumb-low-score-triage
description: 40 点未満など点の低いサムネ再現を、最初に何から直すか決めるときに使う。
---
# 低い点の枚の直し方の順番

1. **位置のずれを疑う**（書体違いより多い）: 1 文字ずつのレイヤーが 1 字隣にずれている・1 行のまま → `helpers/split.py` → `bash helpers/auto2.sh ID`（tune 2 周、上がった時だけ残す）。これだけで +10〜+30（6周目、42 枚 36.9→50.8）。
2. erase が `"by":"layers"` なら色の erase に替えてから split・tune（直後は下がるが、その後大きく上がる: 3bFs 36→60、sDJB 31→49）。
3. 手前の人物・紙袋は front（nczP 56→72）。front を足した後、その行だけ tune し直す。
4. tune で崩れた字は `helpers/ext.py` で外接矩形を取り直して `helpers/box.py` で合わせる（+5〜+7）。
5. 斜体の有無を確かめる（4iT1 italic で +6、g1k3 skew を外して +5）。
- 効かなかった: 縁の太さの調整、グラデの取り直し、字ごとの書体選び（書体が混ざる）。
- 直しきれない型: 白地の白字、黒縁の字の近くの黒い服、半透明の大きい数字、細い線だけの中抜き字、縦書きの複数行。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
