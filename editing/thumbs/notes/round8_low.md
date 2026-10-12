# round8_low（8 周目 D チーム）

対象: round8_low.tsv の 76 行から、別チーム作業中の 3bFsQGeS1MQ（round5_high_*）を除いた 75 枚。
「前」は今回の開始時に採点し直した点（tsv の点は 6・7 周目の直す前の点で、平均 42.7）。「後」は最後に全枚を採点し直した点。
退避: scratchpad/r8_bak/（ID.orig.json＝開始時、ID.best.json＝最終）。自動処理: scratchpad/r8/pipe.sh・prep.py（ログ r8/log/ID.log）。

自動処理（1 枚ずつ、各段で点が +0.05 以上上がったときだけ残す）:
1. split（1 行のままの層。英字の行は --words、価格・日付・記号入り・css_transform は分けない。途中から回転した行・英字の 1 字ずつも分けないように変えた）
2. grp の無い 1 字ずつの層を、同じ行で続くものにまとめて "grp": "P<先頭>" を付ける（regroup.py と同じ考え）
3. tune_group を行（grp）ごとに 1 行ずつ採点
4. 狭い字ごと tune（PAD=8 S0=0.96 S1=1.041 X0=0.96 X1=1.041）を行ごとに 1 組ずつ採点（暗い字も含む）
5. 影を外す（全層）
6. erase に by:layers がある枚は自動処理を飛ばす（Wd_G で偽の点が出たため）
その後、全枚の比較画像を見て、崩れた字は画素の列・地図から矩形を読んで box.py → 極狭い tune（PAD=5、0.97〜1.03）→ notune。

