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


---

# 2 回目（34 本。euYy・nczP・THpZ は担当が終わってから追加）

作業前の spec: スクラッチパッドの `clean_bak/`（1 回目と同じ場所。1 回目で退避済みの ID は上書きしていない）。
道具（スクラッチパッドの `clean_work/`）:
- `logo2.py`・`run2.py`・`batch2.py`: その回のサムネからロゴの箱だけを切り直す。ロゴの色（箱の色・字の色と、その間のにじみ）以外の画素（人物・物・文字）は透過にして、人物・物は `front` 多角形で元の画素を戻す。白黒のロゴは中間の灰色も人物とみなす。黒い箱に重なる黒髪は手で多角形（fpoly）を指定する
- `shopper.py`: ショッパー型。紙袋は rect（ロゴの外側の輪で色を測り、minAreaRect の角度）で描き、ロゴの箱だけを貼る
- `brandcards.py`: 白い札のブランドカード。札は rect、ロゴは札の色からの距離を不透明度にして字の形だけ（写真・指は透過）
- `arrows2.py`（1 回目の `arrow.py`）・チェック・汗・アバター: 元の色の範囲に形のパラメータを IoU で合わせ、cv2 の LINE_AA で描画（画素は使わない）
- 文字の位置合わせは `helpers/snap_b16.py` だけ（fit.py は使っていない）。erase の "by":"layers" は足していない

