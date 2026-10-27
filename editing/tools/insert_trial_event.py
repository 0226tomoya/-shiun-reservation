"""試着会の感想（別の回の完成編集）から人を選び、商品パートの後に差し込む（スキル shiun-trial-event-insert）。
apply_overrides.py の後に使う（上書きの時刻は差し込む前のタイムラインなので）。

    python3 insert_trial_event.py IN.fcpxml PLAN.json OUT.fcpxml

plan.trial_event:
  fcpxml   … 試着会の動画の完成 XML（plan からの相対パス）。カットは編集者の切り方のまま使う
  product  … 差し込む商品のチャプター（その次のチャプターの前のアイキャッチの後ろに入れる）
  seconds_per_person … 1 人の目安の長さ（既定 33 秒。スキルの「1 人 25〜35 秒」）
決まり:
  - 人の区切りは、試着会の XML の本線のアイキャッチ。その人の右上のサイズラベル（「NN サイズ着用」）からサイズを読む。
  - 1 サイズ 1 人。同じサイズの人が何人もいたら、感想の字幕（タイプライター）がいちばん多い人。サイズの小さい順に並べる。
  - 1 人の範囲は、サイズラベルが出る 2 秒前に近いカットの頭から、25〜35 秒に収まる字幕の終わりのうち目安の長さにいちばん近いもの
    （無ければ全体でいちばん近いもの）のカットまで。
  - カット（音のフェード・回転・色）、字幕、サイズラベルは試着会の XML のまま移す。音（BGM・効果音）と動画のタイトルの複合（どの人にも出ているもの）は移さない。
  - 前後にアイキャッチ（1.5 秒）。その商品の価格つきのクレジット（左上）を試着会の間も出す。
  - 差し込みをまたぐ BGM は差し込んだ分だけ長くする（音量の変化も後ろへ）。
  文字起こし（transcript_cut）は v1 の時刻のままでよい（audit_inserts がマルチカムの素材の時刻で写すので、ずらすと二重になる）。
"""
import copy
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_lineup import Donor  # noqa: E402
from fcpxml_util import append_anchor  # noqa: E402
from insert_size_compare import S, T, txt  # noqa: E402

EYECATCH_SEC = Fraction(3, 2)
LEAD = Fraction(2)


def junk(s):
    """打ち損じの字幕（「h」「あ」だけなど）。"""
    s = s.strip()
    return len(s) <= 1 or re.fullmatch(r'[A-Za-z]+', s) is not None


