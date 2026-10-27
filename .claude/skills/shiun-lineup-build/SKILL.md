---
name: shiun-lineup-build
description: shiun ラインナップ動画（A24 など）の編集データを素材から最後まで作り直すときに使う。XML を手で直さず、必ずこの順で全工程を流す。
---
# ラインナップ動画を作り直す

1. `bash editing/tools/build_all.sh WORKDIR PINMIC.wav MEDIA_VID MODELS`
   - apply_cuts（丸ごとカット。`--mic` で端を声に合わせる）→ assemble_lineup → remap_transcript → auto_insert → insert_size_compare → apply_overrides → insert_trial_event（試着会。スキル shiun-trial-event-insert）→ 検証
   - WORKDIR の `A24_v1_old.fcpxml` は、文字起こしを作った時点の v1（git の ce7cd5d の `editing/output/A24_v1.fcpxml`、マルチカムの ID r339）。ID で照合するので、別の v1（10/06 の v1 時点の XML は ID r12）を使うと文字起こしが全行「消えた」になり、字幕と商品名ラベルがほとんど出ない。
   - MEDIA_VID は身長別の動画ごとの `proxy.mp4`・`h/`（8fps・1920 幅）・`motion.json`（analyze_motion.py）。MODELS は mediapipe の `pose_landmarker_full.task`・`face_landmarker.task`（mediapipe は Python 3.11 で入る）。
2. 直すのは XML ではなく作り方（tools・型・`editing/plans/A24_plan.json`）。直したら必ず 1 から流し直す。
3. 最後に必ず通すもの（0 件になるまで渡さない）:
   - `validate_fcpxml.py`（参照の誤り＝ FCP で読み込めないもの。build_all.sh は 1 件でもあれば止まる）
   - `audit_cuts.py`（自分が作った編集点の切り方）→ スキル shiun-cut-audit
   - `audit_inserts.py`（インサートの覆い方・字幕と発言）→ スキル shiun-insert-rules
   - `qa_timing.py`（フレームずれ・編集点とのずれ）
   - `fidelity_full.py`（テロップの値が過去データと同じか）→ スキル shiun-telop-template
4. 撮影素材（身長別の Y98xx・K99xx など）は `fix_asset_tc.py` で asset の頭を実物のタイムコードに合わせる（`plans/A24_size_tc.json`。新しい素材は Dropbox の個別リンクに ffprobe を当てて `tc`・`rate` を足す。頭 0 秒のままだと FCP で「メディアの範囲が異なる」と出て再接続できない）。そのあと `preflight_fcpxml.py` が × 0 であること。
5. 出力は `editing/output/A24_latest.fcpxml`。コミットのメッセージの最後に共同作者の行を付ける。

## Slack #わむう_sns 1 年分のラインナップの決まり（`editing/knowledge/編集ルール集_わむうsns_1年分.md` の 5 章）
- ED は 2 分割: 左にコーデスナップ 5〜6 枚、右に話している映像＋コレクション名・発売日時。延期などのお知らせは ED の冒頭。再販告知もインサートで。
- 試着会の感想など追加の素材は、その商品パートの最後に 20〜30 秒。
- カウントダウンは必ず入れる（確認用はフェードインなし）。
- 身長別インサートには推奨サイズ・価格（EC と照合）・靴のサイズ。わむうのサイズ別インサートも入れる。
- 渡す前に `shiun-export-check` を必ず通す（ローマ字の打ち残しは build_all.sh の `audit_telop_text.py`）。商品の確認は白石さん、サイズ表は中森さん。

## 後から共有された動画の素材（10/27）
- 粗編集に無い動画は plan.register_clips（path・frames・rate・w・h）で auto_insert が登録し、台帳（A24_insert_ledger.json）と動き判定（A24_insert_motion.json）にも足す。
- 頭 0 秒が正しい素材（FCP の書き出しで start 0s のもの）は `A24_size_tc.json` に tc なしで書く。`A24_media_info.json` は fix_asset_tc.py が毎回ここから作り直すので、直接書くと消える。
