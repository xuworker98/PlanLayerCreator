# -*- coding: utf-8 -*-
"""MR grid aggregation in a deterministic metre-based projected grid."""
import math

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer


def grid_aggregate(df, lon_col, lat_col, level_col, grid_size_m=50,
                   aggregation='mean', min_samples=1, weight_col=None):
    """
    将散点数据聚合为网格

    Args:
        df: pandas DataFrame
        lon_col: 经度列名
        lat_col: 纬度列名
        level_col: 测量电平值列名
        grid_size_m: 网格大小（米）

    Returns:
        DataFrame with columns: grid_lon, grid_lat, avg_level, sample_count
    """
    if grid_size_m <= 0:
        raise ValueError('网格大小必须大于 0')
    work = df[[lon_col, lat_col, level_col] + ([weight_col] if weight_col else [])].copy()
    work[lon_col] = pd.to_numeric(work[lon_col], errors='coerce')
    work[lat_col] = pd.to_numeric(work[lat_col], errors='coerce')
    work[level_col] = pd.to_numeric(work[level_col], errors='coerce')
    work = work.dropna(subset=[lon_col, lat_col, level_col])
    if work.empty:
        return pd.DataFrame(columns=['栅格编号', lon_col, lat_col, level_col, '采样点数'])

    mean_lon = float(work[lon_col].mean())
    mean_lat = float(work[lat_col].mean())
    zone = max(1, min(60, int((mean_lon + 180.0) // 6.0) + 1))
    epsg = (32700 if mean_lat < 0 else 32600) + zone
    wgs84 = CRS.from_epsg(4326)
    projected = CRS.from_epsg(epsg)
    forward = Transformer.from_crs(wgs84, projected, always_xy=True)
    inverse = Transformer.from_crs(projected, wgs84, always_xy=True)

    x, y = forward.transform(
        work[lon_col].to_numpy(dtype=np.float64),
        work[lat_col].to_numpy(dtype=np.float64),
    )
    gx = np.floor(np.asarray(x) / float(grid_size_m)).astype(np.int64)
    gy = np.floor(np.asarray(y) / float(grid_size_m)).astype(np.int64)
    work['_gx'] = gx
    work['_gy'] = gy

    grouped = work.groupby(['_gx', '_gy'], sort=False, observed=True)
    if weight_col:
        weights = pd.to_numeric(work[weight_col], errors='coerce').fillna(0.0)
        work['_weighted_level'] = work[level_col] * weights
        work['_weight'] = weights
        grouped = work.groupby(['_gx', '_gy'], sort=False, observed=True)
        result = grouped.agg(
            _weighted_sum=('_weighted_level', 'sum'),
            _weight_sum=('_weight', 'sum'),
            sample_count=(level_col, 'count'),
        ).reset_index()
        result[level_col] = result['_weighted_sum'] / result['_weight_sum'].replace(0, np.nan)
        result = result.drop(columns=['_weighted_sum', '_weight_sum'])
    else:
        method = 'median' if str(aggregation).lower() == 'median' else 'mean'
        result = grouped.agg(
            **{level_col: (level_col, method)},
            sample_count=(level_col, 'count'),
        ).reset_index()

    result = result[result['sample_count'] >= max(1, int(min_samples))].copy()
    center_x = (result['_gx'].to_numpy(dtype=np.float64) + 0.5) * float(grid_size_m)
    center_y = (result['_gy'].to_numpy(dtype=np.float64) + 0.5) * float(grid_size_m)
    center_lon, center_lat = inverse.transform(center_x, center_y)
    result[lon_col] = np.asarray(center_lon)
    result[lat_col] = np.asarray(center_lat)
    result['grid_id'] = [f'Z{zone:02d}_{ix}_{iy}' for ix, iy in zip(result['_gx'], result['_gy'])]
    result = result.rename(columns={'grid_id': '栅格编号', 'sample_count': '采样点数'})
    return result[['栅格编号', lon_col, lat_col, level_col, '采样点数']]