| ID | 前点 | 後点 | 差し替えたもの |
|---|---|---|---|
| nN0bxTWf9IE | 78.0 | 77.0 | 黒い曲がり矢印（写真の背景ごと）→ cv2 で描画 `assets/shapes/arrow_black_curve_nn0b.png`（erase は黒の色指定）。UNIQLO 2 枚はこの回の切り抜きで違反なし、そのまま |
| CFzF147E7vc | 46.8 | 46.9 | 赤い矢印（他の回の `arrow_red_curve.png`）→ cv2 で描画 `assets/shapes/arrow_red_curve_cfzf.png`＋灰色のぼかし影 `arrow_red_curve_cfzf_shadow.png`。UNIQLO ロゴも他の回の `uniqlo_red_small.png` だったので、この回から切り直し `uniqlo_red_cfzf.png` |
| uIQcReIKhhs | 69.5 | 69.5 | コメント欄の灰色のアバター（切り抜き）→ cv2 で円＋頭＋肩を描画 `assets/shapes/avatar_gray_uiqc.png`（3 か所） |
| HcoTwn1KXDY | 84.7 | 81.0 | ブランドの札 10 枚（写真・手ごと）→ 札は rect（色を測る）、ロゴはこの回から字の形だけ透過で切り直し `*_card_hcot.png`（10 枚）。手前の指は透過にし、`front` で元の指を戻す |
| aWYzUBHycTw | 78.4 | 74.8 | 赤いチェック（写真ごと）→ 2 本の太い帯を IoU で合わせて cv2 で描画 `assets/shapes/check_red_awyz.png`（erase は赤の色指定） |
| 7Mrqw2dPfbo | 85.8 | 75.8 | インスタのコメントカード 8 枚（文字ごと）→ rect（白地＋黒い帯）、text（ユーザー名 Inter／本文 Noto Sans JP 500／返信）、line（＞）で作り直し。アバターは平均色の円、絵文字は黄色の円。手前の指・服は `front` |
| GU2ON4koLmk | 61.1 | 55.1 | GU ロゴ（紙袋の写真・赤い文字ごと）→ 紙袋は rect、ロゴは箱だけ切り直し `gu_blue_tilted_gu2o.png`。汗の絵文字（切り抜き）→ cv2 で 3 粒の涙形を描画 `assets/shapes/sweat_drops_gu2o.png` |
| w_Pdnt5SLgE | 71.3 | 65.6 | GU の紙袋（見出しの文字ごと）→ 紙袋は rect、ロゴは箱だけ（文字の所は透過）`gu_blue_wpdn.png` |
| LnmQ9GYPsHU | 80.8 | 79.1 | 傾いた GU（「2024」の文字ごと）→ 箱の 4 隅の範囲だけ切り直し、文字の所は透過 `gu_blue_tilted_lnmq.png`。右の GU は人物の部分を透過＋`front` |
| x1MIToUS3d4 | 66.3 | 65.9 | GU ロゴ（人物と文字入り）→ 切り直し、髪は透過＋`front`（白い文字は front にしない） |
| fikkntDS3-k | 75.5 | 75.5 | UNIQLO・GU（商品の写真入り）→ 箱だけ切り直し |
| kipVVE0CkUY | 82.7 | 80.0 | GU・MUJI の紙袋の写真ごと → 紙袋は rect、ロゴは箱だけ `gu_blue_kipv.png`・`muji_kipv.png` |
| xq6qetN808c | 88.1 | 82.0 | UNIQLO（傾き）・MUJI・GU の紙袋の写真ごと → 紙袋は rect（傾き付き）、ロゴは箱だけ `uniqlo_red_tilted_xq6q.png`・`muji_xq6q.png`・`gu_blue_xq6q.png` |
| DWDz1rp0LHQ | 74.8 | 74.0 | ZOZOTOWN（靴の写真入り）→ 箱だけ切り直し、靴は透過＋`front` |
| L0qdsfyFxYY | 48.8 | 49.8 | UNIQLO・U（頭入り）→ 1 枚ずつ切り直し、頭は透過＋`front`。右上の小さい 2 枚組（手書き文字入り）→ 1 枚ずつ `uniqlo_black_small_l0qd`・`uniqlou_u_black_small_l0qd` |
| OVCLGjU9Du4 | 86.9 | 86.9 | UNIQLO 2 枚（顔入り）→ 箱だけ切り直し |
| nESPvxlUpKw | 48.5 | 44.4 | UNIQLO:C（写真ごと）→ UNIQLO の箱 `uniqlo_black_nesp` と「:C」の字だけ（背景透過）`uniqloc_colonc_nesp` に分割。右の縦 2 枚組（顔入り）→ 1 枚ずつ `uniqlo_red_nesp`・`uniqlo_kata_red_nesp`、顔は透過＋`front` |
| SfZuXd01kvM | 56.4 | 53.7 | 6 枚（頭・顔入り）→ 切り直し。黒い箱に重なる黒髪は手で多角形を指定して透過＋`front`。:C は字の形だけ |
| yepjqOuHxx8 | 56.6 | 55.8 | 4 枚（顔・頭入り）→ 切り直し、人物は透過＋`front` |
| LISxBpIilxo | 53.4 | 50.8 | UNIQLO・GU（顔入り）→ 切り直し、人物は透過＋`front` |
| dlI6Wq1yHj4 | 59.2 | 58.2 | UNIQLO・GU・MUJI（顔入り）→ 切り直し、人物は透過＋`front` |
| SNDhAqvswRM | 85.5 | 85.3 | 4 枚（頭入り）→ 切り直し、頭は透過＋`front` |
| oZtYOlehxus | 59.4 | 59.2 | UNIQLO・U（指入り）→ 切り直し、指は透過＋`front` |
| OvZsUCoeZUQ | 60.2 | 56.8 | MUJI（人物入り）→ 切り直し＋`front`。MUJI Labo・IDÉE（写真の背景ごと）→ 黒い字と白い影を字の形だけ透過で切り直し（`mujilabo_ovzs`＋`_shadow`、`idee_ovzs`＋`_shadow`） |
| 15jJQnnaPQk | 90.5 | 90.5 | MUJI（人物入り）→ 切り直し、人物は透過＋`front` |
| FTPKbFQy-GI | 55.3 | 54.8 | UNIQLO・GU・MUJI・FamilyMart（頭入り）→ 切り直し、頭は透過＋`front`。FamilyMart は `familymart_ftpk.png` に改名 |
| 24CweW03ryU | 66.0 | 65.8 | GU（頭入り）→ 切り直し＋`front` |
| L-RPQSwVdyk | 64.9 | 64.4 | UNIQLO・GU（指入り）→ 切り直し＋`front` |
| sjDyBj8NSDg | 78.6 | 78.0 | 4 枚（髪入り）→ 切り直し＋`front` |
| w1dTeJfTP4s | 75.6 | 75.3 | 4 枚（頭入り）→ 切り直し＋`front` |
| Df9CmIZ8EFA | 84.9 | 83.8 | ブランドの札 7 枚（髪・肌入り）→ 札は rect、ロゴは字の形だけ透過 `*_card_df9c.png`。髪・顔は手で多角形を指定して `front` |
| euYyoHSr3B8 | 40.4 | 40.2 | 右上の UNIQLO 2 枚（頭入り）→ 切り直し＋`front`。下の傾いた小さい 2 枚（布入り）→ 4 隅の四角だけ切り直し |
| nczPFDj6VqI | 71.9 | 71.6 | UNIQLO U の 2 枚組（頭入り）→ 切り直し、頭は手で多角形を指定して透過＋`front` |
| THpZuGk5aZw | 45.5 | 45.5 | 赤い曲がり矢印（切り抜き）→ cv2 で描画 `assets/shapes/arrow_red_curve_thpz.png` |

