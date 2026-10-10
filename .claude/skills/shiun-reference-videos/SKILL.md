---
name: shiun-reference-videos
description: わむうチャンネル（youtube.com/@wamu_164）の公開動画を、手元の編集データと照らし合わせて分析するときに使う。
---
# 公開動画と編集データの対応

- 公開動画と過去の編集データの対応（長さで確認）:
  - A18 本編（1631.4 秒）= 2avOFva-G7M（26 Summer 1st）
  - A19 本編（1570.5 秒）= KcpjBQPnDMc（26 Fall 2nd）
  - A23 は「本編」ではなく「靴なし」プロジェクト（1533.9 秒）= uMARBnCQD_Y（26 Fall 1st）
- 一覧は `yt-dlp --flat-playlist` で取れる。動画そのものはこの環境からは YouTube の bot 確認で取れない（2026-10-10 時点）。
  取るにはユーザーの cookies.txt（`--cookies`）か、動画ファイルの共有が要る。
- 公開動画が取れたら: 編集データを確認動画として描画し、同じ時刻のコマを並べて差を見る（テロップの位置・クロップ・色・切り替わりのフレーム）。

## YouTube から直接取る（2026-10-10 に動作確認）
- ユーザーの cookies.txt（シークレットウィンドウで書き出したもの）をスクラッチパッドの `yt/cookies.txt` に置く（権限 600。リポジトリには絶対に入れない）。
- 解読用のスクリプト: `pip install yt-dlp-ejs`（`--remote-components ejs:github` は証明書の都合で失敗する）。
- 一覧: `yt-dlp --cookies cookies.txt --js-runtimes node --flat-playlist --print "%(id)s\t%(duration)s\t%(title)s" https://www.youtube.com/@wamu_164/videos`（120 本）
- 取得: `yt-dlp --cookies cookies.txt --js-runtimes node -f 136 -o X.mp4 URL`（720p 映像のみ。`--download-sections` は ffmpeg が失敗するので全体を取ってから切る）
- 止められたら（bot 確認・429）cookies を取り直してもらう。
