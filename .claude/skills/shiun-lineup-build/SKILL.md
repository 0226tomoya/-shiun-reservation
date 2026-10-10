---
name: shiun-lineup-build
description: shiun ラインナップ動画（A24 など）の編集データを素材から最後まで作り直すときに使う。XML を手で直さず、必ずこの順で全工程を流す。
---
# ラインナップ動画を作り直す

1. `bash editing/tools/build_all.sh WORKDIR PINMIC.wav MEDIA_VID MODELS`
   - apply_cuts（丸ごとカット。`--mic` で端を声に合わせる）→ assemble_lineup → remap_transcript → auto_insert → insert_size_compare → apply_overrides → 検証
2. 直すのは XML ではなく作り方（tools・型・`editing/plans/A24_plan.json`）。直したら必ず 1 から流し直す。
3. 最後に必ず通すもの（0 件になるまで渡さない）:
   - `validate_fcpxml.py`（参照の誤り＝ FCP で読み込めないもの）
   - `audit_cuts.py`（自分が作った編集点の切り方）→ スキル shiun-cut-audit
   - `audit_inserts.py`（インサートの覆い方・字幕と発言）→ スキル shiun-insert-rules
   - `qa_timing.py`（フレームずれ・編集点とのずれ）
   - `fidelity_full.py`（テロップの値が過去データと同じか）→ スキル shiun-telop-template
4. 出力は `editing/output/A24_latest.fcpxml`。コミットのメッセージの最後に共同作者の行を付ける。

## Slack #わむう_sns 1 年分のラインナップの決まり（`editing/knowledge/編集ルール集_わむうsns_1年分.md` の 5 章）
- ED は 2 分割: 左にコーデスナップ 5〜6 枚、右に話している映像＋コレクション名・発売日時。延期などのお知らせは ED の冒頭。再販告知もインサートで。
- 試着会の感想など追加の素材は、その商品パートの最後に 20〜30 秒。
- カウントダウンは必ず入れる（確認用はフェードインなし）。
- 身長別インサートには推奨サイズ・価格（EC と照合）・靴のサイズ。わむうのサイズ別インサートも入れる。
- 渡す前に `shiun-export-check` を必ず通す（ローマ字の打ち残しは build_all.sh の `audit_telop_text.py`）。商品の確認は白石さん、サイズ表は中森さん。