平均 68.6 → 66.9。点が下がったのは主に、(1) カード・紙袋を rect＋text で作り直した（7Mrq −10.0、xq6q −6.1、GU2O −6.0、w_Pd −5.7）、(2) 人物を透過にして `front` で戻したことで、人物の縁に背景の埋め跡が出た（nESP −4.1、OvZs −3.4、SfZu −2.7 など）。どれも違反のない版を採用した。

- 削除した画像（どの spec も参照しておらず違反のもの、40 枚）: arrow_black_curve_nn0b.png、arrow_red_curve.png、arrow_red_curve_thpz.png、avatar_gray_uiqc.png、brandcard_hcot_1.png、brandcard_hcot_10.png、brandcard_hcot_2.png、brandcard_hcot_3.png、brandcard_hcot_4.png、brandcard_hcot_5.png、brandcard_hcot_6.png、brandcard_hcot_7.png、brandcard_hcot_8.png、brandcard_hcot_9.png、check_red_awyz.png、confect_white_df9c.png、cos_white_df9c.png、familymart_sq.png、gu_blue_bag_kipv.png、gu_blue_bag_wpdn.png、gu_blue_rot_gu2o.png、gu_blue_square_tilted_lnmq.png、idee_black_ovzs.png、igcard_7mrq_1.png、igcard_7mrq_2.png、igcard_7mrq_3.png、igcard_7mrq_4.png、igcard_7mrq_5.png、igcard_7mrq_6.png、igcard_7mrq_7.png、igcard_7mrq_8.png、muji_red_bag_kipv.png、muji_red_bag_xq6q.png、mujilabo_black_ovzs.png、sweat_emoji_gu2o.png、uniqlo_red_rot_xq6q.png、uniqlo_red_vpair_cut_nesp.png、uniqloc_black_nesp.png、uniqlou_pair_small_l0qd.png、uniqloc_nesp.png（1 回目の失敗作）
- 名前を変えずに中身だけ作り直した画像は、上の表の各回の素材（どれもその回の spec だけが使っていることを grep で確認済み）。
- 追加で削除: batoner/blurhms/el/haruta/wym_white_df9c.png、gu_blue_square_xq6q.png、uniqlo_red_small.png（未使用になった写真入りの札・他の回のロゴ。7 枚）。2 回目の削除は合計 47 枚

## 触っていない違反（別の担当が作業中）
| ID | 画像 | 中身 |
|---|---|---|
| r2Gsi3qOH2g | arrow_black_hand_r2gs.png | 矢印（写真の背景ごと） |
| sWkYeQl8BRo | burst_black_swky1.png・burst_black_swky2.png | 黒い集中線の飾り（写真・髪ごと） |
| r6Jxy2FETpM | warning_yellow_r6jx1.png・warning_yellow_r6jx2.png | 警告マーク（写真ごと） |
| zGuc4mpBDJ0 | wym_lidnm_ecstaff.png | ロゴの下に「ECスタッフ」の文字 |
| Nn5xhSpBtMc | gu_blue_square_nn5x.png | ロゴ＋「作」の文字・手 |
| 3DDxA28X06s | gu_blue_3ddx.png | ロゴ＋服の写真 |
| urUYLSsV3PI | gu_blue_square_uruy.png | ロゴ＋紙袋の写真 |
| 8nQqWy24FYw | uniqlo_black_8nqq.png・uniqlou_black_8nqq.png | ロゴ＋紙袋の写真・人物 |
| FWuJoYzSz8U | uniqlo_red_cut_fwuj.png・gu_blue_square_fwuj.png | 人物入り |
| yW8RY0VbOHc | arrow_red_curve_yw8r.png | 赤い矢印の切り抜き |

---

# 3 回目（10 本。7 周目 A2 チーム）

作業前の spec: スクラッチパッドの `r7a2_bak/clean/`。道具（スクラッチパッドの `r7a2_work/`）:
- `simple.py`: ロゴの矩形を切り、手前の物のマスク（色・手で指定した多角形）だけを透過にして、`front` 多角形を返す（2 回目の `clean_work/logo2.py` の穴埋め・閉処理で字の中まで透過になる回があったので、閉処理なしの簡易版）
- `hand_arrow.py`: 細い手書き風の矢印（2 次ベジェの軸＋開いた V の頭、白い光彩）。元の黒の範囲に IoU で合わせて cv2 で描く
- `warn.py`: 警告マーク（角の丸い三角＋「！」の棒と点＋暗い縁）。三角と「！」を別々に IoU で合わせる
- `burst.py`: 黒い集中線の飾り。元の黒（max<22）の輪郭を少ない頂点の多角形（approxPolyDP 1.2px）にして、単色で fillPoly（LINE_AA、4 倍描き）。写真・髪の画素は使っていない
- 赤い矢印は 1・2 回目の `clean_work/arrow.py`（ベジェ＋三角の頭）
- fit.py・tune は使っていない。erase の "by":"layers" は足していない

