"""説明テロップの文を EC の説明文に寄せる（スキル shiun-telop-explain-source）。

    from telop_text import ExplainSource, load_script
    script = load_script(PATH_TO_台本.md)  # {商品名: [文, ...]}
    src = ExplainSource(product, script.get(product['name']))
    text = src.rewrite(text)              # 発言の要約 → 台本の文 → EC の文（一致が低ければそのまま）

決まり（A24 の修正版との比較で分かったもの。次の回でも同じ）:
- 材料の順: 台本（ユーザー: 「基本テロップは台本から取ってる」）→ EC の説明文（design / material・plan の lines）→ 発言の要約。
  台本の文はできるだけそのまま使う。どの文をどの発言の所に出すかは、発言（の要約）との一致で決める。
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
# 発言の要約をテロップにするときの言い換え（修正版の書き方。スキル shiun-telop-explain-source の辞書）
SPOKEN = [('を使用', 'を採用'), ('使用', '採用'), ('若干', 'やや'), ('少しだけ', '程よい'), ('真ん中部分', 'アウトソールの中央'),
          ('周り', 'まわり'), ('頃', 'ごろ'), ('サンドトープ', 'SAND TAUPE')]
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


def load_script(path):
    """台本（Markdown）を商品ごとの文の並びにする。見出し「## 商品名 ¥価格（読み）」、本文は箇条書き。
    色・素材の混率・寸法・価格の行は説明の文ではないので外す。「デザイン:」「素材:」の頭は落とす。"""
    out, cur = {}, None
    try:
        lines = open(path, encoding='utf-8').read().split('\n')
    except OSError:
        return out
    for ln in lines:
        m = re.match(r'^##\s+(.+?)\s+¥', ln)
        if m:
            cur = m.group(1).strip()
            out[cur] = []
            continue
        if cur is None or not ln.startswith('- '):
            continue
        t = ln[2:].strip()
        if re.match(r'^(Color|Material|Size|着丈|ウエスト|¥)', t):
            continue
        t = re.sub(r'^(デザイン|素材|Design|Material)\s*[:：]\s*', '', t)
        out[cur].append(t)
    return out


def candidates(product, texts=None):
    """説明の文を、文と「読点で区切った連続する節」に分ける。texts が無ければ EC の説明文と plan の lines。"""
    out = []
    if texts is None:
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
                    # 「AをBにすることで」の B（名詞句）も候補にする（例: シルエットを「イタリアンローファーのようなシャープで上品なシルエット」にすることで）
                    m = re.search(r'を(.{8,}?)にすることで', c)
                    if m and j == i + 1:
                        out.append((sent, m.group(1)))
    return out


class ExplainSource:
    def __init__(self, product, script=None):
        self.pools = [candidates(product or {}, script)] if script else []
        self.pools.append(candidates(product or {}))
        self.used = set()

    def best(self, text, pool):
        t = _n(text)
        best = (0.0, None, None)
        for sent, c in pool:
            if any(sent == s0 and (c in c0 or c0 in c) for s0, c0 in self.used):
                continue
            r = SequenceMatcher(None, t, _n(tidy(c))).ratio()
            if r > best[0]:
                best = (r, sent, c)
        return best

    def rewrite(self, text):
        # 台本 → EC の順。台本には 0.1 の上乗せをして、一番よく合う文を使う（台本を第一に、でも合わない文は使わない）
        best = None
        for k, pool in enumerate(self.pools):
            r, sent, c = self.best(text, pool)
            if c is None or r < THRESH:
                continue
            sc = r + (0.1 if k == 0 and len(self.pools) > 1 else 0)
            if best is None or sc > best[0]:
                best = (sc, sent, c)
        if best is None:
            # 材料に無い文は発言の要約のまま。ただし書き方（語の言い換え・「。」なし）は修正版にそろえる
            t = text.rstrip('。')
            for a, b in SPOKEN:
                t = t.replace(a, b)
            return re.sub(r'(\d+)ゲージ', r'\1G', t)
        self.used.add((best[1], best[2]))
        return tidy(best[2])
