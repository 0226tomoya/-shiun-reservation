"""元の PSD にレイヤーを足して、Photoshop で開ける形で保存する共通の道具（shiun-thumb-psd-export の決まりをまとめたもの）。
    from psd_edit import Editor
    ed = Editor('src.psd'); lay = ed.add(img, 'レイヤー名', before=ed.find('名前'))  # img はキャンバス大の RGBA（中身の範囲に切って入れる）
    ed.save('out.psd')
- 足すレイヤーは fromarray（透明度付き・マスク無し）、レイヤー ID は全レコードの最大の次から
- 保存したあと、全体のタグブロック（スマートオブジェクトの埋め込みデータ lnk2 など）を元のバイトに戻す"""
import struct
import numpy as np
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from psd_tools.constants import Tag


def _global_blocks(b):
    o = 26; o += 4 + struct.unpack('>I', b[o:o + 4])[0]; o += 4 + struct.unpack('>I', b[o:o + 4])[0]
    lm_end = o + 4 + struct.unpack('>I', b[o:o + 4])[0]
    q = o + 8 + struct.unpack('>I', b[o + 4:o + 8])[0]
    q += 4 + struct.unpack('>I', b[q:q + 4])[0]
    return o, q, lm_end


class Editor:
    def __init__(self, src):
        self.src = src; self.p = PSDImage.open(src)
        recs = self.p._record.layer_and_mask_information.layer_info.layer_records
        self._ids = iter(range(max(r.tagged_blocks.get_data(Tag.LAYER_ID, 0) for r in recs) + 1, 10 ** 6))
        self.root = self.p[0] if len(self.p) == 1 and self.p[0].is_group() else self.p

    def find(self, name, group=None):
        for l in (group or self.root).descendants():
            if l.name == name: return l
        raise KeyError(name)

    def layer(self, img, name, top=0, left=0):
        lay = PixelLayer.fromarray(np.asarray(img.convert('RGBA')), self.p, 'Layer', top=top, left=left)
        lay.name = name; lay._record.name = 'Layer'
        lay._record.tagged_blocks.set_data(Tag.LAYER_ID, next(self._ids))
        return lay

    def add(self, img, name, before=None, after=None, group=None, blend=None, opacity=255):
        """img はキャンバス大。中身の範囲に切って、before の下（after なら上）に入れる。どちらも無ければ一番上"""
        bb = img.getbbox()
        lay = self.layer(img.crop(bb), name, bb[1], bb[0])
        if blend: lay.blend_mode = blend
        lay.opacity = opacity
        tgt = before or after
        g = tgt.parent if tgt is not None else (group or self.root)
        if tgt is None: g.append(lay)
        else: g.insert(g.index(tgt) + (1 if after is not None else 0), lay)
        return lay

    def save(self, out):
        self.p.save(out)
        src, new = open(self.src, 'rb').read(), open(out, 'rb').read()
        so, sq, se = _global_blocks(src); no, nq, ne = _global_blocks(new)
        body = new[no + 4:nq] + src[sq:se]
        open(out, 'wb').write(new[:no] + struct.pack('>I', len(body)) + body + new[ne:])
        # 確かめ: ID の重なり・マスク
        q = PSDImage.open(out); recs = q._record.layer_and_mask_information.layer_info.layer_records
        ids = [r.tagged_blocks.get_data(Tag.LAYER_ID) for r in recs]
        assert len(ids) == len(set(ids)), 'レイヤー ID が重なっている'
        return q