| ID | 前点 | 後点 | 差し替えたもの |
|---|---|---|---|
| r2Gsi3qOH2g | 72.4 | 71.6 | 黒い手書き矢印（写真ごと）→ cv2 で描画（IoU 0.85、#282828、白い光彩 10px／ぼかし 4）`assets/shapes/arrow_black_hand_r2gs.png`。erase は full → 黒・白の色指定 |
| sWkYeQl8BRo | 64.3 | 59.5 | 黒い集中線の飾り 2 つ（写真・髪ごと）→ 単色の多角形で描画 `assets/shapes/burst_black_swky_1.png`・`_2.png`。erase は full → 黒（tol 18）。点が下がったのは元の飾りの縁の灰色のにじみが残るため（縁を 1〜2px 太らせると逆に下がった） |
| r6Jxy2FETpM | 56.9 | 54.4 | 警告マーク 2 つ（写真ごと）→ cv2 で描画（三角の IoU 0.97、黄 #fbc71e、「！」#373327、暗い縁 4px）`assets/shapes/warning_r6jx_1.png`・`_2.png`。erase は full → 黄・黒の色指定 |
| zGuc4mpBDJ0 | 64.2 | 60.7 | WYM LIDNM（「ECスタッフ」の文字・黒帯ごと）→ 白い札と LIDNM の字だけ（背景透過）`assets/logos/wym_lidnm_zguc.png`、黒帯は rect、「ECスタッフ」は text（Noto Sans JP 900、33px）。**rect を足すと、色指定の無い erase（四角だけの要素）の既定の色にその rect の色（黒）が加わって、髪・服まで消える**ので、四角だけの erase には前の既定の色（レイヤーの色 6 つ）を明示した |
| Nn5xhSpBtMc | 61.0 | 58.9 | GU（「作」の文字・手入り）→ 箱だけ切り直し `gu_blue_box_nn5x.png`。「作」の白と黒縁は透過（front にしない。文字は text レイヤーがある）、手と右端の人物は透過＋`front` |
| 3DDxA28X06s | 48.7 | 48.3 | GU（ハンガー・ジーンズ入り）→ 箱（白縁込み）だけ切り直し `gu_blue_box_3ddx.png`、手前の物は透過＋`front` |
| urUYLSsV3PI | 54.0 | 53.3 | GU（紙袋の持ち手入り）→ 箱だけ切り直し `gu_blue_box_uruy.png`、持ち手（G・B が 95 より明るい画素）は透過＋`front` |
| 8nQqWy24FYw | 60.6 | 58.9 | UNIQLO・U の黒い箱（紙袋の写真・人物入り）→ 箱だけ切り直し `uniqlo_black_box_8nqq.png`・`uniqlou_black_box_8nqq.png`。紙袋は手で多角形、持ち手は中間の灰色（110〜232）で拾って透過＋`front`。右下の赤い UNIQLO は違反なしでそのまま |
| FWuJoYzSz8U | 58.6 | 58.0 | UNIQLO・GU（人物の頭入り）→ 箱だけ切り直し `uniqlo_red_box_fwuj.png`・`gu_blue_box_fwuj.png`。頭は手で多角形（15 点）、ラックの黒い棒は暗い色で拾って透過＋`front` |
| yW8RY0VbOHc | 49.4 | 49.3 | 赤い曲がり矢印（切り抜き）→ cv2 で描画（IoU 0.94、#da0e1b）`assets/shapes/arrow_red_curve_yw8r.png` |

平均 59.0 → 57.3。どれも違反のない版を採用。

- 削除した画像（どの spec も参照していないことを grep で確認、14 枚）: assets/logos/ の arrow_black_hand_r2gs、burst_black_swky1、burst_black_swky2、warning_yellow_r6jx1、warning_yellow_r6jx2、wym_lidnm_ecstaff、gu_blue_square_nn5x、gu_blue_3ddx、gu_blue_square_uruy、uniqlo_black_8nqq、uniqlou_black_8nqq、uniqlo_red_cut_fwuj、gu_blue_square_fwuj、arrow_red_curve_yw8r
- これで 1 回目の一覧（ロゴ以外の切り抜き・人物入りロゴ）は全部片付いた。残りは「軽いもの」（写真の背景ごとのロゴ・2 枚組）だけ
