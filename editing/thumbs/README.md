# わむうチャンネルのサムネ再現（過去 2 年・477 本）

- 一覧: `list2y.tsv`（動画ID・おおよその公開日・長さ・タイトル。0 行目が最新）
- 元のサムネ: スクラッチパッドの `yt/thumbs/ID.jpg`（1280x720。`run.sh` が場所を知っている）
- 仕様: `specs/ID.json`（書式は `render.py` の先頭）。ロゴなどの画像素材: `assets/logos/`
- 採点・比較: `bash run.sh ID`（`fit` を付けると文字の位置・大きさを自動で詰めてから採点）
  - 比較画像 `…/th/out/ID_compare.jpg`: 左上＝元、右上＝文字を消した背景（**文字が残っていたら erase が足りない**）、左下＝再現、右下＝差（明るいほど違う）
  - 点数 = 50×形の一致（IoU）＋ 50×文字の範囲の一致（SSIM・色）。形の一致 0.85 以上が目標
- 使えるフォント（ファイル名＝font に書く名前）: NotoSansJP（100〜900）NotoSerifJP ZenOldMincho ShipporiMinchoB1 ShipporiMincho DelaGothicOne ZenKakuGothicNew ZenKakuGothicAntique ZenMaruGothic MPLUS1p MPLUS1 MPLUSRounded1c KosugiMaru YuseiMagic KleeOne ZenKurenaido HinaMincho KaiseiTokumin KaiseiOpti RocknRollOne ReggaeOne MochiyPopOne BIZUDPMincho BIZUDPGothic SawarabiMincho Murecho Yomogi ZenAntique ShipporiAntiqueB1 PottaOne RampartOne HachiMaruPop KiwiMaru ／ 欧文 BebasNeue Oswald Anton PlayfairDisplay CormorantGaramond Cinzel Montserrat ArchivoBlack GreatVibes DancingScript Allura Caveat EBGaramond Inter RobotoCondensed BarlowCondensed Lora LibreBaskerville JosefinSans Jost LeagueSpartan TenorSans Italiana BodoniModa DidactGothic MrDafoe HomemadeApple NothingYouCouldDo ReenieBeanie GochiHand KaushanScript Satisfy Sacramento PinyonScript AlexBrush Parisienne BadScript Cookie MarckScript ShadowsIntoLight PermanentMarker MrsSaintDelafield

## 再現のコツ
- 太い見出し（源ノ角ゴ Heavy 風）は NotoSansJP 900。もっと太いときは**同じ色の細い縁取り**を内側に足す（strokes の最初に [3,"同じ色"]）
- 白文字＋黒縁＋白縁＋影の多重縁は strokes に内側から順に並べる。影は shadow（一番外の縁に付く）
- 金のグラデーションは fill に linear-gradient（例 `linear-gradient(180deg,#fff7d0 0%,#f5d26b 40%,#b8862b 55%,#f9e39a 100%)`）
- 部分的に色や大きさが違う行は runs
- 細い明朝の大人っぽいタイトルは ShipporiMinchoB1 / ZenOldMincho / NotoSerifJP、細いゴシック＋広い字間は NotoSansJP 300〜500＋spacing 0.2〜0.4
- 手書き風は YuseiMagic / ZenKurenaido / KleeOne、筆記体の英字は GreatVibes / Allura / Parisienne
- ロゴ（UNIQLO・GU・MUJI・UNIQLO:C・UNIQLO U など）は元サムネのきれいな所を切り抜いて assets/logos に置き、image で使い回す（erase は "full":true）
- 人物・服・背景写真は元のまま（再現の対象は文字・図形・ロゴ・帯・枠）

## 追加された機能（batch02 の要望）
- runs の各要素に `size_em`（行の size に対する倍率）。fit で行の大きさを変えると一緒に変わる
- 文字の後ろに人物が来る: 仕様の `"front": [[[x,y],[x,y],...]]`（人物の輪郭の多角形）。中は元の画素を上に戻す
- 縁取りが黒で背景に紛れる: レイヤーに `"fit_color": "#文字色"`（fit はその色で形を合わせる）
- `"full": true` の erase（ロゴ・帯）も形の一致に数える（正しい位置に置けば一致）。ロゴの色で erase を重ねる工夫は不要
- グラデーション＋影は、影を下の層に分けた（文字が暗くならない）
- 長い行で小さい仮名が混ざり fit がずれるときは、かたまりごとに別のレイヤーに分けて fit する

## 共通の補助（helpers/。各担当が作って効いたもの）
- `helpers/chars.py ID y0 y1 x0 x1 thr k [white|black]`: 範囲の白（または黒）の画素を開処理して、列ごとの外接矩形（1 文字ずつの x0,x1,y0,y1）を出す。大見出しを 1 文字ずつのレイヤーに分けるときの目標になる（担当 16: 39→72 点）
- `helpers/snap_b11.py`・`helpers/snap_b16.py`: レイヤーの描いた形の外接矩形を、目標の矩形に合わせて size・scale_x・x・y を直す（fit より軽い）
- 新機能: `skew_y`、rect の `radius:"50%"`（楕円）
- **`helpers/split.py ID i[,j]`** → **`helpers/tune.py ID --apply [--layers ..] [--fonts 'NotoSansJP:900,ZenOldMincho:900']`**: 文字レイヤーを描いた位置のまま 1 文字ずつに分け、1 文字ずつ位置・大きさ・横幅・フォント・傾きを合わせる（2 周目で 20 枚が平均 34→56 点）。分けた後は比較画像で字が消えていないか必ず見る
- 太字の当たり: 大きい漢字＝ZenOldMincho 900 / NotoSerifJP 900、丸い仮名＝KaiseiTokumin 800、縦長の太ゴ＝MPLUS1p 900 か NotoSansJP 900＋scale_x 0.7〜0.8。英字の単語や日付は分けずに 1 行で
