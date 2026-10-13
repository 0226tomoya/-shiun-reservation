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


def collect_markers(spine):
    """タイムライン上で実際に見えている (クリップの使用範囲内の) マーカーを返す。"""
    found = []

    def walk(el, parent_tl0, parent_start):
        for c in el:
            if c.tag == "spine":
                walk(c, parent_tl0 + (parse_time(c.get("offset")) - parent_start), Fraction(0))
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
            walk(c, tl0, start)

    walk(spine, Fraction(0), Fraction(0))
    found.sort()
    # 同じ秒に重なったピンは1つにまとめる
    dedup = []
    for item in found:
        if not dedup or int(item[0]) != int(dedup[-1][0]):
            dedup.append(item)
    return dedup


def fmt(t, use_hours):
    s = int(t)  # 秒未満は切り捨て
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if use_hours else f"{m:02d}:{sec:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--label", default="{n}人目", help="各ピンの見出し。{n} が通し番号になる")
    ap.add_argument("--project", help="プロジェクト名 (複数ある場合)")
    ap.add_argument("--no-op", action="store_true", help="先頭の 00:00 OP を付けない")
    ap.add_argument("--no-ed", action="store_true", help="最後のピンを ED にしない")
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
        print("複数のプロジェクトがあります。先頭を使います: "
              + ", ".join(p.get("name") for p in projects), file=sys.stderr)
    proj = projects[0]
    seq = proj.find("sequence")
    total = parse_time(seq.get("duration"))
    markers = collect_markers(seq.find("spine"))
    use_hours = total >= 3600

    print(f"# project: {proj.get('name')} / 全長 {fmt(total, use_hours)} / ピン {len(markers)} 個",
          file=sys.stderr)

    lines = []
    if not a.no_op and (not markers or int(markers[0][0]) > 0):
        lines.append((Fraction(0), "OP", None, None))
    body = markers if a.no_ed else markers[:-1]
    for i, (t, v, c) in enumerate(body, 1):
        lines.append((t, a.label.format(n=i), v, c))
    if not a.no_ed and markers:
        t, v, c = markers[-1]
        lines.append((t, "ED", v, c))

    for t, label, v, c in lines:
        extra = f"   [{v} / {c}]" if a.debug and v else ""
        print(f"{fmt(t, use_hours)} {label}{extra}")


if __name__ == "__main__":
    main()
