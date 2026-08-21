# -*- coding: utf-8 -*-
"""扇区工具：UTM 投影扇形多边形生成 + 编号规则"""
import math

import numpy as np
from pyproj import CRS, Transformer


def assign_sector_numbers_rule1(azimuths):
    """规则一：正北±60°首扇区，顺时针编号

    首扇区判定：与正北(0°)最小夹角 ≤ 60°（含边界 60°/300°）
    扇区1确定：夹角最小优先；夹角相同取角度数值较小者
    后续编号：以扇区1为起点顺时针排序依次编号
    """
    n = len(azimuths)
    if n == 0:
        return []

    def is_candidate(az):
        return az >= 300 or az <= 60  # 含边界 60°/300°

    candidates = [az for az in azimuths if is_candidate(az)]
    if candidates:
        # 双重排序键：夹角优先，夹角相同取角度小者
        best = min(candidates, key=lambda az: (min(az, 360 - az), az))
    else:
        best = min(azimuths)  # 无候选兜底：取最小角度

    # 稳定排序（用 index），重复方位角按出现顺序编号
    order = sorted(range(n), key=lambda i: (azimuths[i] - best) % 360)
    rank = [0] * n
    for pos, i in enumerate(order):
        rank[i] = pos + 1
    return rank


def assign_sector_numbers_rule2(azimuths):
    """规则二：简单顺时针（默认），按方位角从小到大编号"""
    n = len(azimuths)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: azimuths[i])
    rank = [0] * n
    for pos, i in enumerate(order):
        rank[i] = pos + 1
    return rank


def get_utm_crs(lon, lat):
    zone = int((lon + 180) // 6) + 1
    south = lat < 0
    return CRS.from_dict({'proj': 'utm', 'zone': zone, 'south': south})


def make_sector_vertex_generator(lon, lat):
    """预建 UTM transformer，返回可复用的扇区顶点生成函数（性能优化）

    将 CRS/Transformer 创建从循环内移出，同一基站位置只创建一次。
    """
    wgs84 = CRS.from_epsg(4326)
    utm = get_utm_crs(lon, lat)
    to_utm = Transformer.from_crs(wgs84, utm, always_xy=True)
    to_wgs = Transformer.from_crs(utm, wgs84, always_xy=True)
    x0, y0 = to_utm.transform(lon, lat)

    def gen(azimuth, beamwidth, radius_m, num_points=None):
        half_bw = beamwidth / 2.0
        start_angle = azimuth - half_bw
        end_angle = azimuth + half_bw
        if num_points is None:
            num_points = max(int(beamwidth / 3), 15)
        angles = np.linspace(start_angle, end_angle, num_points)
        vertices = [(lon, lat)]
        for ang in angles:
            rad = math.radians(90 - ang)
            dx = radius_m * math.cos(rad)
            dy = radius_m * math.sin(rad)
            x, y = x0 + dx, y0 + dy
            glon, glat = to_wgs.transform(x, y)
            vertices.append((glon, glat))
        vertices.append((lon, lat))  # 闭合
        return vertices

    def label_position(azimuth, radius_m):
        """标签位置：方位角方向、半径一半处（扇区内部，避免同基站标签重叠）"""
        rad = math.radians(90 - azimuth)
        d = radius_m * 0.5
        dx = d * math.cos(rad)
        dy = d * math.sin(rad)
        glon, glat = to_wgs.transform(x0 + dx, y0 + dy)
        return glon, glat

    gen.label_position = label_position
    return gen


def sector_polygon_vertices(lon, lat, azimuth, beamwidth, radius_m, num_points=None):
    """生成扇区多边形顶点（单次调用，内部预建 transformer）"""
    gen = make_sector_vertex_generator(lon, lat)
    return gen(azimuth, beamwidth, radius_m, num_points)
