# round7_mid_0（round5_mid_0 の 103 枚・7 周目 B チーム）

前 = 今回の作業を始めた時の点（素材掃除の回で点が動いた枚はその後の点）、後 = 最後に採点し直した点。退避: スクラッチパッドの r7b_bak/（spec）・r7b/asset_bak/（直す前の素材）。

| 行 | ID | 前 | 後 | 何を直したか |
|---|---|---|---|---|
| 148 | 4rbN_Ts9ZI4 | 63.0 | 63.9 | tune 1 周 |
| 301 | X3ZNBjN9uIw | 60.8 | 62.4 | 見出し・小見出しを split→tune 2 周（字の抜けなし） |
| 12 | 23ZX52AWsic | 69.9 | 70.9 | 2026年・縦書き「低身長のカリスマが解説」を split→tune 2 周。2 枚組ロゴ uniqlo_pair_red_large（灰色の隙間ごと）をこの回から 1 枚ずつ切り直し（uniqlo_kata_red_23zx / uniqlo_red_23zx）。（暗い字）2026 を tune（+0.3） |
| 404 | zbv_Kh20SZ4 | 75.4 | 75.4 | 変更なし（split・tune どちらも上がらず） |
| 211 | RnzKfB4-Px4 | 61.1 | 61.3 | 自動 tune は上がらず。ロゴ uniqlo_red_rnzk（右上に人物の頭）を切り直し、頭は透過＋front。（暗い字）縦書き「低身長のカリスマ」を split→tune（+0.3） |
| 119 | DA4_EPYV-WA | 64.7 | 63.4 | 英字行・手書き行を split→tune。2 枚組ロゴ uniqlo_double_red_small→1 枚ずつ、jwanderson_black_text（紙袋の写真ごと）→黒い字の形だけ透過で切り直し、erase を full→黒の色指定（full だと紙袋が埋め跡になり -5） |
| 128 | 3l9WS2tOwRM | 60.7 | 62.0 | 上の小見出し 4 つを split→tune。崩れた「ワイドパンツ」（パ・ン・ツが散った）と縦の「大丈夫!!」を ext.py の矩形に box.py で戻し、大丈夫!! は細いペン字（KleeOne 600・縁 1px）に |
| 57 | w6XyOjl97X0 | 69.5 | 70.1 | tune 2 周（split 済み） |
| 252 | 7IEhiCe5Vp8 | 66.0 | 68.8 | 見出しを split→tune（字の抜けなし）。（暗い字）黒い MUJI・Labo を tune（+1.0） |
| 397 | ZXl6tZmAlPo | 66.7 | 66.7 | 変更なし（split・tune どちらも上がらず） |
| 284 | VtzhhyzCxC4 | 61.2 | 72.2 | 見出し「OUR LEGACY」「デビューしました」を split→tune 2 周（+11）。上の小さい英字行は 1 字ずつだと字が散った（/OU RLEGACY / Carsk）→ 語ごとの 5 レイヤー（COMOLI・/・OUR LEGACY・/・Clarks）にして列の矩形へ box.py（-0.7 だが字の並びが正しい方を採用） |
| 313 | 6bSBovUuz2w | 75.7 | 75.7 | tune 2 周。shiun ロゴ（写真の背景ごと）→ 白い字の形だけ透過で切り直し。（追記）shiun ロゴの erase を full→白の色指定（+1.1） |
| 184 | vkvVfB4f5IE | 62.2 | 62.5 | tune 1 周 |
| 64 | Ru70Z4wvHeo | 57.3 | 58.8 | tune 1 周 |
| 109 | xUjMZH_p5ig | 57.1 | 57.1 | 変更なし（split・tune どちらも上がらず） |
| 420 | ysm7SeUS49I | 77.3 | 77.8 | Men's Fashion を split→tune（回転した手書きは分けない） |
| 169 | HKsCkphbwds | 65.1 | 65.4 | tune 1 周 |
| 219 | 0J_USL03RFE | 56.7 | 57.0 | （暗い字）:C を tune（+0.4） |
| 187 | Wd8YGiOSV08 | 59.6 | 59.8 | tune 1 周 |
| 440 | 21ZkIjyYszw | 57.2 | 57.2 | 変更なし（split・tune どちらも上がらず） |
| 178 | bP9zvvXtYy4 | 68.0 | 71.0 | 小見出し・英字行・BEST を split→tune 2 周（+6.1）。UNIQLO:C（写真の背景ごと）→ 黒い箱と「:C」の字の形だけに分けて切り直し |
| 337 | dlI6Wq1yHj4 | 58.2 | 60.7 | 「プチプラ肌着8種」「徹底比較‼」「神インナー決定‼」を split→tune。tune で「8」が小さく浮き「徹底 比較」の間が空いた → 黄色の列の矩形（segs.py / ext.py）13 字に box.py |
| 22 | FTPKbFQy-GI | 54.8 | 55.1 | tune 1 周 |
| 474 | aR2OwS2WlPw | 66.5 | 67.0 | tune 1 周 |
| 305 | 4U8Axcr1SNQ | 56.6 | 58.8 | 縦の大見出し・shiun を split→tune。右下の小さい英字 2 行（24Fall Collection・日付）は 1 字ずつ tune で散った → 元の 1 行レイヤーに戻して元の矩形へ box.py（-0.9 だが読める方を採用） |
| 455 | gx1ash3II2g | 60.3 | 60.1 | 自動 tune は上がらず（価格の行は分けない）。ロゴ gu_blue_square_gx1a（左に人物の髪）を切り直し、髪は透過＋front。（暗い字）tune（+0.1） |
| 98 | v5Coaw67z-w | 54.7 | 56.8 | shiun・LOOK・Vlog・小見出しを split→tune 2 周。縮んだ「L」を列の矩形へ box.py |
| 388 | Cl-J5v94lBo | 70.0 | 74.5 | 見出し・英字行を split→tune 2 周（+6.7）。adidas ロゴ（床の写真ごと）→ 白い字の形だけで切り直し、erase を full→白の色指定（full のままだと -6.6、色指定で -2.2 まで戻る） |
| 123 | Jm-d2-uvfSY | 57.6 | 57.9 | tune 2 周 |
| 461 | EW7VcvbKWTQ | 70.3 | 71.7 | tune 2 周 |
| 354 | iWTlMp5PUbk | 58.5 | 58.5 | 変更なし（split・tune どちらも上がらず） |
| 410 | oZtYOlehxus | 59.2 | 60.4 | UNIQLO U・TOP10 を split→tune 2 周。（暗い字）TOP10 などを tune（+0.7） |
| 201 | yepjqOuHxx8 | 55.8 | 57.6 | 見出しを split→tune。UNIQLO|U ロゴに残っていた黒髪を手で多角形を指定して透過＋front。（暗い字）:C を tune（+0.3） |
| 41 | YEYOvWXjZAs | 71.3 | 78.6 | tune 1 周（+6.2）。2 枚組ロゴ uniqlo_double（灰色の隙間ごと）→ 1 枚ずつ切り直し（uniqlo_kata_red_yeyo / uniqlo_red_yeyo） |
| 204 | AbV5nwMbmWk | 64.5 | 66.0 | 「30」を split→tune 2 周（+3.6）。上のブランド名 5 つ（壁の写真ごと）→ 字の形だけ透過で切り直し、erase を full→字の色指定（-2.1。違反のない版を採用） |
| 136 | _Gnn2T7hm3Q | 68.0 | 67.4 | tune 2 周（+7.1）。2 枚組ロゴ（白い背景ごと）→ 1 枚ずつ、UNIQLO:C（シャツの写真ごと）→ 黒い箱と「:C」の字だけに切り直し。（追記）ロゴを切り直すと元の白い光彩（ぼかし）が消えて -5 → ロゴの後ろに radial-gradient の白い rect を 2 つ描いて戻した（67.4） |
| 398 | 7HZodpesIHc | 61.3 | 60.4 | 英字・見出しを split→tune 2 周。shiun ロゴ（写真の背景ごと）→ 白い字の形だけで切り直し、erase を白の色指定に（+0.8）。白い札の中の「低身長男性」が小さく左下にずれていた → 札いっぱいの矩形に box.py（-0.6 だが元の並びに一致） |
| 29 | u-yFzGO73ak | 58.9 | 62.1 | 165cm・見出しを split→tune（+3.2） |
| 44 | IZF_39cj9wE | 53.8 | 53.8 | 変更なし |
| 70 | 3W2f9CWzZ50 | 60.4 | 70.5 | 字間の広い 2 行・英字行を split→tune 2 周（+10.9）。縮んだ COMOLI の I・L、LIDИM の L・I だけ列の矩形へ戻した（全 23 字を矩形に合わせると細い Jost が太って -4.4） |
| 464 | qdjW3YFhXuU | 54.0 | 54.5 | 変更なし（split・tune どちらも上がらず）。（暗い字）黒い小見出しを tune 2 周（+0.5） |
| 322 | zIkC7ypKtck | 58.9 | 58.7 | 自動 tune は上がらず。ロゴ muji_maroon_whiteborder_zikc（右に人物の髪）を切り直し、髪は透過＋front |
| 273 | rqX9Av6pxLQ | 53.3 | 55.7 | 上の小見出しを split→tune 2 周。崩れた「大人・」（大が縮み・が人の右上へ飛んだ）を目で読んだ矩形に box.py |
| 365 | 1s7v8QUvY_4 | 58.7 | 57.8 | 「＼低身長男性必見!!／」を split→tune すると 長 と 男 の間が空き 性・見 が下がった（白い光彩が的に入るため）→ 目で読んだ矩形に box.py（tune 版の 61.0 より低い 57.8 だが字の並びが元に一致。狭い tune をかけ直すとまた崩れた） |
| 104 | YgrNu0ttJRs | 66.4 | 67.0 | 見出しを split→tune。「164cm/チビ」を 1 行に組み直して split→狭い tune（PAD 12・倍率 0.94〜1.06） |
| 467 | x1MIToUS3d4 | 65.9 | 71.1 | 「※価格バグってます」を split→tune 2 周（+5.2。字の抜けなし） |
| 314 | GU2ON4koLmk | 55.1 | 57.2 | GU 2024AW を split→tune。tune で前回と同じく「いいかも…!?」の か・も がずれた → その 7 字だけ前回目で合わせた位置に戻した |
| 376 | qN_3qy29EjE | 53.1 | 55.0 | 変更なし（tune は上がらず）。（暗い字）下段の濃灰の字を tune（+1.9） |
| 72 | Jhdi-5NYvfw | 51.7 | 53.2 | 英字 2 行を split→tune（+1.5。字の抜けなし） |
| 417 | lH-oU8P37mE | 79.1 | 79.7 | 変更なし。（暗い字）黒い字 14 字を tune 2 周（+0.6） |
| 318 | hqZzwhz-hfI | 56.3 | 56.7 | tune 2 周。ロゴ gu_blue_shadow_hqzz（右に人物の髪）を切り直し、髪は透過＋front。（暗い字）黒い字を tune 2 周（+0.5） |
| 411 | LISxBpIilxo | 50.8 | 50.8 | 変更なし。by:layers の「5選」は石の背景に灰色の金属調グラデで色の erase に替えられない（そのまま残した） |
| 361 | 8MPWE-IwQ6g | 56.5 | 57.2 | BEST5・見出しを split→tune。ロゴ uniqlo_red_8mpw（下に人物の髪）を切り直し、髪は透過＋front |
| 359 | 5vxD_5sE4Kc | 67.9 | 74.8 | XL・＼160cm代必見!!／・UNIQLO を split→tune 2 周（+6.9） |
| 76 | 6BGmuxND7zI | 52.7 | 53.3 | tune 1 周 |
| 419 | KrppDXMBfWw | 71.4 | 72.5 | tune 2 周 |
| 7 | gvgCuPXyOHc | 55.7 | 55.7 | 変更なし |
| 412 | P-shLDz0IZ4 | 64.8 | 66.3 | tune 2 周。ロゴ gu_blue_square_pshl（右に人物の頭）を切り直し、頭は透過＋front |
| 339 | OvZsUCoeZUQ | 56.8 | 59.3 | 小見出し（無印良品・2024秋冬・@展示会）を split→tune 2 周。（暗い字）黒い字を tune 2 周（+1.8） |
| 26 | GjAVle8LFls | 49.7 | 53.7 | 変更なし（split・tune どちらも上がらず）。（暗い字）「5.5cmUP」・小さい 2 行を split→tune 2 周（+4.2）。小数点が上に飛んだのを元の位置へ box.py |
| 212 | RLhgOtxcP6o | 50.3 | 50.3 | 変更なし |
| 444 | JYzRNtbISbw | 50.5 | 64.4 | erase の "by":"layers" を外して白の色指定だけに（50.5→50.7）→ 1 字ずつの見出しを tune 2 周（+13.7） |
| 167 | aFgc4pL0_hU | 61.9 | 63.9 | tune 2 周 |
| 25 | fayACVB2oNw | 52.4 | 51.7 | tune 2 周 |
| 445 | 6BbQg9b8k6g | 53.5 | 57.3 | tune 2 周 |
| 385 | NRrVJZNN9YA | 59.7 | 60.6 | （暗い字）定番・アイテム を split→tune（+1.0） |
| 38 | oywMby99ZZU | 48.2 | 48.4 | tune 1 周 |
| 451 | Fi_ZgjtGR9I | 48.7 | 51.7 | erase の "by":"layers" を外して色指定に（48.7→48.6）→ tune 2 周。（暗い字）黒い「ユニクロ冬の定番!!」を tune（+0.9） |
| 393 | aqEPKGbKedk | 51.4 | 55.3 | tune 1 周（+3.9） |
| 271 | gthvDlV0aHg | 47.9 | 47.8 | 変更なし。（暗い字）黒字＋白縁の 2 行を tune 2 周（+1.8）したが「え」が大きく浮き る・か が詰まった → え・る・か を目で読んだ矩形に box.py（47.8。字の並びが元に一致する方を採用） |
| 139 | nESPvxlUpKw | 44.4 | 45.4 | tune 1 周。ロゴ uniqlo_kata_red_nesp（左に顔の肌が残っていた）を手で多角形を指定して切り直し、顔は透過＋front |
| 436 | 24CweW03ryU | 65.8 | 66.3 | tune 1 周（+0.5） |
| 107 | LvtnFO8VfY0 | 48.5 | 48.9 | tune 1 周 |
| 358 | CoMYT3XMjkQ | 48.1 | 53.4 | 変更なし（価格の行は分けない）。（暗い字）赤い価格「¥5,499」などを 1 行のまま tune 2 周（+5.3） |
| 389 | BNXnpGEvhLM | 49.8 | 51.3 | tune 2 周（+1.5） |
| 356 | tZ4ztccxc_0 | 54.6 | 55.2 | 番号 07・01〜06 を split→tune_group→狭い字ごと tune（新しい道具。+0.6） |
| 114 | gz1BzsJvEIQ | 49.2 | 50.0 | tune 2 周 |
| 9 | Y-FVtzsvxN8 | 46.7 | 47.1 | tune 2 周 |
| 181 | rc2YpElqGPs | 49.9 | 55.9 | LEMAIRE を tune 2 周（+6.0） |
| 405 | my19nMrHhkY | 79.9 | 81.6 | tune 2 周（+1.2）。前回から「新 作」の間が空いていた（作が MUJI ロゴの full の範囲に引かれる）→ 作を目で読んだ矩形に box.py（+0.5） |
| 210 | 59OuL2ImSus | 47.8 | 64.6 | 30代・男性・＼今すぐ始めろ‼／・垢抜ける・13・のこと を split→tune_group→狭い字ごと tune（新しい道具。+4.5）。（暗い字）濃灰の「30代 男性」などを tune 2 周（+12.3） |
| 237 | fELtFrdlAuY | 50.8 | 55.6 | shiun・YouTuber・縦書き「低身長」を split→tune_group→狭い tune（+4.8） |
| 363 | BIlTzg5GO9c | 51.2 | 52.8 | tune 2 周 |
| 403 | Uw2_iD5RGDA | 50.2 | 53.9 | tune 2 周（+2.2）。（暗い字）GU×UNDERCOVER を tune 2 周（+1.5） |
| 312 | GMvrCCz9IAw | 54.3 | 56.7 | 2 行目「ユニクロ秋の新作アウター」を split→tune_group→狭い tune（+2.4）。字が元より少し小さく間が空いたまま（tune_group を広い範囲でかけ直しても的の一致が上がらず変わらない） |
| 27 | QJfxhb2t-II | 45.6 | 46.9 | tune 2 周（+1.3） |
| 416 | bKt5SXwrL98 | 51.3 | 52.6 | ヤバすぎぃ!!・ボトムス を split→tune_group→狭い tune（+1.3） |
| 427 | -C-wHRhgEZs | 51.6 | 53.4 | tune 2 周。（暗い字）ええええええ!? などを tune 2 周（+0.9） |
| 406 | naaElZuH3Qc | 49.6 | 49.3 | 英字行を split→tune_group→狭い tune（+1.0）。前回と同じく「TOP3」の 3 が縮んで浮いた → 目で読んだ矩形へ box.py（-0.7 だが元の大きさ）。2 枚組ロゴ（人物の髪入り）→ 1 枚ずつ切り直し、髪は透過＋front |
| 434 | ypg_GVKZAB4 | 43.4 | 46.4 | tune 1 周。（暗い字）手書きの 4 行を split→tune（+4.6）したが「低身 長」の間が空き「モテ る香」が崩れた → その 2 行だけ元の 1 行に戻した（46.4）。tune_group での組み直しは「低」が大きくなり 47.3 で採らず |
| 188 | I0PTDNRQllc | 53.0 | 57.8 | tune 2 周（+4.8） |
| 349 | aZ3Qx4kx-E4 | 42.2 | 46.5 | erase の "by":"layers" 4 つを外して色指定だけに（42.2→41.6）→ tune（+3.5）。（暗い字）激・安・縦書き「買いです」・低身長男性必見!! を split→tune（+1.4） |
| 332 | dbH9XAfTHhc | 49.1 | 51.3 | 「UNIQLO秋冬パンツ」を split→tune_group→狭い tune（+2.2） |
| 71 | CFzF147E7vc | 46.9 | 50.1 | 見出し 4 語を split→tune_group→狭い tune（+3.2） |
| 286 | nfxbWQSVziQ | 49.8 | 70.0 | 「ドライバーズニット待ってました‼」「冬の新作トップス」「GU 2024 Autumn/Winter」を split→tune_group→狭い tune（+20.2） |
| 77 | CnJ53hGpeOE | 46.6 | 57.5 | 英字の縦の一覧・見出し・英字行を split→tune_group→狭い tune（+11.7）。筆記体「2026 Winter & Spring」は 1 字ずつだと字が散った → 元の 1 行に戻した（-0.8） |
| 328 | V6zuRH7FnSE | 44.0 | 51.6 | 見出し・小見出し・縦書き 3 行を split→tune_group→狭い tune（+6.5）。ロゴ gu_blue_v6zu（下に手）を切り直し、手は透過＋front。（暗い字）黒い字を tune 2 周（+1.5） |
| 421 | ONDAaT4CFak | 48.5 | 54.6 | 悩みの語・見出し・縦書き 5 行を split→tune_group→狭い tune（+5.8）。「低身長男性のファッションの悩み」は同色の縁 4px で ョ が黒い塊に潰れた → 縁 1.5px にして狭い tune（54.3→54.6、字が読める） |
| 428 | DI9lodmh6CA | 52.6 | 53.8 | ww などを split→tune_group→狭い tune（+1.2） |
| 62 | 2avOFva-G7M | 45.8 | 47.5 | tune 1 周。（暗い字）変化なし |
| 226 | L0qdsfyFxYY | 49.8 | 61.6 | 新作先行発売!!・UNIQLO U 2025SS・モテる春服 を split→tune_group→狭い tune（+6.1）。（暗い字）紙袋の上の回った 2 行「UNIQLO U / 2025SS」は暗い字の split→字ごと tune で字が散った（63.1）→ 元の 1 行に戻し、新しい split（回転のまま）→ tune_group --rots -3,0,3 で行ごとに合わせた（61.6。字の並びが元に一致） |
| 90 | kwi4UJOBexA | 43.8 | 54.9 | shiun・低身長・大人スタイル・英字 2 行を split→tune_group→狭い tune（+11.1） |
| 106 | nTphzhwEygY | 41.3 | 49.2 | shiun試着会・長い 1 行を split→tune_group→狭い tune（+7.9）。手書きの細い字で書体が違い、5cm 以降が少し左に寄る（元の 1 行に戻すと 41.3 に落ちるので分けた版を採用） |

