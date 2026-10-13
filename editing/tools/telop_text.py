"""説明テロップの文を EC の説明文に寄せる（スキル shiun-telop-explain-source）。

    from telop_text import ExplainSource
    src = ExplainSource(product)          # plan の products の 1 件（design / material / lines）
    text = src.rewrite(text)              # 発言の要約 → EC の文（一致が低ければそのまま）

決まり（A24 の修正版との比較で分かったもの。次の回でも同じ）:
- 材料の順: EC の説明文（design / material）→ 台本（lines）→ 発言の要約。
- 要約と EC の文（文・読点で区切った連続する節）の一致が 0.35 以上なら EC の文を使う。
- 1 枚に 1 つの仕様。同じ EC の節は 2 回使わない（使った節と重なる節は候補から外す）。
- 節で切るときは、文として終わっている所で切る（「〜ので」「〜ため」「〜ことで」で止めない）。
- 語尾: 「。」と「です」を付けない。文頭のつなぎ言葉（さらに・ただ・また）は落とす。
- 表記の辞書（下の DICT）を当てる。
"""
import re
import unicodedata
from difflib import SequenceMatcher

DICT = [
    ('衿', '襟'), ('すっきり', 'スッキリ'), ('頃', 'ごろ'), ('周り', 'まわり'),
    ('機能素材', '機能性素材'), ('サンドトープ', 'SAND TAUPE'),
]
LEAD = ('さらに、', 'さらに', 'ただ、', 'また、', 'そして、', 'なので、', '今回は')
THRESH = 0.35
# 節の切れ目で文が終わっていない（「〜ので」「〜ため」「〜ことで」で止まる）候補は使わない
DANGLING = ('ので', 'ため', 'ことで', 'ながら', 'が', 'て', 'し', 'り', 'ず', 'え', 'き', 'れ', 'く', 'でも', 'けど', 'から', 'に対して')


def _n(t):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', t or ''))


def tidy(t):
    """EC の文をテロップの書き方に直す。"""
    t = t.strip()
    for a in LEAD:
        if t.startswith(a) and len(t) > len(a) + 8:
            t = t[len(a):]
            break
    t = t.rstrip('。．.')
    if t.endswith('です'):
        t = t[:-2]
    t = t.rstrip('、')
    t = re.sub(r'(\d+)ゲージ', r'\1G', t)
    for a, b in DICT:
        t = t.replace(a, b)
    return t


def candidates(product):
    """EC の説明文・台本を、文と「読点で区切った連続する節」に分ける。"""
    out = []
    texts = [product.get('design') or '', product.get('material') or '']
    texts += [l[1] for l in (product.get('lines') or []) if len(l) > 1]
    for body in texts:
        for sent in re.split(r'(?<=[。])', body):
            sent = sent.strip()
            if not sent:
                continue
            parts = [p for p in re.split(r'(?<=、)', sent) if p]
            for i in range(len(parts)):
                for j in range(i + 1, len(parts) + 1):
                    c = ''.join(parts[i:j])
                    if len(_n(c)) >= 8 and not tidy(c).endswith(DANGLING):
                        out.append((sent, c))
    return out


class ExplainSource:
    def __init__(self, product):
        self.cands = candidates(product or {})
        self.used = set()

    def best(self, text):
        t = _n(text)
        best = (0.0, None, None)
        for sent, c in self.cands:
            if any(sent == s0 and (c in c0 or c0 in c) for s0, c0 in self.used):
                continue
            r = SequenceMatcher(None, t, _n(tidy(c))).ratio()
            if r > best[0]:
                best = (r, sent, c)
        return best

    def rewrite(self, text):
        r, sent, c = self.best(text)
        if c is None or r < THRESH:
            return text
        self.used.add((sent, c))
        return tidy(c)
