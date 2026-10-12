# 素材の掃除（ロゴ以外の切り抜き・人物入りロゴの差し替え）

決まり: 元のサムネの写真・カード・文字の切り抜きは禁止（ブランドロゴだけ可。ロゴもその回のサムネから切り直す）。
作業前の spec: スクラッチパッドの `clean_bak/`。矢印・札の描画スクリプト: スクラッチパッドの `clean_work/arrow.py`・`star.py`
（元の赤い画素の範囲に、ベジェ曲線＋三角の頭／星形のパラメータを IoU で合わせ、cv2 の LINE_AA で 4 倍描きして縮小。画素はコピーしていない）。

## 対象 ID（前点 → 後点）

| ID | 前点 | 後点 | 差し替えたもの |
|---|---|---|---|
| BtFMK0EWAbs | 68.2 | 67.6 | 赤い曲がり矢印（写真の背景ごとの切り抜き）→ cv2 で描画 `assets/shapes/arrow_red_curve_btfm.png`（erase は full → 赤の色指定）。Instagram ロゴ（灰色の背景ごと）→ この回から切り直し、背景を透過 `assets/logos/instagram_btfm.png`（erase は full → ロゴの 6 色の色指定） |
| CoMYT3XMjkQ | 47.6 | 48.1 | 他の回（THpZ）の矢印の切り抜き `arrow_red_curve_thpz` を流用していた → cv2 で描画（白縁 6px を白で太く描いてから赤 #cd0102 を重ねる）`assets/shapes/arrow_red_curve_comy.png` |
| Gbae2_a5beo | 76.0 | 76.0 | 変更なし（`assets/shapes/arrow_red_curve_gbae.png` は cv2 で描いた単色の図形で違反ではないことを確認） |
| MTOjgr-Vmas | 78.6 | 75.0 | 赤い曲がり矢印（写真の背景ごと）→ cv2 で描画 `assets/shapes/arrow_red_curve_mtoj.png`（erase は full → 赤の色指定） |
| Ru70Z4wvHeo | 58.4 | 57.3 | ロゴ 4 枚（`uniqlo_red_square`・`muji_red_square`・`uniqlo_black_square`・`uniqlou_black_square`。どれも人物の顔入り）→ この回から 1 枚ずつ切り直し `uniqlo_red_ru70`・`muji_ru70`・`uniqlo_black_ru70`・`uniqlou_ru70`。ロゴの手前にいる人物の頭（白い光彩込み）は透過にし、spec の `front` 多角形（5 個）で元の人物を上に戻す |
| pT0qpo9i0pI | 77.5 | 66.7 | 赤い上向き矢印（後ろの服・人ごとの切り抜き 375×262）→ cv2 で描画（半透明 0.75、#e0141e）`assets/shapes/arrow_red_up_pt0q.png`。元の矢印は「ス」の下まで尻尾が伸びているので、そこまで描いた。erase は full → 赤（半透明の赤 5 色）の色指定。点が下がったのは採点の範囲が矢印全体に広がったため |
| yDHRoLXxX8c | 80.9 | 74.7 | GU×UNDERCOVER ロゴ（右下に女性の髪が入っていた）→ この回から切り直し、髪は透過＋`front` で戻す `assets/logos/gu_undercover_ydhr.png`。黒いずらし影は rect で別に描画。星形の札（「9/27 発売」の文字ごと切り抜き）→ cv2 で 26 角の星形を描画 `assets/shapes/badge_starburst_ydhr.png`、文字は text レイヤー 2 つ（「9/27」Inter 800、「発売」Noto Sans JP 900、白）。erase は札の赤・白の色指定 |

- fit.py は使わず、文字の位置合わせは helpers/snap_b16.py（yDHR の札の文字 2 つだけ）。erase の "by":"layers" は足していない。
- 削除した画像（どの spec も参照しておらず違反のもの）: assets/logos/ の arrow_red_curve_btfm・arrow_red_curve_mtoj・arrow_red_up_pt0q・badge_starburst_red_ydhr・instagram_grad_btfm・uniqlo_red_square・muji_red_square・uniqlo_black_square・uniqlou_black_square・gu_undercover_red_ydhr・uniqloc_colon_c_black_yepj（最後の 1 枚は人物の頭入りで未使用だったもの）。

## 触っていないが同じ違反がある回（別の担当が作業中）
- THpZuGk5aZw: `assets/logos/arrow_red_curve_thpz.png`（赤い矢印の切り抜き。ロゴではない）
- yW8RY0VbOHc: `assets/logos/arrow_red_curve_yw8r.png`（赤い矢印の切り抜き。ロゴではない）

