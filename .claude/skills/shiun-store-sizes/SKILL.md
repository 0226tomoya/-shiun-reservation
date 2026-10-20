---
name: shiun-store-sizes
description: shiun ONLINE STORE（shiun-store.com）の商品のサイズ表（着丈・身幅・股上・股下など）・価格・推奨サイズ・着用モデルを調べる、動画やテロップに寸法を入れる、サイズ表を最新にするときに使う。
---
# shiun ONLINE STORE のサイズ表

- **一覧：** `editing/knowledge/shiun_ストアのサイズ表.md`（分類ごとの表）と `editing/knowledge/store_sizes.json`（道具から読む形）。2026-10-20 時点で 37 商品（OUTER 6・SHIRT 5・TOPS 10・BOTTOMS 11・SHOES 4・BELT 1）。
- **取り直す：** `python3 editing/tools/store_sizes.py 作業フォルダ 1 420`（1 秒おきに商品ページを取る。商品 ID は 276〜379 に出ていて、抜けている番号は 404 = 消えた商品）→ `python3 editing/tools/store_sizes.py 作業フォルダ --md editing/knowledge/shiun_ストアのサイズ表.md` → `store_sizes.json` を knowledge にコピー。新作が出たら最後の ID を広げる。
- **ページの作り：** EC-CUBE 系。商品名は `<h1 class="fontL">`、価格は `#detail_price`（税込）、サイズ表は `div.size_table` の `ul`（1 本目が項目名、2 本目からサイズごと）、推奨サイズは「推奨サイズ」の段落。分類は一覧ページ（`list.php?category_id=`）から。

## 読むときの決まり
- **ボトムスのウエスト：** ストアの表のまま（周囲の長さ）。イージーパンツはゴムの伸びの幅（「72 - 80cm」）。平置きの幅とは違う。
- **シャツの着丈：** 前後に分けて書くものがある（着丈(前)・着丈(後)、または前身頃・後ろ身頃）。着丈と言うときは後ろ。
- **タンクトップ：** 着丈ではなく総丈。
- **ラグラン袖：** 肩幅・袖丈の代わりに裄丈（首の後ろの中心から袖口まで）。
- **靴：** 寸法ではなく、サイズごとの足の大きさの目安（37 = 23.5〜24.5cm、39 = 24.5〜25.5、41 = 25.5〜26.5、43 = 26.5〜27.5）。中敷きの高さは商品名の「(+6cm)」。
- **推奨サイズ：** 24 商品が同じ書き方（XS: 〜160cm / S: 161〜169cm / M: 170cm〜）。13 商品（靴を含む）は書かれていない。
- **着用モデル：** つかさ 158cm XS、わむう 164cm S、モデル 167cm M か S、たき 170cm M、すけ 171cm M、MATSU 160cm XS、小林 176cm M。名前の表記がばらつく（「わむう」と「わむう身長」など）。
- 価格・商品名をテロップに入れるときは `shiun-price-name-check` で照らし合わせる。
