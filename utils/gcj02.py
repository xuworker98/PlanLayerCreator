"""
gcj02.py — GCJ-02（火星坐标）与 WGS84 互转

纯 Python 实现，基于公开的逆向工程算法。
不依赖任何 C 扩展或外部库。

算法来源：学术界对 GCJ-02 偏移函数的逆向分析。
使用克拉索夫斯基椭球参数（1940）。
"""

import math
from .constants import (
    PI,
    KRASOVSKY_A,
    KRASOVSKY_EE,
    CHINA_LNG_MIN,
    CHINA_LNG_MAX,
    CHINA_LAT_MIN,
    CHINA_LAT_MAX,
)


def _is_outside_china(lng: float, lat: float) -> bool:
    """
    判断坐标是否在中国境外。
    GCJ-02 加密仅在中国大陆境内生效，境外不做偏移。
    """
    return not (
        CHINA_LNG_MIN <= lng <= CHINA_LNG_MAX
        and CHINA_LAT_MIN <= lat <= CHINA_LAT_MAX
    )


def _transform_lat(x: float, y: float) -> float:
    """
    纬度偏移分量计算（多项式 + 三角函数拟合）。
    
    参数:
        x: 经度偏移 (lng - 105.0)
        y: 纬度偏移 (lat - 35.0)
    返回:
        纬度方向的偏移量（未缩放）
    """
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y
    ret += 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * PI) + 320.0 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x: float, y: float) -> float:
    """
    经度偏移分量计算（多项式 + 三角函数拟合）。
    
    参数:
        x: 经度偏移 (lng - 105.0)
        y: 纬度偏移 (lat - 35.0)
    返回:
        经度方向的偏移量（未缩放）
    """
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x
    ret += 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 30.0 * PI)) * 2.0 / 3.0
    return ret


def _delta(lng: float, lat: float) -> tuple[float, float]:
    """
    计算 GCJ-02 偏移量 (delta_lng, delta_lat)。
    
    这是 GCJ-02 算法的核心：给定 WGS84 坐标，计算需要叠加的偏移量。
    使用克拉索夫斯基椭球参数进行缩放。
    
    返回:
        (dlng_deg, dlat_deg) — 以度为单位
    """
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)

    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - KRASOVSKY_EE * magic * magic
    sqrtmagic = math.sqrt(magic)

    dlat_deg = (dlat * 180.0) / ((KRASOVSKY_A * (1 - KRASOVSKY_EE)) / (magic * sqrtmagic) * PI)
    dlng_deg = (dlng * 180.0) / (KRASOVSKY_A / sqrtmagic * math.cos(radlat) * PI)

    return dlng_deg, dlat_deg


def wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """
    WGS84 → GCJ-02 正向转换（精确，无迭代）。
    
    参数:
        lng: WGS84 经度
        lat: WGS84 纬度
    返回:
        (gcj02_lng, gcj02_lat)
    
    注意：中国境外坐标原样返回，不做偏移。
    """
    if _is_outside_china(lng, lat):
        return lng, lat

    dlng, dlat = _delta(lng, lat)
    return lng + dlng, lat + dlat


def gcj02_to_wgs84(lng: float, lat: float, max_iterations: int = 30) -> tuple[float, float]:
    """
    GCJ-02 → WGS84 逆向转换（二分迭代逼近法）。
    
    由于 GCJ-02 偏移函数是非线性且不可逆的，无法解析求逆。
    采用牛顿-拉夫逊风格的迭代法：
        1. 以输入坐标作为 WGS84 的初始猜测
        2. 将猜测值正向转换为 GCJ-02
        3. 计算猜测结果与输入的误差
        4. 用误差修正猜测值
        5. 重复直到收敛
    
    参数:
        lng:     GCJ-02 经度
        lat:     GCJ-02 纬度
        max_iterations: 最大迭代次数（默认 30，通常 5-10 次即收敛）
    返回:
        (wgs84_lng, wgs84_lat)
    
    收敛精度：< 1e-8 度（约 1 毫米），或 max_iterations 次后强制退出。
    """
    if _is_outside_china(lng, lat):
        return lng, lat

    # 初始猜测：直接用输入值（GCJ-02 偏移量最多几百米）
    wgs_lng, wgs_lat = lng, lat

    for _ in range(max_iterations):
        guess_lng, guess_lat = wgs84_to_gcj02(wgs_lng, wgs_lat)
        delta_lng = guess_lng - lng
        delta_lat = guess_lat - lat

        if abs(delta_lng) < 1e-8 and abs(delta_lat) < 1e-8:
            break

        wgs_lng -= delta_lng
        wgs_lat -= delta_lat

    return round(wgs_lng, 8), round(wgs_lat, 8)
