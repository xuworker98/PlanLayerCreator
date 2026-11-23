"""
bd09.py — BD-09（百度坐标）与 GCJ-02 互转

BD-09 = 百度地图使用的坐标系，在 GCJ-02 上叠加极坐标偏移。
转换公式公开，双向可逆。
"""

import math
from .constants import X_PI


def gcj02_to_bd09(lng: float, lat: float) -> tuple[float, float]:
    """
    GCJ-02 → BD-09 正向转换。

    参数:
        lng: GCJ-02 经度
        lat: GCJ-02 纬度
    返回:
        (bd09_lng, bd09_lat)
    """
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * X_PI)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * X_PI)
    return z * math.cos(theta) + 0.0065, z * math.sin(theta) + 0.006


def bd09_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """
    BD-09 → GCJ-02 逆向转换。

    参数:
        lng: BD-09 经度
        lat: BD-09 纬度
    返回:
        (gcj02_lng, gcj02_lat)
    """
    x = lng - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * X_PI)
    return z * math.cos(theta), z * math.sin(theta)
