---
name: shiun-overrides
description: ユーザーから届いた修正（時刻つきの指示）を編集データに入れるときに使う。
---
# ユーザーの修正を入れる

- 修正は `editing/plans/A24_plan.json` の `overrides` に書き、`apply_overrides.py` で当てる（clear / remove / move / retime / videos / stills / pairs / screens …）。
- 時刻は「その修正を書いたときのタイムライン」（`base_v1`）の時刻で書く。前の工程が変わっても素材の時刻を通して写される。
- 修正の受け取り: 「以上」まで受け取ってからまとめて直す。音声入力の言い間違い（例「価格」→「画角」、「ECより」→「EC寄り」）は文脈で読み、
  解釈は `editing/plans/A24_fixes_v23.md` のように 1 件ずつ書き残す。わからないものは仮の解釈で入れて、渡すときに確認する。
- 素材の名前が変わったとき: Dropbox の一覧を取り直し、フォルダとファイルサイズで旧名と新名を 1 対 1 に対応させて `rename_map` にする
  （番号だけで合わせない。V ネックチャコールは順番も変わっていた）。
