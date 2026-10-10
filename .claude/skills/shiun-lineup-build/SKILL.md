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