**全 103 枚。平均 56.9 → 59.5（+2.6）。下がった枚は 9 枚（字の並びを元に戻した・ロゴ切り直し。違反のない／字が読める版を採用）。**

## 素材（ロゴ以外の切り抜き・人物入りロゴ）の直し
- 人物の頭・髪・顔・手が入っていたロゴをその回から切り直し、人物は透過＋front: uniqlo_red_rnzk、gu_blue_shadow_hqzz、uniqlo_red_8mpw、gu_blue_square_pshl、uniqlo_red_nrrv、uniqlo_red_square_ew7v、gu_blue_v6zu、muji_maroon_whiteborder_zikc、uniqlo_red_0jus、gu_blue_square_gx1a、uniqlou_black_yepj（黒髪は手で多角形を指定）、uniqlo_kata_red_nesp（顔の肌は手で多角形）。
- 2 枚組（間の背景・隙間ごと）→ 1 枚ずつ（helpers ではなく scratchpad の r7b/logo/pair.py）: DA4_・fayA・naaE・_Gnn・YEYO・23ZX。旧画像 5 枚は削除（uniqlo_pair_red_large は担当外の sbJf07Bkd94 が使うので残した）。
- 写真の背景ごとの字のロゴ → 字の形だけ透過（glyph）: shiun_white_6bsb・shiun_white_7hzo・jwanderson_black_text・adidas_white_clj5・ブランド名 5 つ（abv5）。UNIQLO:C（bp9z・gnn）は黒い箱と「:C」の字に分割。erase も full → 字の色指定に替えた。
- by:layers は新しく足していない。JYzR・Fi_Z・aZ3Q は by:layers を外して色指定に替えた（LISx の「5」は金属調グラデで替えられず据え置き）。

