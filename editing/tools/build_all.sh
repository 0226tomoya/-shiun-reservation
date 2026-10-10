#!/bin/bash
# A24 を素材から最後まで作り直す（毎回この順で。手で XML を直さない）
#   bash tools/build_all.sh WORKDIR PINMIC.wav MEDIA_VID MODELS
set -e
W=$1; MIC=$2; VID=$3; MODELS=$4
cd "$(dirname "$0")/.."
python3 -I tools/apply_cuts.py sources/A24_粗編集_素材入り.fcpxml plans/A24_plan.json sources/A24_粗編集_カット済み.fcpxml plans/A24_subject.json plans/A24_subject_cut.json --mic "$MIC"
cp output/A24_v1.fcpxml "$W/A24_v1_prev.fcpxml"
python3 -I tools/assemble_lineup.py sources/A24_粗編集_カット済み.fcpxml plans/A24_plan.json output/A24_v1.fcpxml
python3 -I tools/remap_transcript.py "$W/A24_v1_old.fcpxml" output/A24_v1.fcpxml plans/A24_transcript.json plans/A24_transcript_cut.json
python3 -I tools/auto_insert.py output/A24_v1.fcpxml plans/A24_plan.json "$W/b_a.fcpxml" | tail -1
python3 -I tools/insert_size_compare.py "$W/b_a.fcpxml" plans/A24_plan.json "$W/b_b.fcpxml" --media-vid "$VID" --models "$MODELS" | tail -1
python3 -I tools/apply_overrides.py "$W/b_b.fcpxml" plans/A24_plan.json "$W/b_c.fcpxml"
python3 -I tools/validate_fcpxml.py "$W/b_c.fcpxml" | tail -1
python3 -I tools/audit_cuts.py "$W/b_c.fcpxml" "$MIC" "$W/b_cuts.json"
python3 -I tools/audit_inserts.py "$W/b_c.fcpxml" plans/A24_transcript_cut.json --v1 output/A24_v1.fcpxml
python3 -I tools/audit_telop_text.py "$W/b_c.fcpxml" || { echo "テロップの文字に問題あり（ローマ字の打ち残しなど）"; exit 1; }
python3 -I tools/qa_timing.py "$W/b_c.fcpxml" 本編 | sed -n 2,8p
cp "$W/b_c.fcpxml" output/A24_latest.fcpxml
