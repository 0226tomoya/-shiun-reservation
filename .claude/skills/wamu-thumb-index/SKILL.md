---
name: wamu-thumb-index
description: わむうチャンネルの YouTube サムネを作る・再現する・直すときに最初に読む。サムネ関係のスキル（型・文字・色・ロゴ・部品・道具）の一覧と使う順番。
---
# わむうサムネのスキル一覧（過去 2 年 477 本を再現して作った）

1. 型を決める: `wamu-thumb-type-aori`（煽り・最多）/ `wamu-thumb-type-otona`（白枠の大人型）/ `wamu-thumb-type-shiun-announce`（自社の告知）/ `wamu-thumb-type-size-compare` / `wamu-thumb-type-lookbook` / `wamu-thumb-type-kyokasho` / `wamu-thumb-type-street-interview` / `wamu-thumb-type-tier` / `wamu-thumb-type-best-ranking` / `wamu-thumb-type-coord-split` / `wamu-thumb-type-shopper` / `wamu-thumb-type-back-giant-text`
2. 言葉: `wamu-thumb-wording` → `wamu-thumb-fuseji`（伏せ字）
3. 見出しの文字: `wamu-thumb-headline-kana-scaling` → `wamu-thumb-font-selection` → `wamu-thumb-numbers-latin`
4. 色: `wamu-thumb-color-white-shadow` / `wamu-thumb-color-yellow` / `wamu-thumb-color-gold-gradient` / `wamu-thumb-color-red-blue-gradient`
5. ロゴ: `wamu-thumb-logo-placement` → `wamu-thumb-logo-uniqlo` / `wamu-thumb-logo-gu-muji-others`
6. 部品: `wamu-thumb-handwritten-note` / `wamu-thumb-vertical-text` / `wamu-thumb-bouten` / `wamu-thumb-question-silhouette` / `wamu-thumb-arrows-lines-callouts` / `wamu-thumb-frame-band` / `wamu-thumb-text-behind-person`
7. 道具と手順: `wamu-thumb-renderer-spec` → `wamu-thumb-headline-per-char` → `wamu-thumb-measure-helpers` → `wamu-thumb-erase-tuning` → `wamu-thumb-scoring-loop`
8. 新しく作る: `wamu-thumb-new-from-scratch`、仕上げの確認: `wamu-thumb-final-check`、失敗集: `wamu-thumb-pitfalls`
詳細は `editing/knowledge/サムネの決まり_わむう2年分.md`、再現の仕様は `editing/thumbs/specs/ID.json`（点数は `editing/thumbs/summary.tsv`）。