| 行 | ID | 前 | 後 | 何を直したか |
|---|---|---|---|---|
| 287 | H1Or3Hiz6Po | 62.7 | 63.4 | 自動: split 36:chars→狭い tune 2 組。手: pipeline 63.6 だが英字の行「24Winter 1st Collection」を 1 字ずつに split して「Wint er」「Coll ection」と空いた → 元の 1 行から語ごとに split → tune_group（S 0.96〜1.04）→ 極狭い tune PAD6（63.4）＋notune |
| 15 | sbJf07Bkd94 | 71.0 | 72.4 | 狭い tune 2 組 |
| 137 | azmvFulJets | 63.0 | 64.2 | split 2:words→tune_group 1 行→狭い tune 1 組→影外し |
| 227 | QkaUnq-Gz3k | 58.7 | 61.5 | 自動: split 1:chars→狭い tune 2 組→影外し。手: pipeline 61.7 だが手書き「これ知ってる?」の「っ」が「知」の下に隠れ行が右に詰まっていた → 連結成分の矩形 7 つに box.py して notune（-0.2、見た目優先） |
| 447 | 4iT1PFtsJZ8 | 46.2 | 46.2 | split 19:words,5:chars,3:chars,1:chars→split は戻した→どの段も上がらず |
| 229 | xj95BNOr2co | 70.2 | 71.4 | 狭い tune 2 組 |
| 268 | euYyoHSr3B8 | 40.2 | 56.7 | 自動: split 4:words,2:chars→tune_group 2 行→狭い tune 2 組→影外し。手: 白地の白字: pipeline の tune で 待望 が白壁へずれ英字が見出しへ移動(50.2) → 待望の を fit_color #fff tol12 PAD20 で tune、英字は元の 1 行に戻して notune |
| 266 | oI-5e5ORnf4 | 53.4 | 57.4 | 自動: split 19:chars→tune_group 1 行→狭い tune 2 組。手: pipeline 57.1、「ユニ クロ」の隙間（ユ・ニ が細すぎ）→ 金色の列の矩形に box.py＋notune（+0.3） |
| 321 | YF8HVK2JYE4 | 60.8 | 61.5 | 自動: 狭い tune 1 組。手: 「MEN'S  FASHION」の間が元より 30px 空いている（前の回から）→ 列の矩形へ box.py すると見た目は合うが 58.6（-2.9）、tune は空いた位置へ戻る。点が下がるので戻した（的＝白 tol20 が暗い服の上で欠ける） |
| 222 | tnH6etyNliw | 72.5 | 73.5 | 狭い tune 1 組→影外し |
| 200 | P-DHHqvTE_0 | 49.4 | 51.2 | 狭い tune 2 組 |
| 263 | MLnDE53vIns | 65.3 | 71.0 | 狭い tune 2 組→影外し |
| 105 | Erj8ujoPAIQ | 59.1 | 60.3 | split 8:words→split は戻した→狭い tune 2 組→影外し |
| 83 | m2rS50Ptjx4 | 46.1 | 48.0 | 自動: 狭い tune 2 組。手: pipeline 47.5、「を カ」の隙間とカ・ッ が小さい（前の回から）→ 画素の地図で 4 字の矩形を読み box.py＋notune（+0.5） |
| 423 | pljQuPDyDEk | 48.2 | 51.8 | split 9:words,1:chars→狭い tune 2 組 |
| 424 | fN4pcESsdpQ | 43.5 | 45.2 | 自動: split 14:chars,3:chars,2:chars→tune_group 2 行→影外し。手: pipeline 44.4（下の行 tune_group・影外し）→ 黒い手書き「チビは着るなww」8 字を fit_color #111111 tol35・PAD20・S 0.9〜1.2 で tune（+0.8）。同色縁 3px は -0.6。残り: 赤字の太い黒縁と斜めの黒いもやが背景に灰色の影として残る |
| 269 | qpCmOcw55kM | 67.5 | 72.5 | split 9:chars→狭い tune 2 組 |
| 191 | -Jfkot5UbDI | 46.6 | 46.8 | 狭い tune 2 組 |
| 198 | THpZuGk5aZw | 45.5 | 46.5 | split 1:chars,0:chars→狭い tune 3 組 |
| 125 | SSuub09qLtU | 62.2 | 64.3 | 狭い tune 2 組 |
| 306 | jRYVxxwXAgg | 44.4 | 46.1 | split 10:chars→狭い tune 2 組→影外し |
| 302 | nczPFDj6VqI | 71.6 | 74.6 | split 0:words→狭い tune 3 組 |
| 282 | obMTx7dd_II | 41.8 | 44.4 | split 1:chars,0:chars→tune_group 2 行→狭い tune 2 組 |
| 277 | mdOQKJqtBgU | 63.8 | 65.0 | 狭い tune 2 組 |
| 111 | Avz219ur5bM | 44.5 | 49.2 | tune_group 1 行→狭い tune 2 組→影外し |
| 55 | LzXG6WP5xmo | 40.0 | 41.4 | 自動: split 1:chars→どの段も上がらず。手: pipeline は split で -0.2（戻した）。細い手書きの 1 行を YuseiMagic→KleeOne 600 に替え 1 行のまま狭い tune（+1.4）。split→tune_group→字ごと tune は 47.0 まで上がるが「5.5」の点が消え字間が空くので採らず。元は細く字間の広い手書きで、的（白 tol8）がまばら → 点は短く縮めた形を好む |
| 283 | Y7oAJc1t4j4 | 50.1 | 52.3 | split 3:words,2:words,1:chars→tune_group 3 行→狭い tune 6 組 |
| 122 | O4T5bB3-G1c | 58.1 | 61.1 | 自動: split 12:chars,11:chars,1:words→tune_group 1 行→狭い tune 3 組→影外し。手: pipeline 60.7。右上の英字 4 語で「Winter1st」がくっついていた → 列の矩形へ box.py（59.8）→ skew -4.5→0（元は立体）→ 語ごとに狭い tune PAD6（61.1）＋notune |
| 91 | 27pgmTWaDw4 | 52.9 | 53.5 | split 1:words→split は戻した→狭い tune 3 組 |
| 267 | g1k37XP-dyo | 48.0 | 49.2 | split 22:chars→tune_group 2 行→狭い tune 3 組 |
| 19 | uMARBnCQD_Y | 42.6 | 44.5 | 自動: split 1:words→tune_group 1 行→狭い tune 4 組。手: pipeline 44.5。「着たい 」を」の 」 が右へ離れていた → 地図で矩形を読み box.py＋notune（同点）。灰色のシャツの上の白字は ext の矩形が服まで広がる |
| 308 | IRda-I0hpRM | 41.0 | 46.8 | 自動: split 8:chars,7:chars→tune_group 2 行→狭い tune 3 組。手: pipeline 44.6。下の行「するファッション」で「ァ」が大きく「ファ ッ」の間が空いていた → 画素の地図で 8 字の矩形を読み box.py＋notune（+2.2）。黄の「な・‼」を矩形に合わせると見た目は良いが -0.5、skew -8 は -1.4 で採らず |
| 462 | sDJBIgqaUKE | 49.0 | 49.4 | 狭い tune 3 組 |
| 395 | MZmTmXDVIXU | 34.1 | 37.1 | split 0:chars→tune_group 3 行→狭い tune 3 組 |
| 126 | NlEa5AILtZA | 37.1 | 37.2 | split 0:words→split は戻した→狭い tune 1 組 |
| 108 | 67DtJKx3BaU | 42.7 | 43.4 | split 1:words→split は戻した→狭い tune 2 組 |
| 99 | 5PpR1OfijTk | 36.0 | 36.3 | split 23:chars,22:chars,20:chars,18:chars,16:chars,15:chars,13:chars,12:chars,10:chars,9:chars,6:words,5:chars,4:chars,3:chars,2:chars,1:chars,0:chars→split は戻した→狭い tune 1 組 |
| 272 | wBcpEsv5_dg | 46.5 | 47.9 | 自動: split 0:words→tune_group 1 行→狭い tune 5 組。手: pipeline 48.1。「169c m」の m が離れていた → 画素の地図で c・m の矩形に box.py → 極狭い tune PAD5（47.9、-0.2 だが見た目優先）＋notune |
| 56 | bq14Ml3YPgc | 35.3 | 41.8 | 縦書き 5 層（6 周目は split.py が縦書き非対応で 1 層のまま）を新しい split で 1 字ずつ（縦書きのまま）→ tune_group 3 行→狭い tune 5 組（+6.5） |
| 92 | qiV5AIev7J4 | 29.2 | 30.8 | 自動: split 3:chars,2:chars,1:chars→狭い tune 4 組。手: pipeline 30.3（3 行を split→行ごと tune）。split 後の tune で「カ」が「ど」に重なり「カ ッ」の間が空いた → 列の矩形 8 つに box.py＋notune（+0.5）。残り: 半透明の筆記体「28」 |
| 453 | 2EnD6PALGYY | 26.3 | 28.3 | split 1:words→狭い tune 3 組 |
| - | XDRHeskRdFI | 41.2 | 43.6 | split 6:chars,5:chars,4:chars,3:chars,2:chars,1:chars→tune_group 1 行→狭い tune 4 組 |
| - | n5nr9CpNsQA | 44.0 | 46.8 | split 0:chars→tune_group 1 行→狭い tune 2 組→影外し |
| - | Wd_GdqzMBqY | 45.1 | 45.1 | 自動: split 21:chars→tune_group 4 行→狭い tune 5 組。手: erase が by:layers → pipeline の tune_group が的（＝自分の字の形）を追って見出しが二重・字が重なった（49.4 は偽の点）→ 元に戻した |
| - | RJvdDBb3fOQ | 46.4 | 48.6 | 自動: split 6:chars,5:chars,4:chars,3:chars→tune_group 1 行→狭い tune 4 組。手: pipeline 48.6 だが「お洒落さん」が tune で 3 割縮んでいた → 画素の地図で 5 字の矩形に box.py（48.0）→ 極狭い tune PAD5（48.6、同点で見た目が元どおり）＋notune |
| - | d7HPxyfP1xI | 47.2 | 50.9 | 自動: 狭い tune 2 組→影外し。手: pipeline 47.9。見出し「今欲しいアイテム」が 3 書体混ざり・欲 が小さく「欲 し」が離れていた → 全字 NotoSansJP 900・skew -8（元は斜体）にそろえ、画素の地図の 8 矩形へ box.py（48.5）→ 極狭い tune PAD5（50.9）＋notune |
| - | 9_McXtWepIU | 47.3 | 47.6 | split 13:chars→狭い tune 2 組 |
| - | hDq4-JyK6fg | 47.5 | 47.5 | split 7:words,6:chars,5:chars→split は戻した→どの段も上がらず |
| - | Dert0M5y8cM | 47.6 | 48.6 | split 21:words→狭い tune 3 組 |
| - | h7mFdNJ2WmY | 47.6 | 69.0 | 吹き出し内の 2 行（各 2 段）が 1 層のままだった → split（段ごとに grp L6・L6_1・L7・L7_1）→ tune_group 4 行で 47.6→62.9 → 狭い tune で 69.0。見た目も一致（+21.4、今回最大） |
| - | SX_jXvipj0Q | 47.7 | 47.5 | 自動: split 1:chars→tune_group 2 行。手: 右上の手書き「低身長デザイナーが徹底レビュー!!」は白字＋黒いにじみなのに #1a1a1a の黒字で描いていて、元の白字が背景に残り二重に見えた（色の読み違い）。さらに pipeline の split が回転した行の字を右へ 80px ずらした（split.py の回転＋box/fixed の行）→ 1 行に戻し、白字＋影・YuseiMagic・erase を白に替え矩形へ box.py＋notune。点は -0.2 だが二重の字が消えたので採った |
| - | KcpjBQPnDMc | 47.9 | 48.9 | 自動: split 1:words→狭い tune 4 組。手: pipeline 48.9。「シン プル」の隙間を列の矩形へ box.py すると 38.8（-10）: ル の右が白いシャツ（#fcfcfb tol16 の erase の範囲内）とつながって矩形が大きくなり、プ も ゜ が erase の範囲（y500〜）の外に出た → 戻した。白い服の隣の白字は列の矩形が取れない |
| - | k1ZZgrf3mdE | 48.4 | 48.4 | erase が by:layers のため自動処理を飛ばした |
| - | YyTh4oYDGZ0 | 48.5 | 52.0 | split 8:chars,7:chars→tune_group 2 行→狭い tune 2 組 |
| - | 3DDxA28X06s | 48.3 | 49.2 | 自動: split 4:chars,2:chars→tune_group 1 行→狭い tune 4 組→影外し。手: pipeline 49.3。上の黒字「安 いのに」で いのに が右へ 50px ずれ小さかった（集中線・髪と同じ黒で的が取れず、tune_group も動かない）→ 目で読んだ矩形へ box.py＋notune（-0.1、見た目優先） |
| - | N5vktmbfs8c | 49.0 | 50.2 | split 10:chars,8:chars→tune_group 3 行→狭い tune 3 組 |
| - | yW8RY0VbOHc | 49.3 | 51.8 | 自動: split 35:chars→tune_group 1 行→狭い tune 4 組。手: pipeline 50.8。左下の手書き「低身長のメンズ必見‼」で「身 長」が離れ・字が太かった → 列の矩形 10 個へ box.py → 手書きの中で書体を比べ ZenKurenaido（細い）に → 極狭い tune PAD5（51.8）＋notune。矢印は cv2 で描いたもの（切り抜きでない）を確認 |
| - | FVCTcwToQWo | 49.8 | 50.6 | 自動: split 2:chars→tune_group 2 行→狭い tune 3 組。手: pipeline 51.1 だが左上「おすすめスポットも紹介!!」は白字＋赤縁なのに赤字＋白縁＋赤縁で描いていた（色の読み違い）＋回転した行の split で 紹介 が崩れた → 1 行に戻し白＋赤縁 6px、矩形へ box.py→fit_color 白で tune（ROTS -4〜-2）＋notune。-0.5 だが字の色が正しくなった |
| - | uFDK5oSTQ5E | 49.9 | 51.6 | 自動: split 3:chars,2:chars,1:chars,0:chars→tune_group 1 行→狭い tune 7 組。手: pipeline 52.4 だが、回転＋斜体の右上 2 行を split が分けると「〇〇」が詰まり「!!」が 1 つに見えた → 2 行を元の 1 行に戻す。「〇〇が超重要!!」は濃灰の塗りと読んでいたが実際は白い細線の中抜き（中は背景）→ hollow＋白 2.5px・erase を白に替え矩形へ box.py→fit_color 白で tune（51.6）＋notune。点は -0.8 だが字の読み違いを直した |
| - | wIwmHcL_qkc | 50.0 | 51.0 | 自動: split 10:chars→狭い tune 3 組。手: 右上の手書き「低身長男性必見!!」は白い細字なのに黒字＋白縁で描いていた（色の読み違い）＋pipeline の split が回転した行で字を崩した → 1 行に戻し、白・縁なし・ZenKurenaido・erase を白に、box.py→fit_color 白で tune（51.0）＋notune |
| - | r47UvWE1eN0 | 50.2 | 51.6 | 自動: split 1:chars→tune_group 1 行→狭い tune 3 組。手: pipeline 51.7 だが英字の見出し「UNIQLO U 24SS」（size 65・900）を 1 字ずつに split して字間が空き S が縮んだ → 元の 1 行に戻し狭い tune（51.6）＋notune。元は縦長の太い斜体ゴシックで Montserrat は横に広い。NotoSansJP 900・Oswald・BarlowCondensed＋skew を試したが 48.9〜51.3 で採らず |
| - | HZ0L2ig3Uls | 50.7 | 53.7 | 自動: tune_group 1 行→狭い tune 2 組。手: pipeline 51.5。下の行「カッコよく着こなす方法」で コ・く・こ・な が半分の大きさに縮んでいた（前の回から。tune の旧い偏り）→ 列の矩形 4 つへ box.py（52.8）→ 極狭い tune PAD5（53.7）＋notune。方法 も矩形に合わせると -2.5 で戻した |
| - | bsheKOGDsUM | 50.7 | 50.7 | erase が by:layers のため自動処理を飛ばした |
| - | UVCaGbnFNDA | 51.2 | 54.1 | split 16:words→tune_group 1 行→狭い tune 2 組 |
| - | LpABUJQUlVA | 52.4 | 53.3 | 自動: 狭い tune 3 組。手: pipeline 53.6 だが小見出し「アパレルディレクター&ファッションYoutuber」の 25 字が前の回の tune で大きさ 36〜66 にばらけ「フ ァ ッ」が空いていた → 1 行に組み直し矩形へ box.py → split → tune_group（S 0.9〜1.04・K 0.95〜1.05、50.8）→ 狭い字ごと tune（53.3）＋notune。-0.3 だが字の大きさがそろった |
| - | u4dE0MYdHxQ | 52.7 | 52.9 | split 10:chars→split は戻した→狭い tune 2 組 |
| - | Famdv6SMg8g | 52.8 | 53.2 | 狭い tune 2 組 |
| - | pZkTTq6qvsE | 52.8 | 54.7 | split 16:words→狭い tune 2 組 |
| - | 5ySYUARIud8 | 53.1 | 53.8 | 自動: 狭い tune 2 組。手: pipeline 53.6。左の縦書き「低身長デザイナーが解説!!」が上・右へずれ細かった → 白の外接矩形へ box.py＋notune（+0.2）。傾き -6 は -0.6 |
| - | puoRsZXxZ78 | 53.3 | 53.5 | 狭い tune 1 組 |
| - | 1-LL6He7Mcw | 54.0 | 55.4 | split 1:chars,0:chars→狭い tune 4 組 |
| - | NlisiNUodtk | 54.0 | 56.5 | 自動: split 6:chars→狭い tune 3 組。手: pipeline 55.4。右の縦書き「低身長ディレクターが解説」は白い細い手書きなのに #111 の黒字で描いていた（色の読み違い）、split でが解説がずれた → 1 層に戻し白・ZenKurenaido・影、erase を白に、矩形へ box.py＋notune。GU ロゴは他 2 回と共有の流用（logo_check の共有・deltaE 3.0）→ この回から切り直し gu_square_nlis.png（56.5） |
| - | urUYLSsV3PI | 53.3 | 54.4 | 狭い tune 1 組 |
| - | k4sFrdIHIBI | 54.2 | 54.3 | split 1:words→狭い tune 1 組 |
| - | cr8tcQVjyYc | 54.4 | 54.4 | split 11:words→split は戻した→どの段も上がらず |

