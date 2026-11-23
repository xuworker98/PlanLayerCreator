# -*- coding: utf-8 -*-
"""WKT 几何文本解析器"""
from shapely import wkt


def parse_wkt(wkt_text):
    """解析 WKT 文本，返回 Shapely geometry 对象"""
    if not wkt_text or not isinstance(wkt_text, str):
        return None
    text = wkt_text.strip()
    if not text:
        return None
    try:
        return wkt.loads(text)
    except Exception:
        return None


def parse_wkt_multi(wkt_series):
    """批量解析 WKT 列，返回 geometry 列表"""
    result = []
    for wt in wkt_series:
        geom = parse_wkt(str(wt))
        result.append(geom)
    return result
