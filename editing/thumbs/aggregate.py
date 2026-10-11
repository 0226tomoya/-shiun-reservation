"""全サムネの仕様を同じ条件で採点し直して一覧にする。

    python3 aggregate.py [--rerender]
出力: summary.tsv（行番号・ID・点数・形の一致・にじみ許容・切り抜き画像の有無・型）と、点数の分布。
--rerender で全部描き直して採点（遅い）。無ければ out/ の最新の採点を使う。
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/th/out'
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(HERE, 'list2y.tsv'))]


def crops(spec):
    # ロゴ以外の大きな画像（元の写真・カードの切り抜き）＝再現ではないもの
    big = 0
    for L in spec.get('layers', []):
        if L.get('type') == 'image':
            w, h = L.get('w', 0), L.get('h', 0) if not isinstance(L.get('h'), str) else L.get('w', 0)
            if w * h > 1280 * 720 * 0.04:
                big += 1
    return big


def main():
    if '--rerender' in sys.argv:
        import render as R  # noqa
        from playwright.sync_api import sync_playwright
        os.environ.setdefault('THUMB_ORIG', '/tmp/claude-0/-home-user--shiun-reservation/d72f7582-7e9c-5464-8148-e66e3d2158e4/scratchpad/yt/thumbs')
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
            for i, r in enumerate(rows):
                sp = os.path.join(HERE, 'specs', r[0] + '.json')
                if not os.path.exists(sp):
                    continue
                page = b.new_page(viewport={'width': 1280, 'height': 720})  # フォントの積み増しで重くならないよう 1 枚ごとに
                try:
                    R.run(sp, os.path.join(os.environ['THUMB_ORIG'], r[0] + '.jpg'), OUT, page)
                except Exception as e:
                    print('NG', r[0], e)
                page.close()
            b.close()
    out = ['行\tID\t点数\tIoU\tIoU許容\t切り抜き\tタイトル']
    sc = []
    missing = []
    for i, r in enumerate(rows):
        sp = os.path.join(HERE, 'specs', r[0] + '.json')
        js = os.path.join(OUT, r[0] + '_score.json')
        if not os.path.exists(sp):
            missing.append(i)
            continue
        spec = json.load(open(sp))
        s = json.load(open(js)) if os.path.exists(js) else {}
        c = crops(spec)
        sc.append((s.get('score', 0), s.get('iou', 0), s.get('iou_tol', 0), c))
        out.append(f"{i}\t{r[0]}\t{s.get('score', '')}\t{s.get('iou', '')}\t{s.get('iou_tol', '')}\t{c}\t{r[3][:40]}")
    open(os.path.join(HERE, 'summary.tsv'), 'w').write('\n'.join(out) + '\n')
    import statistics as st
    v = [x[0] for x in sc]
    print(f'仕様 {len(sc)} 枚 / 未作成 {len(missing)} 枚')
    if v:
        print(f'点数 平均 {st.mean(v):.1f} 中央 {st.median(v):.1f} / 80 以上 {sum(x >= 80 for x in v)} / 70 以上 {sum(x >= 70 for x in v)} / 50 未満 {sum(x < 50 for x in v)}')
        print(f'IoU 平均 {st.mean(x[1] for x in sc):.3f} / にじみ許容 {st.mean(x[2] for x in sc):.3f} / 切り抜きあり {sum(1 for x in sc if x[3])} 枚')


if __name__ == '__main__':
    main()