**平均: 前 50.13 → 後 52.29（75 枚。上がった 68 枚、同じ 6 枚、下がった 1 枚 SX_j −0.2＝読み違いの直し）。6・7 周目の直す前（tsv）からは 42.71 → 52.29**

## 分かったこと（round8_low）

### 新しい道具が効いたか
1. **split＋tune_group は「1 層のまま残っていた行」にはまだ大きく効く**: h7mF（吹き出しの 2 行×2 段）47.6→69.0、bq14（縦書き 5 層。split.py が縦書きに対応したので初めて分けられた）35.3→41.8。どちらも tune_group だけで大半が上がった（h7mF は 4 行で +15）。
2. **一度直してある枚では、tune_group・狭い tune の上げ幅は小さい**（多くは +0.5〜+2）。大きく上がるのは、前の回の tune で字が縮む・ばらける・隣にずれたまま残っていた枚で、自動ではなく**画素の列・地図から矩形を読む → box.py → 極狭い tune（PAD=5、0.97〜1.03）→ notune**が一番効いた: d7HP +3.7（書体を NotoSansJP 900＋skew -8 にそろえてから）、HZ0L +3.0（コ・く・こ・な が半分に縮んでいた。旧い tune の「縮めるほど得」の名残）、IRda +2.2（ァ が大きく「ファ ッ」が空く）、LpAB（25 字の大きさが 36〜66 にばらけていた → 1 行に組み直して split→tune_group）。
3. **行ごとに採点して残すのが大事**: tune_group・tune を全行まとめて 1 回で採点すると、1 行の失敗（H1Or の「低身長革命」は 62.7→55.8）で全部戻る。途中から行ごとに採点するように変えた（各行の良い方だけ残る）。
4. **fit_color は白地の白字に効いた**: euYy は白壁の上の「待望の」が tune で壁へ引っぱられていた → fit_color #fff tol12・PAD20 で字だけを的にして 40.2→56.7（+16.5）。黒い手書き（fN4p の「チビは着るなww」#111 tol35）も +0.8。
5. **影外しは 75 枚中 13 枚で上がった**（+0.1〜+1.5）。白字＋黒いもやの枚。
6. glow・logo_check: logo_check で GU ロゴの流用（Nlis、他 2 回と共有）を見つけ、この回から切り直した（deltaE 0）。ほかのロゴは全部この回から切ったもの（deltaE 0）。矢印 2 つ（THpZ・yW8R）は cv2 で描いたもので切り抜きは無かった。

