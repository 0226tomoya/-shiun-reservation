# 服の寸法のメジャー線アニメーション（measure_kit）

2026-10-20 のデニムの動画（`editing/output/denim_measure/デニム股上股下_メジャー_v3_効果音のみ.mp4`）の見た目・音を、どの服でも作れるようにしたもの。

## 手順（4 つのコマンド）
```
cd 作業フォルダ
python3 editing/tools/measure/transcribe_words.py 素材.mp4 words.json            # 文字起こし（単語と時刻）
python3 editing/tools/measure/measure_points.py 素材.mp4 TOPS points.json --check points.png --ignore '[[0,0,600,150]]'
#   → points.png を必ず見る。橙の「要確認」の点と、ずれている点は points.json を手で直す
python3 editing/tools/measure/measure_kit.py spec.json --still 10 still.png       # 最後の状態を 1 枚で確かめる
python3 editing/tools/measure/measure_kit.py spec.json                            # 書き出し（元の声はミュート、効果音だけ）
```
- `--ignore` は見出しなど、服でない物の矩形（x0, y0, x1, y1）。左上の見出しは必ず入れる。
- 服の種類: `TOPS`（カットソー・ニット）/ `OUTER` / `SHIRT` は同じ点、`BOTTOMS`（デニム・スラックス）。`SHOES`・`ACCESSORY` は点を手で置く。

## spec.json
```json
{"video": "素材.mp4", "out": "完成.mp4", "mute": true,
 "preset": "TOPS", "use": ["着丈", "肩幅", "身幅", "袖丈"],
 "points": { … points.json の中身 … },
 "words": "words.json",
 "store": {"product_id": 379, "size": "S"},
 "items": [{"label": "身幅", "say": "身幅", "line_at": 3.5, "num_at": 4.0, "value": "52"}]}
```
- `use`: 型の中から出す寸法（話している物だけ）。
- 時刻: `words` があれば、見出しの言葉を言った時刻で線を伸ばし、次の数字を言った時刻で数字を打つ。言い方が違うときは `say`（例 `"say": "みはば"`）。手で入れるときは `line_at` / `num_at`（秒）。
- 数字: 話した数字 → 無ければ `store`（`editing/knowledge/store_sizes.json` の商品 ID とサイズ）→ `value` で上書き。
- 型の中身は `presets.json`。寸法ごとに上書きできる: `offset`（線を服から離す px）、`dy`（横線の高さをずらす）、`x`（縦線を left / right）、`label_pos`（left / right）、`label_at`（数字の箱の左上 [x, y]）、`color`（ink / white。無ければ下地の明るさで自動）。
- 点線: `guides`（例: 股の高さ → 股上の線まで）。

## 見た目と音（変えない）
- 墨 (34,34,34)。黒い服の上の線は自動で白。書体は Noto Sans JP（見出し 500・30、数字 700・76、cm 500・34）。
- 線は 0.55 秒で伸びる。目盛りはその寸法の 5cm ごと（10cm ごとに長く）。数字は 1 字ずつ打ち込み、カーソルと入力欄の下線。
- 音は効果音だけ: キー入力と線のシュッ。確定音（ピロン）は入れない。元の声はミュート。
- 数字の箱は重なったら自動で下へずらす。

## 試した例（examples/）
- `denim_check.png` … デニムの動画の点（自動）。股は手で測った位置と 12px 差。
- `tee_points.png` / `tee_kit.mp4` … 黒のロンT（ストアの写真を紙の背景に置いた試しの画）。袖が胴に付いて下がる形は脇・裾が見えないので「要確認」になり、手で直した。
