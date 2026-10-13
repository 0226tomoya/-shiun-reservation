---
name: task-preview
description: 長い作業の進み具合を、ユーザーが開いたまま自動で最新になる「タスクプレビュー」（claude.ai の artifact）に出すときに使う。「作業の様子を表示して」「進捗を見せて」と言われたら使う。
---
# タスクプレビュー

- ページ: https://claude.ai/artifact/HQQTMCW7ai97WvLreNseKX （元のファイル `editing/task_preview/task_preview.html`。持ち主だけが開ける）
- データは artifact の db の `boards` コレクション。1 つの作業 = 1 ドキュメント（例 `boards/shiun-short`）。ページは更新日時の新しい順に最大 8 つを出し、上のボタンで切り替える。
- 書き方: ArtifactData の `set`（初回）／`update`（2 回目から、`if_version` に前回の version）。url は上のページ。中身:
```
{"project": "上の小見出し", "title": "作業の名前", "status_line": "今やっていることを 1 文",
 "updated_at": ミリ秒の時刻,
 "tasks": [{"name": "手順", "state": "done|doing|todo|blocked", "progress": 0〜100, "detail": "補足"}],
 "activity": [{"at": ミリ秒, "text": "何をしたか"}]}
```
- 全体の % は、各手順の progress の平均（done は 100）で、ページが計算する。手順ごとにバーが出る。
- ページは db を購読しているので、書いたらすぐ（開いたまま）変わる。「◯秒前に更新」が毎秒進む。30 分以上書かないと印が灰色になる。
- 中身はファイルの状態から作ると楽（例 `editing/task_preview/board_example.py`）。節目ごと（手順が進んだ・終わった・止まった）と、定期の呼び出しのたびに書く。
- 別の会話から使うときも、同じ url に書けば同じページに出る（ページを作り直さない）。
