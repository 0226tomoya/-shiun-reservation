"""テロップの文字の検査（Slack #わむう_sns で 1 年に 8 本以上指摘された「文字化け」＝ローマ字入力の打ち残し）。

    python3 audit_telop_text.py X.fcpxml

見るもの:
  - 日本語に接した小文字の半角英字 1〜2 文字（例「履きやすいし、s」「k若干キツい」「テーパードn効いた」「使用すr」）
  - 半角英字だけの 1〜2 文字のテロップ（例「s」「t」）
  - 全角と半角の混ざった英数字（例「２0cm」）
単位（cm・kg・mm・g）と、大文字のサイズ表記（S・M・XS・Vネック・Uチップ など）は対象外。
"""
import re
import sys
import xml.etree.ElementTree as ET

JP = r'[぀-ヿ㐀-鿿ｦ-ﾟ、。・ー「」]'
UNITS = {'cm', 'kg', 'mm', 'g', 'm'}


def problems(s):
    out = []
    t = s.replace('\n', '')
    if re.fullmatch(r'[A-Za-z]{1,2}', t.strip()) and t.strip() not in ('S', 'M', 'L', 'XS', 'XL'):
        out.append('英字だけの短いテロップ')
    for m in re.finditer(r'[a-z]{1,2}', t):
        w = m.group()
        a, b = t[m.start() - 1] if m.start() else '', t[m.end()] if m.end() < len(t) else ''
        if w in UNITS and re.match(r'[0-9０-９.]', a or ''):
            continue
        if re.match(r'[A-Za-z]', a or '') or re.match(r'[A-Za-z]', b or ''):
            continue  # 英単語の一部
        if re.match(JP, a or '') or re.match(JP, b or '') or not a or not b:
            out.append(f'打ち残しの疑い「{t[max(0, m.start() - 6):m.end() + 6]}」')
    if re.search(r'[0-9][０-９]|[０-９][0-9]', t):
        out.append('全角と半角の数字が混ざっている')
    return out


def main():
    root = ET.parse(sys.argv[1]).getroot()
    n = bad = 0
    for ti in root.iter('title'):
        s = ''.join(''.join(x.itertext()) for x in ti.findall('text'))
        if not s.strip():
            continue
        n += 1
        for p in problems(s):
            bad += 1
            print(f'  {ti.get("name", "")[:30]} @ {ti.get("offset")}: {p}')
    print(f'テロップの文字: {n} 枚を検査、問題 {bad}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
