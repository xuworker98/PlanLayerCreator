# -*- coding: utf-8 -*-
"""扇区工具：UTM 投影扇形多边形生成 + 编号规则"""
import math
import numpy as np
from pyproj import CRS, Transformer


def angle_to_north(az):
    diff = abs(az - 0)
    return min(diff, 360 - diff)


def assign_sector_numbers_rule1(azimuths):
    """规则一：正北±60°首扇区，顺时针编号"""
    n = len(azimuths)
    if n == 0:
        return []

    def is_candidate(az):
        return (300 <= az < 360) or (0 <= az < 60)

    candidates = [az for az in azimuths if is_candidate(az)]
    if candidates:
        best = min(candidates, key=lambda az: (angle_to_north(az), az))
    else:
        best = min(azimuths)

    sorted_az = sorted(azimuths)
    start_idx = sorted_az.index(best)
    ordered = sorted_az[start_idx:] + sorted_az[:start_idx]
    az_to_rank = {az: i + 1 for i, az in enumerate(ordered)}
    return [az_to_rank[az] for az in azimuths]


def assign_sector_numbers_rule2(azimuths):
    """规则二：简单顺时针排序编号"""
    sorted_az = sorted(azimuths)
    az_to_rank = {az: i + 1 for i, az in enumerate(sorted_az)}
    return [az_to_rank[az] for az in azimuths]


def get_utm_crs(lon, lat):
    zone = int((lon + 180) // 6) + 1
    south = lat < 0
    return CRS.from_dict({'proj': 'utm', 'zone': zone, 'south': south})


def sector_polygon_vertices(lon, lat, azimuth, beamwidth, radius_m, num_points=None):
    """生成扇区多边形顶点（WGS84经纬度）"""
    wgs84 = CRS.from_epsg(4326)
    utm = get_utm_crs(lon, lat)
    to_utm = Transformer.from_crs(wgs84, utm, always_xy=True)
    to_wgs = Transformer.from_crs(utm, wgs84, always_xy=True)

    x0, y0 = to_utm.transform(lon, lat)
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
