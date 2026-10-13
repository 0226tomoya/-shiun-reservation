#!/usr/bin/env python3
"""Final Cut Pro の書き出し (.fcpxmld.zip / .fcpxmld / .fcpxml) から
プロジェクトのタイムライン上のピン (マーカー) 位置を拾い、YouTube チャプター形式の目次を出力する。

デフォルトの出力:
    00:00 OP
    <ピン1> 1人目
    ...
    <最後のピン> ED

使い方:
    python3 -I fcpxml_toc.py <入力> [--label "{n}人目"] [--project 名前] [--no-op] [--no-ed] [--debug]
"""
import argparse
import os
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from fractions import Fraction

CLIP_TAGS = {"asset-clip", "clip", "ref-clip", "mc-clip", "sync-clip",
             "video", "audio", "title", "gap"}


def parse_time(s):
    if not s:
        return Fraction(0)
    s = s.rstrip("s")
    if "/" in s:
        a, b = s.split("/")
        return Fraction(int(a), int(b))
    return Fraction(s)


def find_fcpxml(path, workdir):
    if os.path.isfile(path) and path.endswith(".fcpxml"):
        return path
    if os.path.isdir(path):
        base = path
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            z.extractall(workdir)
        base = workdir
    else:
        sys.exit(f"入力を読めません: {path}")
    for root, _, files in os.walk(base):
        for f in files:
            if f.endswith(".fcpxml"):
                return os.path.join(root, f)
    sys.exit("fcpxml が見つかりません")


def collect_markers(spine, eyecatch_key=None, eyecatches=None):
    """タイムライン上で実際に見えている (クリップの使用範囲内の) マーカーを返す。

    eyecatch_key と eyecatches (list) を渡すと、名前に eyecatch_key を含む
    クリップの (終了時刻, クリップ名) も eyecatches に追加する。
    """
    found = []

    def walk(el, parent_tl0, parent_start, parent_end):
        for c in el:
            if c.tag == "spine":
                walk(c, parent_tl0 + (parse_time(c.get("offset")) - parent_start), Fraction(0), None)
                continue
            if c.tag not in CLIP_TAGS:
                continue
            off = parse_time(c.get("offset"))
            start = parse_time(c.get("start"))
            dur = parse_time(c.get("duration"))
            tl0 = parent_tl0 + (off - parent_start)
            for m in c.findall("marker") + c.findall("chapter-marker"):
                ms = parse_time(m.get("start"))
                if start <= ms < start + dur:
                    found.append((tl0 + (ms - start), m.get("value"), c.get("name")))
            # 親の使用範囲外に隠れている接続クリップは数えない
            visible = parent_end is None or parent_start <= off < parent_end
            if (eyecatches is not None and eyecatch_key and visible
                    and eyecatch_key in (c.get("name") or "")):
                eyecatches.append((tl0 + dur, c.get("name")))
            walk(c, tl0, start, start + dur)

    walk(spine, Fraction(0), Fraction(0), None)
    found.sort()
    # 同じ秒に重なったピンは1つにまとめる
    dedup = []
    for item in found:
        if not dedup or int(item[0]) != int(dedup[-1][0]):
            dedup.append(item)
    return dedup


def pair_eyecatches(eyecatches, markers, tolerance):
    """アイキャッチ(目次を付ける場所)とピン(時刻の基準)を組にする。

    アイキャッチ終了 -0.5秒〜+tolerance 秒 (YouTube チャプターの最短間隔 10 秒) の
    最も近い未使用ピンを相方にする。相方が居れば目次の時刻はそのピン、居なければ
    (つけ忘れ) アイキャッチ終了時刻。
    戻り値: (chapters=[(時刻, ピン名 or None, アイキャッチ名, 組か)], 余ったピン)
    """
    used = set()
    chapters = []
    for end, name in sorted(eyecatches):
        cand = [(abs(t - end), i) for i, (t, _, _) in enumerate(markers)
                if i not in used and end - Fraction(1, 2) <= t <= end + tolerance]
        if cand:
            i = min(cand)[1]
            used.add(i)
            chapters.append((markers[i][0], markers[i][1], name, True, end))
        else:
            chapters.append((end, None, name, False, end))
    leftover = [m for i, m in enumerate(markers) if i not in used]
    return chapters, leftover


def fmt(t, use_hours):
    s = int(t)  # 秒未満は切り捨て
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if use_hours else f"{m:02d}:{sec:02d}"