## 分かったこと（round7_mid_0）

### 効いたやり方
1. **まだ 1 行のまま残っていた見出し・英字の行を split → tune（2 周）がやはり一番効く**: nfxb +20.2、Vtzh +11.0、CnJ5 +10.9、3W2f +10.1、kwi4 +11.1、Cl-J +6.7、5vxD +6.9、bP9z +6.1。5 周目で 1 文字ずつにしたのは見出しだけで、小見出し・英字行・番号が 1 行のまま残っていた枚が多かった。
2. **新しい tune_group（split → tune_group → 狭い字ごと tune PAD=8・0.96〜1.04）は、字ごと tune より字が散らない**。後半 30 枚で使い、59Ou +4.5、nfxb +20.2、kwi4 +11.1、L0qd +6.1 と点も同じくらい上がり、崩れて手で戻した字は少なかった。特に **回転した行は「新しい split（回転のまま）→ tune_group --rots -3,0,3」**で、紙袋の上の傾いた「UNIQLO U / 2025SS」が字ごと tune では散ったのに、元とほぼ一致した（L0qd）。
3. **暗い字（黒・濃灰の字）も tune の対象にする**: 自動処理が暗い字を飛ばしていた 27 枚に 2 回目をかけて 59Ou +12.3、CoMY +5.3、GjAV +4.2、ypg +4.6、qN_3 +1.9（erase に暗い色が入っている枚だけ。入っていないと的が無い）。
4. **by:layers を外して色指定だけにすると、その直後は ±0.6 でも、後の tune で大きく上がる**: JYzR 50.7→64.4（+13.7）、aZ3Q +4.9、Fi_Z +3.1。
5. **ロゴを切り直すと元の白い光彩・ぼかし縁が消えて点が落ちる → 光彩を radial-gradient の rect で描く**（_Gnn 62.6→67.4）。写真の背景ごとの字のロゴを字の形だけにしたら、erase も full → 字の色指定に替えると落ち幅が小さい（Cl-J −6.6 → −2.2、DA4_ −5 → −1.3、6bSB は +1.1）。
6. tune 後は必ず拡大して見る。崩れた字は列の矩形（ext.py・自作 segs.py）に box.py で戻した: 3l9W「ワイドパンツ」、dlI6「8・徹底比較」、v5Co「L」、3W2f「I・L」、my19「作」、naaE「3」、GjAV の小数点、gthv「え」、ONDA「ョ」。**崩れる字が全体の数より少ないときは、その字だけ戻す方が全部の字を矩形に合わせるより点が高い**（3W2f: 全部 −4.4、I・L だけ +0）。

