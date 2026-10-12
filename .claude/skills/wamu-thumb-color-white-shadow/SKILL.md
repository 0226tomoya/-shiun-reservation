---
name: wamu-thumb-color-white-shadow
description: サムネの基本色「白文字＋黒のぼかし影」（全体の約 7 割）を作る・再現するときに使う。
---
# 白＋黒ぼかし影

- `"color":"#ffffff"`（純白より `#fcf5ee` のクリームのことも多い）＋ `"shadow":"0 0 8〜24px rgba(0,0,0,.3〜.75)"`。大きくぼかすほど元に近い（担当 02）。
- 縁取りはほぼ使わない。使うなら濃灰 3〜4px。
- 白い壁・白い服の上では白文字が沈むので、濃灰（#2c2c2c）か黒＋白の太縁 6px に切り替える。
- 影が元より濃い・広いと形の採点で損をする（見た目を崩さない範囲で元と同じ薄さに）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
