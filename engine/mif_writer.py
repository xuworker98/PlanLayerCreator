# -*- coding: utf-8 -*-
"""
MIF writer - grid layer
"""
import os
import csv
import numpy as np

from engine.mapinfo_writer import _dataframe_field_map, _mid_value, _series_type

RN = "\r\n"


def write_grid_mif_fast(grid_df, lon_col, lat_col, level_col,
                         half_lon, half_lat, level_colors,
                         columns, mif_path, progress_cb=None, border_width=1):
    mid_path = os.path.splitext(mif_path)[0] + ".mid"
    n = len(grid_df)

    if progress_cb:
        progress_cb(5, "计算配色...")

    levels = grid_df[level_col].values.astype(float)
    color_ints = _map_colors(levels, level_colors)
    lons = grid_df[lon_col].values.astype(float)
    lats = grid_df[lat_col].values.astype(float)

    field_map = _dataframe_field_map(columns)
    col_defs = [(field_map[str(col)], _series_type(grid_df[col])) for col in columns]
    header = _mif_header(col_defs)

    chunk_size = 20000
    total_chunks = (n + chunk_size - 1) // chunk_size

    with open(mif_path, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        for ci in range(total_chunks):
            start = ci * chunk_size
            end = min(start + chunk_size, n)
            rows = []
            hlx, hly = half_lon, half_lat
            for idx in range(start, end):
                lo, la = lons[idx], lats[idx]
                ci_color = color_ints[idx]
                rows.append(
                    "Region  1" + RN + "  5" + RN
                    + "{:.6f} {:.6f}".format(lo - hlx, la - hly) + RN
                    + "{:.6f} {:.6f}".format(lo + hlx, la - hly) + RN
                    + "{:.6f} {:.6f}".format(lo + hlx, la + hly) + RN
                    + "{:.6f} {:.6f}".format(lo - hlx, la + hly) + RN
                    + "{:.6f} {:.6f}".format(lo - hlx, la - hly) + RN
                    + "   Pen ({},2,{})".format(max(1, int(border_width)), ci_color) + RN
                    + "   Brush (2,{},16777215)".format(ci_color) + RN
                    + "   Center {:.6f} {:.6f}".format(lo, la) + RN
                )
            f.write("".join(rows))
            if progress_cb:
                pct = 10 + int((ci + 1) / total_chunks * 85)
                progress_cb(pct, "MIF... {}/{}".format(end, n))

    _write_mid_bytes(grid_df, columns, mid_path, n, chunk_size)
    if progress_cb:
        progress_cb(95, "MIF 完成")
    return field_map


def _mif_header(col_defs):
    h = "Version 1520" + RN + "Charset " + chr(34) + "UTF-8" + chr(34) + RN
    h += "Delimiter " + chr(34) + "," + chr(34) + RN
    h += "CoordSys Earth Projection 1, 0" + RN
    h += "Columns {}".format(len(col_defs)) + RN
    for name, typ in col_defs:
        h += "  {} {}".format(name, typ) + RN
    h += "Data" + RN + RN
    return h


def _build_col_defs(columns, data):
    float_cols = {"LON", "LAT", "SingleInfo"}
    result = []
    for col in columns:
        if col in float_cols:
            result.append((col, "Float"))
        elif hasattr(data, "dtypes") and data[col].dtype == "float64":
            result.append((col, "Float"))
        else:
            result.append((col, "Char(254)"))
    return result


def _map_colors(values, level_colors):
    n = len(values)
    result = np.full(n, 0xC0C0C0, dtype=np.int64)
    for low, high, hex_color in level_colors:
        mask = (values > low) & (values <= high)
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        result[mask] = r * 65536 + g * 256 + b
    return result


def _write_mid_bytes(df, columns, mid_path, n, chunk_size):
    with open(mid_path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=",", quotechar='"', lineterminator=RN)
        for row in df[columns].itertuples(index=False, name=None):
            writer.writerow([_mid_value(value) for value in row])