### 効かなかったやり方・注意
- **小さい英字の行（size 40 未満の日付・ブランド名の並び）を 1 文字ずつに split すると字が散る**（4U8A「24Fall Collection」、Vtzh「COMOLI / OUR LEGACY / Clarks」、CnJ5 の筆記体）。1 行または語ごとのレイヤーにして矩形に box.py の方が読める。自動処理は途中から size 40 未満・¥・カンマ入りを分けないようにした。
- **白い光彩・白縁の字（1s7v「＼低身長男性必見!!／」、ypg の手書き）は tune（字ごと・tune_group・狭い範囲どれも）で字の間が空く**。光彩の白も的に入るため。目で読んだ矩形への box.py か、元の 1 行のまま。
- 同色の縁 4px の黄色い行は小さい「ョ」が塊に潰れる（ONDA）→ 縁 1.5px にして狭い tune で読める字に戻る（点は ±0）。
- 5 周目に崩れて直した字（GU2O の「か・も」、my19 の「作」、naaE の「3」）は、今回の tune でもまた同じように崩れた。毎回の自動 tune から外す仕組みが要る。

## 足りない機能
- **レイヤーに「tune しない」印**（"lock": true など）。手で合わせた字（帯・札の中、光彩の字、過去に崩れた字）が次の周の自動 tune でまた崩れる。
- **ロゴ画像の周りの白い光彩（ぼかし縁）**を image レイヤーの設定で付ける機能（今は rect の radial-gradient で代用）。
- tune.py・tune_group の的から、白い光彩・白縁の色を外す指定（"fit_color" を tune でも使えるように）。
- split.py で小さい英字の行の字幅が CSS の字詰めと合わず散る → 語ごと（空白区切り）に分けるオプション。
- 金属調のグラデ（LISx の「5」）を色の erase で消す方法（今は by:layers しかない）。