## assets/logos/ 全体（556 枚を contact sheet で目視）で見つかった、他の違反
直していない。ID はその画像を使っている spec（grep）。

### ロゴではないもの（矢印・アイコン・カード・文字・写真）
| 画像 | 中身 | 使っている ID |
|---|---|---|
| arrow_black_curve_nn0b.png | 矢印（写真背景ごと） | nN0bxTWf9IE  |
| arrow_black_hand_r2gs.png | 矢印（写真背景ごと） | r2Gsi3qOH2g  |
| arrow_red_curve.png | 赤い矢印（切り抜き） | CFzF147E7vc  |
| avatar_gray_uiqc.png | アイコン（ロゴではない） | uIQcReIKhhs  |
| brandcard_hcot_1.png | ブランドのカード | HcoTwn1KXDY  |
| brandcard_hcot_2.png | ブランドのカード | HcoTwn1KXDY  |
| brandcard_hcot_3.png | ブランドのカード | HcoTwn1KXDY  |
| brandcard_hcot_4.png | ブランドのカード | HcoTwn1KXDY  |
| brandcard_hcot_5.png | ブランドのカード | HcoTwn1KXDY  |
| brandcard_hcot_6.png | ブランドのカード | HcoTwn1KXDY  |
| brandcard_hcot_7.png | ブランドのカード | HcoTwn1KXDY  |
| brandcard_hcot_8.png | ブランドのカード（手が写る） | HcoTwn1KXDY  |
| brandcard_hcot_9.png | ブランドのカード（指が写る） | HcoTwn1KXDY  |
| brandcard_hcot_10.png | ブランドのカード（手が写る） | HcoTwn1KXDY  |
| burst_black_swky1.png | 黒い集中線の飾り（写真・髪ごと） | sWkYeQl8BRo  |
| burst_black_swky2.png | 黒い集中線の飾り（写真ごと） | sWkYeQl8BRo  |
| check_red_awyz.png | 赤いチェック（写真ごと） | aWYzUBHycTw  |
| igcard_7mrq_1.png | コメントのカード（文字） | 7Mrqw2dPfbo  |
| igcard_7mrq_2.png | コメントのカード（文字） | 7Mrqw2dPfbo  |
| igcard_7mrq_3.png | コメントのカード（文字） | 7Mrqw2dPfbo  |
| igcard_7mrq_4.png | コメントのカード（文字） | 7Mrqw2dPfbo  |
| igcard_7mrq_5.png | コメントのカード（文字） | 7Mrqw2dPfbo  |
| igcard_7mrq_6.png | コメントのカード（文字） | 7Mrqw2dPfbo  |
| igcard_7mrq_7.png | コメントのカード（文字） | 7Mrqw2dPfbo  |
| igcard_7mrq_8.png | コメントのカード（文字） | 7Mrqw2dPfbo  |
| sweat_emoji_gu2o.png | 汗の絵文字（写真ごと） | GU2ON4koLmk  |
| warning_yellow_r6jx1.png | 警告マーク（写真ごと） | r6Jxy2FETpM  |
| warning_yellow_r6jx2.png | 警告マーク（写真ごと） | r6Jxy2FETpM  |
| wym_lidnm_ecstaff.png | ロゴの下に「ECスタッフ」の文字 | zGuc4mpBDJ0  |
| gu_blue_bag_wpdn.png | ロゴ＋見出しの文字（絶対買…） | w_Pdnt5SLgE  |
| gu_blue_rot_gu2o.png | ロゴ＋赤い文字 | GU2ON4koLmk  |
| gu_blue_square_tilted_lnmq.png | ロゴ＋「2024」の文字 | LnmQ9GYPsHU  |
| gu_blue_square_nn5x.png | ロゴ＋「作」の文字・手 | Nn5xhSpBtMc  |
| gu_blue_square_x1mi.png | ロゴ＋人物＋文字 | x1MIToUS3d4  |
| gu_blue_3ddx.png | ロゴ＋服の写真 | 3DDxA28X06s  |
| gu_blue_fikk.png | ロゴ＋商品の写真 | fikkntDS3-k  |
| gu_blue_bag_kipv.png | ショッパーの写真ごと | kipVVE0CkUY  |
| gu_blue_square_uruy.png | ロゴ＋紙袋の写真 | urUYLSsV3PI  |
| uniqlo_red_rot_xq6q.png | ショッパーの写真ごと | xq6qetN808c  |
| uniqlou_black_8nqq.png | ロゴ＋紙袋の写真 | 8nQqWy24FYw  |
| uniqlo_black_8nqq.png | ロゴ＋紙袋の写真・人物 | 8nQqWy24FYw  |
| zozotown_black_dwdz.png | ロゴ＋靴の写真 | DWDz1rp0LHQ  |
| uniqlou_pair_small_l0qd.png | ロゴ＋黒い文字（手書き） | L0qdsfyFxYY  |

