---
name: shiun-romaji-leftover-check
description: テロップ（字幕・強調・手書き風）に日本語入力の打ち残しの半角英字（「文字化け」「テロップバグ」と呼ばれるもの）が無いか確かめるときに使う。1 年で 30 か所以上・14 本で指摘された一番多いミス。
---
# ローマ字の打ち残し

- 例: 「履きやすいし、s」「k若干キツい」「テーパードn効いた」「使用すr」「hシューズシリーズを」「s」だけの字幕、強調テロップ「おn」「r」「t」、「…ないd」「好みではないd」。
- 検査: `python3 editing/tools/audit_telop_text.py X.fcpxml`（build_all.sh に組み込み済み。1 件でもあれば止まる）。
- 単位（cm・kg・mm）と大文字のサイズ（S・M・XS）は対象外。
- 書き出した動画でも字幕の最初と最後を目で見る（強調テロップの中央の 1 文字も）。
出典: `editing/knowledge/編集ルール集_わむうsns_1年分.md`（原文は `editing/knowledge/slack_wamu_sns/`）。
