"""編集データの配置プレビュー動画を作る（素材は枠で代用、音なし）。テロップ・インサートの位置とタイミングを再生で確かめる用。

    python3 preview_video.py FLAT.json OUT.mp4 [開始秒 終了秒]

表示が変わる瞬間（テロップ・インサートの頭と終わり）ごとに 1 枚描いてつなぐので、30 分の動画でも数分で作れる。
左上に分:秒（フレーム精度ではない）とチャプター名を出す。
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role  # noqa: E402
import preview_frames as pf  # noqa: E402

W, H = 960, 540
FPS = 30


def main():
    flat, out = sys.argv[1:3]
    items = [i for i in json.load(open(flat)) if i['enabled'] != '0' and len(i['path']) <= 1]
    total = max(i['t1'] for i in items)
    a0 = float(sys.argv[3]) if len(sys.argv) > 4 else 0.0
    a1 = float(sys.argv[4]) if len(sys.argv) > 4 else total

    # チャプター（マーカーが付いた最初のカットの頭）
    chs = sorted({(i['t0'], m['value']) for i in items for m in i.get('markers', []) if m['tag'] == 'chapter-marker'})

    def chapter(t):
        name = 'OP'
        for c, v in chs:
            if c <= t:
                name = v
        return name

    # 表示が変わる瞬間
    vis = [i for i in items if i['tag'] != 'mc-clip' and role(i) not in ('adjustment_main', 'adjustment_other')
           and i['name'] != 'BGM' and str(i['lane']) not in ('-1',) and not str(i['lane']).startswith('in')]
    pts = sorted({round(x, 3) for i in vis for x in (i['t0'], i['t1']) if a0 < x < a1} | {a0, a1} | {c for c, _ in chs if a0 < c < a1})
    # 1 フレーム未満の区間はまとめる
    clean = [pts[0]]
    for p in pts[1:]:
        if p - clean[-1] >= 1 / FPS:
            clean.append(p)
    if clean[-1] != a1:
        clean[-1] = a1

    tmp = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(out)))
    lines = []
    for k, (s, e) in enumerate(zip(clean, clean[1:])):
        im = pf.render(items, (s + e) / 2).resize((W, H))
        d = ImageDraw.Draw(im)
        d.rectangle((0, H - 26, W, H), fill=(0, 0, 0))
        d.text((8, H - 24), f'{chapter(s)}　配置プレビュー（素材は枠で代用・音なし）', fill=(230, 230, 230), font=pf.font(pf.SANS, 16))
        path = os.path.join(tmp, f'{k:05d}.png')
        im.save(path)
        lines.append(f"file '{path}'\nduration {e - s:.4f}\n")
    lines.append(f"file '{path}'\n")
    lst = os.path.join(tmp, 'list.txt')
    open(lst, 'w').writelines(lines)
    font = pf.SANS
    draw = (f"drawtext=fontfile={font}:text='%{{eif\\:floor((t+{a0})/60)\\:d}}\\:%{{eif\\:mod(floor(t+{a0})\\,60)\\:d\\:2}}"
            f".%{{eif\\:floor(mod((t+{a0})*10\\,10))\\:d}}':x=w-tw-10:y=h-24:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.8")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf', f'fps={FPS},{draw}',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print(f'{len(clean) - 1} 場面 -> {out} ({os.path.getsize(out) / 1e6:.1f}MB, {a1 - a0:.0f} 秒)')


if __name__ == '__main__':
    main()
