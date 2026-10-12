---
name: wamu-thumb-headline-kana-scaling
description: サムネの見出しで、かな・助詞を小さくして漢字・数字を大きく見せる（わむうのほぼ全サムネ共通）ときに使う。
---
# かなを小さく（全型共通）

- 助詞・送り仮名・小さい仮名（の・に・が・は・を・で・と・っ・ャ・する・でした・かった・選）を**漢字の 0.6〜0.8 倍**にして**下に寄せる**。
- 名詞は大きく、数字（3・7・10・2026・165cm）はさらに大きく。
- かなはプロポーショナル詰め: レイヤーに `"palt": true`。
- `!!` は「‼」1 文字で詰める。
- 書き方: 1 行のまま `runs` に `size_em`（例 `{"text":"の","size_em":0.7}`）、または 1 文字ずつのレイヤー（`wamu-thumb-headline-per-char`。こちらの方が点が上がる）。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