def detect_scale(seq, root):
    """FCP のタイムコード表示 (NDF) に合わせる倍率。

    59.94/29.97/23.976p を NDF で表示すると、タイムコード秒は実時間より 0.1% 遅れる
    (実測: 25 分で約 1.5 秒)。目次はタイムラインのタイムコードを見て打つので、
    それに合わせる。DF や整数フレームレートでは 1 (実時間)。
    """
    if seq.get("tcFormat") != "NDF":
        return Fraction(1)
    fmt_el = None
    for f in root.findall(".//format"):
        if f.get("id") == seq.get("format"):
            fmt_el = f
            break
    fd = parse_time(fmt_el.get("frameDuration")) if fmt_el is not None else Fraction(0)
    if fd and fd.numerator == 1001:
        return Fraction(1000, 1001)
    return Fraction(1)


ED_NAME = ("ED", "エンディング", "エンド")


def _is_ed(name):
    return (name or "").strip().upper() in ED_NAME


def compute(markers, eyecatches, total, *, label="{n}人目", op=True, ed=True,
            tolerance=Fraction(10), scale=Fraction(1), basis="eyecatch", ed_mode="last_chapter"):
    """目次を決める (純粋関数)。戻り値 = (lines, warnings, info)。

    lines = [(表示秒, 見出し, 補足)] / info = {"forgot": [表示秒], "leftover": [(表示秒, ピン名)], "mode": "eyecatch"|"pin"}
    時刻は scale 倍して表示用にする (内部の組み合わせ判定は実時間)。
    basis: "eyecatch" = 組の時刻はアイキャッチの終わり / "pin" = 組のピンの時刻。
    ed_mode: "last_chapter" = 最後の目次を ED にする (後ろのピンは使わない) / "trailing_pin" = 最後のアイキャッチより後ろの最後のピン。
    """
    warnings, lines = [], []
    info = {"forgot": [], "leftover": [], "mode": "pin"}
    if eyecatches:
        info["mode"] = "eyecatch"
        chapters, leftover = pair_eyecatches(eyecatches, markers, tolerance)
        # 目次の時刻: basis に従う (ピンが無いアイキャッチはアイキャッチ終了)
        chapters = [((c[4] if basis == "eyecatch" else c[0]), c[1], c[2], c[3]) for c in chapters]
        dedup = []
        for c in chapters:
            if not dedup or int(c[0] * scale) != int(dedup[-1][0] * scale):
                dedup.append(c)
        chapters = dedup
        info["forgot"] = [c[0] * scale for c in chapters if not c[3]]
        last_t = chapters[-1][0] if chapters else Fraction(0)
        ed_pin = None
        if ed and ed_mode == "trailing_pin":
            after = [m for m in leftover if m[0] > last_t]
            if after:
                ed_pin = after[-1]
                leftover = [m for m in leftover if m is not ed_pin]
        ed_idx = None
        if ed and ed_pin is None and chapters:
            ed_idx = len(chapters) - 1          # 最後のアイキャッチ = ED の入口
        if ed and ed_pin is None and ed_idx is None:
            warnings.append("アイキャッチが無いので ED を付けません")
        info["leftover"] = [(m[0] * scale, m[1]) for m in leftover]
        if op and (not chapters or int(chapters[0][0] * scale) > 0):
            lines.append((Fraction(0), "OP", None))
        n = 0
        for i, (t, v, name, paired) in enumerate(chapters):
            note = f"{v} / {name}" if paired else "ピン無し→アイキャッチ位置から補完"
            if i == ed_idx:
                lines.append((t * scale, "ED", note))
            else:
                n += 1
                lines.append((t * scale, label.format(n=n), note))
        if ed_pin:
            lines.append((ed_pin[0] * scale, "ED", f"{ed_pin[1]} / {ed_pin[2]}"))
    else:
        if op and (not markers or int(markers[0][0] * scale) > 0):
            lines.append((Fraction(0), "OP", None))
        body = markers if not ed else markers[:-1]
        for i, (t, v, c) in enumerate(body, 1):
            lines.append((t * scale, label.format(n=i), f"{v} / {c}" if v else None))
        if ed and markers:
            t, v, c = markers[-1]
            lines.append((t * scale, "ED", f"{v} / {c}" if v else None))
    return lines, warnings, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--label", default="{n}人目", help="各ピンの見出し。{n} が通し番号になる")
    ap.add_argument("--project", help="プロジェクト名 (複数ある場合)")
    ap.add_argument("--no-op", action="store_true", help="先頭の 00:00 OP を付けない")
    ap.add_argument("--no-ed", action="store_true", help="ED を付けない")
    ap.add_argument("--eyecatch", default="アイキャッチ",
                    help="アイキャッチと見なすクリップ名の一部 (既定: アイキャッチ)")
    ap.add_argument("--no-eyecatch", action="store_true", help="アイキャッチを使わず、従来どおりピンだけで目次を作る")
    ap.add_argument("--tolerance", type=float, default=10.0,
                    help="アイキャッチ終了後この秒数以内のピンを組の相手とする (既定 10)")
    ap.add_argument("--time-basis", choices=["eyecatch", "pin"], default="eyecatch",
                    help="目次の時刻: eyecatch=アイキャッチの終わり(既定・公開済み動画と最も一致) / pin=組のピンの位置")
    ap.add_argument("--timecode", choices=["auto", "real"], default="auto",
                    help="auto: FCP のタイムコード表示(NDF)に合わせる / real: 実時間のまま (既定 auto)")
    ap.add_argument("--debug", action="store_true", help="マーカー名・クリップ名も表示")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        path = find_fcpxml(a.input, tmp)
        root = ET.parse(path).getroot()

    projects = root.findall(".//project")
    if a.project:
        projects = [p for p in projects if p.get("name") == a.project]
    if not projects:
        sys.exit("project が見つかりません")
    if len(projects) > 1:
        # 未指定なら「アイキャッチを含む > 名前が 本編 > 長い」の順で選ぶ (サムネ/物撮り等の短いプロジェクトを避ける)
        def rank(p):
            sq = p.find("sequence")
            eyes = []
            collect_markers(sq.find("spine"), a.eyecatch, eyes)
            return (len(eyes) > 0, p.get("name") == "本編", parse_time(sq.get("duration")))
        projects = sorted(projects, key=rank, reverse=True)
        print("複数のプロジェクトがあります。" + projects[0].get("name") + " を使います"
              "(別のものは --project で指定): " + ", ".join(p.get("name") for p in projects),
              file=sys.stderr)
    proj = projects[0]
    seq = proj.find("sequence")
    scale = detect_scale(seq, root) if a.timecode == "auto" else Fraction(1)
    total = parse_time(seq.get("duration")) * scale
    eyecatches = []
    markers = collect_markers(seq.find("spine"), None if a.no_eyecatch else a.eyecatch, eyecatches)
    use_hours = total >= 3600

    lines, warnings, info = compute(
        markers, eyecatches, total, label=a.label, op=not a.no_op, ed=not a.no_ed,
        tolerance=Fraction(a.tolerance).limit_denominator(1000), scale=scale,
        basis=a.time_basis)

    tc = "" if scale == 1 else " / タイムコード(NDF)換算"
    if info["mode"] == "eyecatch":
        print(f"# project: {proj.get('name')} / 全長 {fmt(total, use_hours)} / "
              f"アイキャッチ {len(eyecatches)} 個 / ピン {len(markers)} 個{tc}", file=sys.stderr)
        if info["forgot"]:
            print("# ピンのつけ忘れ候補 (アイキャッチ終了位置を時刻にして目次に載せました): "
                  + ", ".join(fmt(t, use_hours) for t in info["forgot"]), file=sys.stderr)
        if info["leftover"]:
            print("# 参考: アイキャッチと組でないピンは目次に載せていません: "
                  + ", ".join(f"{fmt(t, use_hours)}[{v}]" for t, v in info["leftover"]), file=sys.stderr)
    else:
        if not a.no_eyecatch:
            print(f"# 警告: 「{a.eyecatch}」のクリップが見つからないので、ピンだけで目次を作ります",
                  file=sys.stderr)
        print(f"# project: {proj.get('name')} / 全長 {fmt(total, use_hours)} / ピン {len(markers)} 個{tc}",
              file=sys.stderr)
    secs = [int(t) for t, _, _ in lines]
    if len(lines) < 3:
        warnings.append("目次が3個未満です。YouTube のチャプターは3個以上必要です")
    short = [f"{fmt(secs[i], use_hours)}→{fmt(secs[i + 1], use_hours)}" for i in range(len(secs) - 1)
             if secs[i + 1] - secs[i] < 10]
    if short:
        warnings.append("10秒未満の間隔があります(YouTube でチャプターとして無効になります): " + ", ".join(short))
    for w in warnings:
        print(f"# 警告: {w}", file=sys.stderr)

    for t, lab, note in lines:
        extra = f"   [{note}]" if a.debug and note else ""
        print(f"{fmt(t, use_hours)} {lab}{extra}")


if __name__ == "__main__":
    main()