### ロゴだが人物（顔・頭・髪・指）が写り込んでいるもの
| 画像 | 写り込み | 使っている ID |
|---|---|---|
| uniqlo_katakana_red_ovcl.png | 人物の顔 | OVCLGjU9Du4  |
| uniqlo_red_vpair_cut_nesp.png | 人物の顔 | nESPvxlUpKw  |
| uniqloc_colon_black_sfzu.png | 人物の顔 | SfZuXd01kvM  |
| uniqlou_black_yepj.png | 人物の顔 | yepjqOuHxx8  |
| uniqlo_black_yepj.png | 人物の顔 | yepjqOuHxx8  |
| uniqlo_kata_black_euyy.png | 人物の顔（下） | euYyoHSr3B8  |
| uniqlo_red_yepj.png | 人物の頭 | yepjqOuHxx8  |
| uniqlo_red_square_sfzu.png | 人物の頭 | SfZuXd01kvM  |
| uniqlo_black_square_sfzu.png | 人物の頭 | SfZuXd01kvM  |
| uniqlo_black_square_sfzu_2.png | 人物の頭 | SfZuXd01kvM  |
| uniqlo_red_square_lisx.png | 人物の顔 | LISxBpIilxo  |
| uniqlo_red_cut_fwuj.png | 人物 | FWuJoYzSz8U  |
| uniqlo_red_dli6.png | 人物の顔 | dlI6Wq1yHj4  |
| uniqlou_pair_white_ncz.png | 人物の頭 | nczPFDj6VqI  |
| uniqlou_u_black_sndh.png | 人物の頭 | SNDhAqvswRM  |
| uniqlou_u_black_ozty.png | 人の指 | oZtYOlehxus  |
| muji_maroon_ovzs.png | 人物 | OvZsUCoeZUQ  |
| muji_maroon_square_15jj.png | 人物 | 15jJQnnaPQk  |
| gu_blue_ftpk.png | 人物の頭 | FTPKbFQy-GI  |
| gu_blue_square_24cw.png | 人物の頭 | 24CweW03ryU  |
| gu_blue_square_fwuj.png | 人物の頭 | FWuJoYzSz8U  |
| gu_blue_square_lrpq.png | 人の指 | L-RPQSwVdyk  |
| gu_blue_square_sfzu.png | 人物の頭 | SfZuXd01kvM  |
| uniqlo_kata_red_sjdy.png | 人物の髪 | sjDyBj8NSDg  |
| uniqlo_kata_red_w1d.png | 人物の頭 | w1dTeJfTP4s  |
| familymart_sq.png | 人物の頭 | FTPKbFQy-GI  |
| confect_white_df9c.png | 人物の髪 | Df9CmIZ8EFA  |
| cos_white_df9c.png | 人物の髪 | Df9CmIZ8EFA  |
| uniqlou_u_black_kbsa.png | 人物の髪 | KBsary5SFwA  |
| uniqlou_u_black_kg5k.png | 人物の髪 | kg5KC0Fuw0s  |
| uniqlou_u_black_l0qd.png | 人物の髪 | L0qdsfyFxYY  |
| wym_lidnm_white_gsz2.png | 人物の髪 | GsZ2zexyN-4  |

### 軽いもの（参考。背景の写真が入っている／2 枚組を間の背景ごと）
- 写真の背景ごと切っているロゴ: shiun_white_*（240〜251 番台の多く）、uniqloc_black_*（purple・白シャツなどの写真背景）、nike_white_wd5y、newbalance_white_doup、newbalance_red_6df、yoke_white_*、kaneisa_script_white_owgj、stevenalan_script_white_wd5y、adidas_white_doup、adidas_black_qkau など。透過にして切り直すのが望ましい。
- 2 枚組を間の背景ごと: uniqlo_pair_*・uniqlo_red_pair_*・uniqlou_pair_black_*（スキルの決まりでは 1 枚ずつ）。
- 人物の髪がごく一部だけ端に入っているものは他にも多数（gu_blue_shadow_*、uniqlo_red_*、uniqlo_kata_red_* の一部）。上の表は目で見て明らかなものだけ。