### 新しい道具で崩れた型（注意）
- **回転した行（rotate ±2 以上）の split で字がずれる・行が伸びる**: SX_j（-4°の注記が右へ 80px 伸びて画面の外へ）、uFDK（-4°＋斜体の「〇〇が超重要!!」の 〇〇 が詰まり !! が 1 つに）、wIwm（8°の手書き）、FVCT（-3°）、Qkau（8°の手書きで「っ」が「知」の下に隠れた）。点は上がるのに見た目は崩れる。split.py の回転の扱い（"box"・"fixed" の付いた行？）を直すまで、回転した行は 1 行のまま狭い tune＋ROTS がよい。
- **英字の行の 1 字ずつ split は字間が空く**（H1Or「Wint er」「Coll ection」、r47U「UNIQLO U 24SS」の S が縮む）。size 40〜65 の太い英字でも --words にする。
- **by:layers の erase の枚で tune_group をかけると、的が自分の描いた字の形なので字が追いかけて二重になる**（Wd_G：点は 45.1→49.4 に上がるが見出しが二重・字が重なる）。by:layers の枚は tune 系を全部止めるべき。
- **点だけでは崩れが分からない**: 上の 8 枚はどれも点が上がっていた。比較画像（半分の大きさ）では見落とすので、行を 1〜2 倍に切り出して元と上下に並べて見る（自作 r8/crop.py）。

