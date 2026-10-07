"""FCPXML を組み立てるときの共通処理。"""
import xml.etree.ElementTree as ET

# 接続クリップより後ろに来なければならない子要素（DTD の並び順）
_AFTER_ANCHORS = {'marker', 'chapter-marker', 'rating', 'keyword', 'analysis-marker', 'hidden-clip-marker',
                  'filter-audio', 'metadata', 'filter-video'}
_ANCHOR_TAGS = {'audio', 'video', 'clip', 'title', 'caption', 'mc-clip', 'ref-clip', 'sync-clip', 'asset-clip',
                'audition', 'spine', 'live-drawing', 'gap'}


def append_anchor(parent, el):
    """接続クリップを、DTD の順番（マーカーやフィルタより前）を守って追加する。"""
    kids = list(parent)
    idx = len(kids)
    for k, ch in enumerate(kids):
        if ch.tag in _AFTER_ANCHORS:
            idx = k
            break
    # video/asset-clip/ref-clip などでは filter-video は接続クリップより後ろ、マーカーより後ろ
    parent.insert(idx, el)
    return el
