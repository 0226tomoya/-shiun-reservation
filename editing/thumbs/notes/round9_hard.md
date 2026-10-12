# round9_hard（9 周目 F チーム：これまで直せなかった型）

対象: 指定 8 枚＋round8_low.md で「白地の白字」「白い壁・白い服／シャツの上の白字」とされた euYy・uMAR（YF8H は暗い服の上なので外した）。
退避: scratchpad/r9_bak/（ID.orig.json＝開始時、ID.best.json＝最終）。前＝開始時に採点し直した点。最後に全枚へ sweep（影外し・grow）。

| ID | 型 | 前 | 後 | 何をしたか |
|---|---|---|---|---|
| qiV5AIev7J4 | 半透明の大きい数字「28」 | 30.8 | 34.0 | 画素で読むと「28」は白の約 47% 透過（暗い所 120・ズボンの上 160）。Cormorant の斜体＋#b4b4b4 → #dddddd・opacity 0.52（形の一致に入る 128 を超える最小）。erase の色 #a8a8a8 は字の 120 前後に合っておらず「8」が背景に丸ごと残っていた → #828282＋#a8a8a8 tol12 に、灰色のズボンの上だけ #a8a8a8 のみの 4 つの矩形に分割。書体候補（GreatVibes・Allura・Pinyon・AlexBrush・Bodoni 等）で PinyonScript が最良 → split で 2 と 8 に分け、広い tune（S 0.8〜1.2）＋ROTS。notune。grow=5 |
| 2EnD6PALGYY | 灰色の半透明＋白縁の中抜き字 | 28.3 | 28.4 | 「価格破壊」の 2 層（塗り rgba .13＋hollow 線）を fill_opacity 0.23＋白縁 1 層ずつに統合（塗り 70〜80 / 背景 20 から α≈0.23 と逆算）。縁は fill_opacity だと中心振り分けの 2w なので w=0.75（=1.5px）が最良、2.5 は -5。tune（fit_color 白）は -0.5 で戻した。点はほぼ同じ: 下の「足りない描画機能」1 |
| uFDK5oSTQ5E | 灰色の半透明＋白縁 | 51.6 | 58.3 | 「身だしなみ」「ファッション」「女性に言っては…」を #4a4a4a の不透明で描いていた → 実際は壁 172 の上で 133（黒 α0.23）→ #000・fill_opacity 0.23・白縁 1.25（54.5）。「○○が超重要!!」は ○○ だけ中抜き・残りは半透明の塗り → runs で ○○ を透明、fill_opacity＋縁を 1 層に。erase から灰を外し白だけに。左 11 字を fit_color 白 PAD8 で tune（55.0）。下線 4 本は「白 2px・灰 4px・白 2px の帯」なのに白線＋濃灰線で位置も 4〜8px 下 → 画素で測り直し白 8px＋#8c8c8c 4px に（58.5）。右上 2 行を fit_color で tune（58.3、線と字の重なりが直る）＋notune |
| MZmTmXDVIXU | 銀・金属のグラデ＋黒縁 | 37.1 | 39.9 | 「BEST11」が 70px 下・大きすぎ → 黒縁の外接矩形を画素で測り 6 字を box.py（38.4）。字の中の明るさを縦に測ると B・E・T で全く同じ段（行全体に 1 本のグラデ: 255→56（y440）→224（y540）→48（y690））→ 各字の要素の箱（y〜y+size×line）から絶対 y を % に換算した 23 段の linear-gradient（39.3）。background-attachment:fixed は効かなかった。縁 黒3＋白6＋光彩 14px（39.7）、erase の #000 を外す、grow=5。書体候補は Playfair 900 のまま |
| obMTx7dd_II | 銀グラデ＋黒縁 | 44.4 | 45.6 | 縦に測ると銀は 3 段（195→255→195）で、今の fill が既に合っていた。下の行 7 字を画素の矩形へ box.py（45.4）。斜体＋細い灰縁（38.6）・黒縁 6（44.5）は下がった。sweep で影 1 層外し・grow=5 |
| KcpjBQPnDMc | 白い服の隣の白字 | 48.9 | 49.0 | 白 tol12 の連結成分で 8 字の矩形が初めて正しく取れた（白シャツ ≒200 は外れる）。プ の ゜ が erase の外（y<500）→ erase を y486 から。box.py だけだと 41.9（字形が合わず IoU が下がる）→ fit_color #fcfcfb tol12 で 2 回 tune（PAD15→10）で 48.7、「シン プル」の隙間が消えた。sweep で影外し・grow=5 で 49.0 |
| LzXG6WP5xmo | 字間の広い細い手書き | 41.4 | 51.6 | 書体 5 種（ZenKurenaido・Yomogi・KleeOne 400・YuseiMagic・HachiMaruPop）を 1 行のまま字間で幅を合わせると 33〜37 で全部下がる。FORCE=1 で split（元の行との IoU 0.70）→ tune_group → 字ごと tune は 47.8 だが「5.5」の点が消え「c n」と崩れた → 白 tol14 の列の切れ目から 26 字の矩形を取り box.py（45.4）→ 極狭い tune PAD5 0.97〜1.03（51.6）＋notune。見た目もほぼ一致。KleeOne 400 は 51.3 |
| r47UvWE1eN0 | 縦長の太い斜体の英字 | 51.6 | 51.6 | 白縁の外接矩形へ 6 書体（NotoSansJP 900・Anton・Oswald 700・BarlowCondensed 800・Inter 900・Montserrat 900）を skew -12 で box.py → 47.9〜48.8 で全部下。元の Montserrat（横に広い・白縁 5）に戻した |
| euYyoHSr3B8 | 白い壁の上の白字 | 56.7 | 57.6 | 前回 fit_color を付けていなかった「再コラボ!?」6 字に fit_color #fff tol12・PAD20 で tune（57.3）＋notune、grow=5 |
| uMARBnCQD_Y | 灰色のシャツの上の白字 | 44.5 | 44.5 | 見出し 21 字に fit_color #fcfcfb tol12・PAD12 で tune → 同点のため戻した |

