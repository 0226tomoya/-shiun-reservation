---
name: wamu-thumb-new-from-scratch
description: わむうの新しい動画のサムネを一から作るときに使う（過去の型に当てはめて作る手順）。
---
# 新しいサムネを作る手順

1. 回の種類から型を選ぶ（購入品・ランキング→煽り型、コーデ紹介→大人型、shiun→告知型）。
2. 言葉を決める（`wamu-thumb-wording`）: 「低身長」＋断定 1 語＋数字。2 行なら上が前置き、下が結論。
3. 写真は「盛れている」スタジオ・LOOK 写真（Slack の決まり）。顔は文字で隠さない。
4. 似た型の `editing/thumbs/specs/ID.json`（点の高いもの）をコピーして、文字・ロゴ・色だけ差し替える。
5. `render.py` で描く（`--orig` に新しい写真を渡す）。2〜3 案作る。
6. `wamu-thumb-final-check` で確認。
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
