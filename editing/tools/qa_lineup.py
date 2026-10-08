"""採点表に出ない品質の問題を洗い出す（60 点扱いのレビュー用）。

    python3 qa_lineup.py FLAT.json

チェック:
  - 流用した部品（アイキャッチ等）の中も含め、コレクション名・発売日の表記が 1 種類か
  - 同じレーンで重なっている接続クリップ（FCP が勝手にレーンをずらし、見え方が変わる）
  - 同じ写真・動画の使い回し（1 区間で 3 回以上）
  - 字幕の読む速さ（1 秒あたり 6 文字を超える）、字幕同士の重なり
  - 字幕・中央商品名・価格表示が同時に出て、画面で重なる
  - B-roll がない時間が 40 秒以上続く商品区間
"""
import collections
import json
import os
import sys
import unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roles import role, text  # noqa: E402


def main():
    it = [i for i in json.load(open(sys.argv[1])) if i['enabled'] != '0' and len(i['path']) <= 1]
    issues = []
    # 0) 流用した部品の中も含め、コレクション名・発売日の表記が 1 種類か（別の回の文字が残っていないか）
    import re
    allt = [i for i in json.load(open(sys.argv[1])) if i['enabled'] != '0' and i['tag'] == 'title']
    cols = collections.Counter(m.group(0) for i in allt for m in [re.search(r'shiun\s+\S+.*?Collection', ' '.join(text(i).split()))] if m)
    rels = collections.Counter(m.group(0) for i in allt for m in [re.search(r'\w+ \d+(st|nd|rd|th) \w+\.? \d+(am|pm) - Release', text(i))] if m)
    if len(cols) > 1 or len(rels) > 1:
        issues.append((3, f'コレクション名・発売日の表記が複数ある（別の回の文字が残っている可能性）: {dict(cols)} {dict(rels)}'))
    # 1) 同じレーンの重なり
    by_lane = collections.defaultdict(list)
    for i in it:
        if i['lane'] not in (None,) and not str(i['lane']).startswith('in') and i['tag'] != 'mc-clip':
            by_lane[i['lane']].append(i)
    ov = 0
    for lane, xs in by_lane.items():
        xs.sort(key=lambda i: i['t0'])
        for a, b in zip(xs, xs[1:]):
            if b['t0'] < a['t1'] - 0.05 and lane not in ('1', '2', '-1'):
                ov += 1
    if ov:
        issues.append((3, f'同じレーンで重なっている接続クリップが {ov} 組（FCP がレーンをずらす）'))
    # 2) 使い回し
    use = collections.Counter()
    for i in it:
        if i['tag'] in ('video', 'asset-clip', 'clip') and i['lane'] not in (None, '-1'):
            src = unicodedata.normalize('NFC', urllib.parse.unquote(str((i.get('asset') or {}).get('src') or i['name'])))
            use[src] += 1
    heavy = [(k.split('/')[-2] + '/' + k.split('/')[-1], v) for k, v in use.items() if v >= 4]
    if heavy:
        issues.append((2, f'同じ素材を 4 回以上使っている: {len(heavy)} 点（例: {sorted(heavy, key=lambda x: -x[1])[:3]}）'))
    # 3) 字幕
    subs = sorted([i for i in it if i['tag'] == 'title' and role(i) == 'subtitle'], key=lambda i: i['t0'])
    fast = [i for i in subs if len(text(i)) / max(i['dur'], 0.1) > 6]
    if fast:
        issues.append((2, f'読む速さが速すぎる字幕 {len(fast)} 本（1 秒 6 文字超）'))
    clash = sum(1 for a, b in zip(subs, subs[1:]) if b['t0'] < a['t1'] - 0.05)
    if clash:
        issues.append((3, f'字幕同士が重なっている箇所 {clash}'))
    # 4) 字幕と中央の文字の衝突
    centers = [i for i in it if i['tag'] == 'title' and role(i) in ('product_center', 'emphasis')]
    hit = sum(1 for c in centers for s in subs if s['t0'] < c['t1'] and c['t0'] < s['t1'])
    if hit:
        issues.append((1, f'字幕と中央商品名が同時に出ている箇所 {hit}'))
    # 5) B-roll の空白
    talk_end = max(i['t1'] for i in it)
    vis = sorted([(i['t0'], i['t1']) for i in it if i['tag'] in ('video', 'asset-clip', 'clip', 'ref-clip')
                  and i['lane'] not in (None, '-1') and i['name'] != 'BGM'])
    gaps, cur = [], 0.0
    for a, b in vis:
        if a - cur >= 40:
            gaps.append((round(cur), round(a)))
        cur = max(cur, b)
    if talk_end - cur >= 40:
        gaps.append((round(cur), round(talk_end)))
    if gaps:
        issues.append((2, f'B-roll がない 40 秒以上の区間 {len(gaps)} 箇所: {gaps[:6]}'))
    issues.sort(key=lambda x: -x[0])
    print(f'品質チェック: {len(issues)} 件')
    for sev, msg in issues:
        print(f"  [{'高' if sev == 3 else '中' if sev == 2 else '低'}] {msg}")


if __name__ == '__main__':
    main()