def read_people(d):
    """試着会の XML の本線から、人ごとのカット・字幕・サイズラベルを読む。時刻は試着会のタイムライン。"""
    p = next(d.root.iter('project'))
    spine = p.find('sequence/spine')
    cuts, conn, eyes = [], [], []
    for e in spine:
        st, off = T(e.get('start')), T(e.get('offset'))
        a, b = off, off + T(e.get('duration'))
        if e.tag == 'mc-clip':
            cuts.append((a, b, e))
        elif 'アイキャッチ' in (e.get('name') or ''):
            eyes.append((a, b))
        for c in e:
            if c.get('lane') and c.get('offset') is not None:
                c0 = off + T(c.get('offset')) - st
                conn.append((c0, c0 + T(c.get('duration')), c))
    # どの人にも出ている複合（動画のタイトル）は移さない
    ref_count = {}
    for _, _, c in conn:
        if c.tag == 'ref-clip':
            ref_count[c.get('ref')] = ref_count.get(c.get('ref'), 0) + 1
    title_refs = {r for r, n in ref_count.items() if n >= max(3, len(eyes) // 2)}
    people = []
    for (_, e0), (e1, _) in zip(eyes, eyes[1:]):
        lab = [(a, b, c) for a, b, c in conn if c.tag == 'ref-clip' and c.get('ref') not in title_refs and e0 <= a < e1]
        size = None
        for _, _, c in lab:
            m = re.search(r'(\d+)サイズ着用', ' '.join(txt(t) for t in d.res[c.get('ref')].iter('title')))
            if m:
                size = int(m.group(1))
                break
        if size is None:
            continue
        tw = [(a, b, c) for a, b, c in conn if c.tag == 'title' and e0 <= a < e1 and int(c.get('lane')) > 0
              and 'タイプライター' in (d.res[c.get('ref')].get('name') or '') and not junk(txt(c))]
        people.append({'size': size, 't0': e0, 't1': e1, 'label_at': min(a for a, _, _ in lab),
                       'cuts': [x for x in cuts if e0 <= x[0] < e1],
                       'conn': [x for x in conn if int(x[2].get('lane')) > 0 and x[2].get('ref') not in title_refs
                                and e0 <= x[0] < e1 and not (x[2].tag == 'title' and junk(txt(x[2])))],
                       'n_comments': len(tw), 'comments': tw})
    return people


def choose(people, per):
    best = {}
    for pp in people:
        if pp['size'] not in best or pp['n_comments'] > best[pp['size']]['n_comments']:
            best[pp['size']] = pp
    out = []
    for size in sorted(best):
        pp = best[size]
        heads = [a for a, _, _ in pp['cuts'] if a >= pp['t0']]
        start = min(heads, key=lambda a: abs(a - (pp['label_at'] - LEAD)))
        ends = sorted(b for a, b, _ in pp['comments'] if a >= start)
        fit = [b for b in ends if 25 <= b - start <= 35] or ends
        want = min(fit, key=lambda b: abs(b - start - per)) if fit else pp['t1']
        end = next((b for a, b, _ in pp['cuts'] if a < want <= b), pp['cuts'][-1][1])
        out.append(dict(pp, start=start, end=end))
    return out


def write(root, out):
    with open(out, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding='utf-8'))


def main():
    src, plan_path, out = sys.argv[1:4]
    plan = json.load(open(plan_path, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(plan_path))
    te = plan.get('trial_event')
    tree = ET.parse(src)
    root = tree.getroot()
    if not te:
        write(root, out)
        print('試着会: なし（plan.trial_event が null）')
        return
    resources = root.find('resources')
    project = [p for p in root.iter('project') if p.get('name') == plan.get('project', '本編')][0]
    seq = project.find('sequence')
    spine = seq.find('spine')
    fd = T(next(e for e in resources if e.get('id') == seq.get('format')).get('frameDuration'))
    EYECATCH = round(EYECATCH_SEC / fd) * fd  # フレームの格子に乗せる（59.94p なら 90 コマ）
    d = Donor(os.path.join(base, te['fcpxml']), 'tr_', resources)
    per = Fraction(str(te.get('seconds_per_person', 33)))
    chosen = choose(read_people(d), per)

    # ---- 差し込み位置: 商品の次のチャプターの前のアイキャッチ ----
    items = list(spine)
    starts, cur = [], Fraction(0)
    for e in items:
        starts.append(cur)
        cur += T(e.get('duration'))
    chapters = [(k, m.get('value')) for k, e in enumerate(items) for m in e.findall('chapter-marker')]
    ci = next(i for i, (_, v) in enumerate(chapters) if v == te['product'])
    nxt = chapters[ci + 1][0]
    eye_k = nxt - 1
    eye = items[eye_k]
    assert eye.tag == 'ref-clip' and 'アイキャッチ' in (eye.get('name') or ''), eye.get('name')
    old_eye = T(eye.get('duration'))
    eye.set('duration', S(EYECATCH))
    at = starts[eye_k] + EYECATCH  # 試着会の頭（新しいタイムライン）

    # ---- 試着会のカットを並べる ----
    block, runs, t = [], [], at  # runs: (試着会の時刻 a, b, 新しい時刻)
    for pp in chosen:
        for a, b, e in pp['cuts']:
            if a < pp['start'] or b > pp['end']:
                continue
            c = d.element(e)
            for ch in list(c):
                # 接続クリップは後で付け直す。マーカー（A27 の作業用・未完了の ToDo）は持ち込まない
                if ch.get('lane') or ch.tag in ('marker', 'chapter-marker', 'rating', 'keyword'):
                    c.remove(ch)
            c.set('offset', S(t))
            block.append(c)
            runs.append((a, b, t, c))
            t += b - a
    # 字幕・サイズラベル: 頭が使うカットに入っているものを、続いて使っている所まで
    n_tw = 0
    for pp in chosen:
        for a, b, x in pp['conn']:
            k = next((k for k, (ra, rb, _, _) in enumerate(runs) if ra <= a < rb), None)
            if k is None:
                continue
            j = k
            while j + 1 < len(runs) and runs[j + 1][0] == runs[j][1] and runs[j][1] < b:
                j += 1
            end = min(b, runs[j][1])
            ra, _, rt, parent = runs[k]
            c = d.element(x)
            c.set('offset', S(T(parent.get('start')) + a - ra))
            c.set('duration', S(end - a))
            append_anchor(parent, c)
            n_tw += x.tag == 'title'
    total = t - at
    eye2 = copy.deepcopy(eye)
    eye2.set('offset', S(t))
    dur_add = total + EYECATCH + EYECATCH - old_eye

    # ---- 商品の価格つきクレジットを試着会の間も出す ----
    name = next(p['name'] for p in plan['products'] if p['chapter'] == te['product'])
    cred = None
    for e in items[chapters[ci][0]:eye_k]:
        for c in e:
            if c.tag == 'title' and (c.get('name') or '').startswith('product_label') and txt(c).startswith(name) and '¥' in txt(c):
                cred = c
    if cred is not None and block:
        c = copy.deepcopy(cred)
        # 書式 ID は複製ごとに変える（同じ ID が 2 つあると FCP で読み込めない）
        for sd in c.iter('text-style-def'):
            sd.set('id', sd.get('id') + '_tr')
        for ts in c.iter('text-style'):
            if ts.get('ref'):
                ts.set('ref', ts.get('ref') + '_tr')
        c.set('offset', block[0].get('start'))
        c.set('duration', S(total))
        append_anchor(block[0], c)

    # ---- スパインに入れて後ろをずらす ----
    shift = dur_add
    new_items = items[:eye_k + 1] + block + [eye2] + items[eye_k + 1:]
    for e in list(spine):
        spine.remove(e)
    cur = Fraction(0)
    for e in new_items:
        e.set('offset', S(cur))
        spine.append(e)
        cur += T(e.get('duration'))
    seq.set('duration', S(cur))

    # ---- アイキャッチより前から始まり差し込み位置をまたぐ接続クリップ ----
    cut_at = starts[eye_k] + EYECATCH
    n_bgm = n_trim = 0
    for e, st in zip(items[:eye_k + 1], starts[:eye_k + 1]):
        for c in list(e):
            if c.get('lane') is None or c.get('offset') is None:
                continue
            a0 = st + T(c.get('offset')) - T(e.get('start'))
            a1 = a0 + T(c.get('duration'))
            if not a0 < cut_at < a1:
                continue
            if int(c.get('lane')) < 0:
                c.set('duration', S(T(c.get('duration')) + shift))
                cs = T(c.get('start'))
                for kf in c.iter('keyframe'):
                    kt = T(kf.get('time'))
                    if a0 + kt - cs >= cut_at:
                        kf.set('time', S(kt + shift))
                m = next((r for r in resources if r.get('id') == c.get('ref')), None)
                if m is not None and m.tag == 'media':
                    assert T(m.find('sequence').get('duration')) >= cs + T(c.get('duration')), f"BGM の素材が足りない: {c.get('name')}"
                n_bgm += 1
            else:
                c.set('duration', S(cut_at - a0))
                n_trim += 1

    write(root, out)
    for pp in chosen:
        print(f"  {pp['size']} サイズ: 試着会の {float(pp['start']):.1f}〜{float(pp['end']):.1f} 秒（{float(pp['end'] - pp['start']):.1f} 秒・字幕 {pp['n_comments']} 本）")
    print('試着会:', len(chosen), '人', len(block), 'カット', round(float(total), 2), '秒 | 字幕・ラベル', n_tw,
          '| 差し込み位置', round(float(at), 2), '| BGM 延長', n_bgm, '| 位置で終えた要素', n_trim, '->', out)


if __name__ == '__main__':
    main()