**平均（10 枚）: 前 43.53 → 後 46.05（+2.52）。上がった 8 枚、同じ 2 枚（r47U・uMAR）**

## 分かったこと
1. **半透明の型は「色の読み違い」が本体だった**: uFDK は灰の塗りを不透明 #4a4a4a で描いていた（実際は黒 α0.23）。塗り α は「字の中の値・すぐ外の背景の値」の 2 点で逆算できる（qiV5: 2 か所の背景から α0.47・白、2EnD: α0.23、uFDK: 黒 α0.23）。
2. **fill_opacity の縁は中心振り分けで 2w の太さ**（普通の縁は外側に w）。同じ見た目にするには w を半分に（2EnD は 0.75、uFDK は 1.25）。
3. **α が 0.5 未満だと描いた塗りは形の一致（alpha>128）に入らない**。qiV5 のように塗りだけの字は opacity 0.52 以上にしないと IoU に数えられない。逆に縁＋半透明塗りの字は縁だけが数えられ、erase の色を縁の色だけにすると IoU が上がる（uFDK 0.633→0.68）。
4. **erase の色が実際の字の色とずれていて、元の字が背景に残っていた**（qiV5 の 28: #a8a8a8 tol14 に対し実際は 120 前後）。比較画像の右上（背景）を必ず見る。
5. **銀・金属のグラデは字ごとではなく行全体に 1 本**（MZmT の B・E・T で縦の明るさが同じ y で一致）。字ごとのレイヤーでは、要素の箱（y から size×line）で絶対 y を % に換算して同じ段を書けばよい。
6. **細い手書きの字間の広い行は「列の切れ目 → box.py → 極狭い tune（PAD5）」が効く**（LzXG +10.2）。split の照合（IoU 0.70）は字間・書体違いで低く出るので、この型は FORCE=1 で分けてから矩形で直すのが良い。
7. **白い服の隣の白字は fit_color の tol12 の連結成分で矩形が取れる**（Kcpj: 字 252・服 200）。ただし box.py は外接矩形を合わせるだけなので字形の違いで IoU が下がり、その後の fit_color tune で戻す必要がある。
8. 下線・帯など「線」の層も画素で測ると 4〜8px ずれ・色の構成違い（白・灰・白の帯）が残っていた（uFDK +3.5）。

## 足りない描画機能（これがあれば直る）
1. **半透明の字の下の背景を inpaint しない（逆合成で戻す）モード**: いまは描いた字の範囲（alpha>8）を全部 inpaint するので、半透明の字の中の服の織り目が消えて塗りつぶしになる（2EnD の region 22 が上がらない原因）。text に `"unblend": true` を付けると、その字の塗りの範囲は「元 = 背景×(1−α)＋色×α」を解いて背景を復元する（縁の範囲だけ inpaint）、という指定が欲しい。2EnD・qiV5・uFDK に効く。
2. **行全体に 1 本のグラデ（字ごとのレイヤーでも共有）**: `"fill_abs": true` などで linear-gradient の位置を画面の絶対座標（px）で書けるように（CSS の background-attachment:fixed は transform 下で効かない）。いまは字ごとに % を手計算している（MZmT・金グラデの全ランキング型）。
3. **筆記体の飾り（swash）付きの数字**: qiV5 の「28」は 2 の下の長い払い・8 の右上への長い尾があり、手持ちの筆記体（Pinyon・GreatVibes 等）に無い形。数字を SVG パス（cv2 で描く線＋太さ変化）で描ける "path" レイヤー（太さを点ごとに変えられる線）が欲しい。
4. **縦長の太い斜体ゴシックの欧文書体**（r47U）: Helvetica Neue Condensed Black Italic 系が無い。Anton は細長すぎ、Montserrat・Inter は横に広い。候補として "Archivo"（width 可変）・"Roboto Flex"・"Barlow Condensed 900 Italic"・"Saira ExtraCondensed" などの追加が必要。
5. **光彩（glow）を text にも**: MZmT の BEST11 は黒細縁の外に広い白の光彩。今は shadow 1 つ（一番外の縁にだけ）で、強さ・回数を image の "glow" のように [px, 色, 回数] で text に付けたい。
6. **box.py の字形照合版**: 外接矩形だけでなく、矩形の中で IoU 最大になる size・scale_x を選ぶ（Kcpj・LzXG で box→狭い tune の 2 段をやっている部分）。