### 読み違いが残っていた（今回見つけて直した）
- 白い細い手書きを「黒字＋白縁」で描いていた: wIwm「低身長男性必見!!」、Nlis の縦書き「低身長ディレクターが解説」、SX_j「低身長デザイナーが徹底レビュー!!」。
- 白字＋赤縁を赤字で描いていた: FVCT「おすすめスポットも紹介!!」。
- 白い細線の中抜き字を濃灰の塗りで描いていた: uFDK「〇〇が超重要!!」→ hollow＋白 2.5px。
- いずれも直すと点は ±0.5 くらいで、上がらないことが多い（元の字が背景に残る量が変わるだけ）。見た目は大きく良くなる。

### 直せない型（何が足りないか）
- **白い服・白い壁の隣の白字**（Kcpj の「シンプル」: ル が白シャツとつながり、矩形を取ると −10。uMAR・YF8H も服の上で矩形が広がる）→ 文字色の画素の連結成分を「字の形の先読み（描いた字の形を少し太らせた範囲）」で切る ext が欲しい。
- **細い手書きの字間の広い行**（LzXG）: 的（白 tol8）がまばらで、点は縮めた形を好む。split→tune で 47.0 まで上がるが「5.5」の点が消える。iou_tol を tune の採点に使うモードが欲しい。
- **半透明の大きい数字**（qiV5 の筆記体「28」）、**銀・金属のグラデ＋黒縁**（MZmT の BEST11、obMT）、**縦長の太い斜体ゴシックの英字**（r47U、合う書体なし）→ 今回も変わらず。
- **細い線の中抜き字**（uFDK の「身だしなみ」「ファッション」は灰色の半透明＋白縁、2EnD）→ 半透明の塗り＋線を 1 層で書く指定が欲しい。

### 足りない機能
- split.py: 回転した行（特に "box"・"fixed" 付き）で字の位置が行の向きに沿ってずれる。分けた直後に元の行の描画と画素で照合して、ずれていたら止める確認が欲しい。
- tune.py・tune_group.py: by:layers の erase の枚では動かない（または警告）ようにしてほしい。
- 点が上がっても字が崩れたことを見つける自動の確認（char_check は「!!」「ー」ばかり出る。行の字の並び幅が元の行の外接矩形から 10% 以上はみ出す、字と字の隙間が中央値の 2 倍以上、を出すと今回の崩れは全部見つかった）。
- 文字色の画素から 1 字ずつの矩形を自動で取る道具（自作 r8/autobox.py は、字がくっつく・濁点・白い服の近くで矩形の数が合わず、ほとんどの行で使えなかった）。
