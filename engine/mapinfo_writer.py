# -*- coding: utf-8 -*-
"""Styled MapInfo MIF/TAB writer with Chinese field-name support."""
from __future__ import annotations

import csv
import math
import numbers
import os
import re
import tempfile
from collections import OrderedDict
from datetime import date, datetime

import numpy as np
import pandas as pd
from shapely.geometry import shape

from engine.gdal_runtime import mif_to_tab_compatible


RN = "\r\n"
_INVALID_FIELD = re.compile(r"[\s,;:\"'`()\[\]{}\\/]+")


def color_int(value, default=0):
    if isinstance(value, numbers.Integral):
        return int(value)
    text = str(value or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", text):
        return int(text[1:], 16)
    return int(default)


def _field_map(features):
    result = OrderedDict()
    used = set()
    for feature in features:
        for original in feature.get("properties", {}):
            original = str(original)
            if original in result:
                continue
            clean = _INVALID_FIELD.sub("_", original.strip()).strip("_") or "字段"
            clean = clean[:31]
            candidate = clean
            index = 2
            while candidate.casefold() in used:
                suffix = f"_{index}"
                candidate = clean[:31 - len(suffix)] + suffix
                index += 1
            result[original] = candidate
            used.add(candidate.casefold())
    return result


def _column_type(values):
    present = [v for v in values if not _is_null(v)]
    if not present:
        return "Char(254)"
    if all(isinstance(v, (bool, np.bool_)) for v in present):
        return "Char(5)"
    if all(isinstance(v, numbers.Integral) and not isinstance(v, bool) for v in present):
        if all(-(2**31) <= int(v) <= 2**31 - 1 for v in present):
            return "Integer"
        return "Char(32)"
    if all(isinstance(v, numbers.Real) and not isinstance(v, bool) for v in present):
        return "Float"
    if all(isinstance(v, (date, datetime, pd.Timestamp)) for v in present):
        return "Char(32)"
    # Native TAB string width is byte-oriented after CP936 recoding.  Using a
    # character-count width truncates Chinese text (e.g. five Han characters
    # need ten bytes), so reserve the driver's safe classic maximum.
    return "Char(254)"


def _is_null(value):
    if value is None:
        return True
    try:
        result = pd.isna(value)
        return bool(result) if np.isscalar(result) else False
    except Exception:
        return False


def _mid_value(value):
    if _is_null(value):
        return ""
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return "" if not math.isfinite(float(value)) else float(value)
    if isinstance(value, (bool, np.bool_)):
        return "T" if value else "F"
    text = str(value)
    return text[:254]


def _coords_line(coords):
    return RN.join(f"{float(x):.7f} {float(y):.7f}" for x, y, *_ in coords)


def _geometry_text(geometry):
    if isinstance(geometry, dict):
        geometry = shape(geometry)
    gtype = geometry.geom_type
    if gtype == "Point":
        return f"Point {geometry.x:.7f} {geometry.y:.7f}{RN}"
    if gtype == "MultiPoint":
        # MIF has no single multi-point primitive; use a collection.
        parts = [f"Point {p.x:.7f} {p.y:.7f}{RN}" for p in geometry.geoms]
        return f"Collection {len(parts)}{RN}" + "".join(parts)
    if gtype == "LineString":
        return f"Pline {len(geometry.coords)}{RN}{_coords_line(geometry.coords)}{RN}"
    if gtype == "MultiLineString":
        parts = list(geometry.geoms)
        text = f"Pline Multiple {len(parts)}{RN}"
        for part in parts:
            text += f"{len(part.coords)}{RN}{_coords_line(part.coords)}{RN}"
        return text
    if gtype in ("Polygon", "MultiPolygon"):
        polygons = [geometry] if gtype == "Polygon" else list(geometry.geoms)
        rings = []
        for polygon in polygons:
            rings.append(list(polygon.exterior.coords))
            rings.extend(list(ring.coords) for ring in polygon.interiors)
        text = f"Region {len(rings)}{RN}"
        for ring in rings:
            text += f"{len(ring)}{RN}{_coords_line(ring)}{RN}"
        return text
    raise ValueError(f"MapInfo 暂不支持几何类型: {gtype}")


def _style_text(style, geometry):
    style = style or {}
    if isinstance(geometry, dict):
        geometry = shape(geometry)
    gtype = geometry.geom_type
    if "Point" in gtype:
        symbol = int(style.get("symbol", 35))
        size = max(1, min(255, int(round(float(style.get("symbol_size", 12))))))
        color = color_int(style.get("symbol_color", "#0078FF"), 0x0078FF)
        font = str(style.get("symbol_font", "MapInfo Symbols")).replace('"', "")
        return f'  Symbol ({symbol},{color},{size},"{font}",0,0){RN}'
    width = max(1, int(round(float(style.get("line_width", 1)))))
    pattern = int(style.get("line_pattern", 2))
    line_color = color_int(style.get("line_color", "#000000"), 0)
    text = f"  Pen ({width},{pattern},{line_color}){RN}"
    if "Polygon" in gtype:
        fill_color = color_int(style.get("fill_color", "#FFFFFF"), 0xFFFFFF)
        brush = int(style.get("brush_pattern", 2))
        background = color_int(style.get("background_color", "#FFFFFF"), 0xFFFFFF)
        text += f"  Brush ({brush},{fill_color},{background}){RN}"
    return text


def write_styled_mif(features, mif_path, progress_cb=None):
    """Write UTF-8 MIF/MID. UTF-8 is intentional: GDAL then recodes to CP936."""
    if not features:
        raise ValueError("没有可写入的图层要素")
    fields = _field_map(features)
    values = {
        original: [feature.get("properties", {}).get(original) for feature in features]
        for original in fields
    }
    definitions = [(safe, _column_type(values[original])) for original, safe in fields.items()]
    mid_path = os.path.splitext(mif_path)[0] + ".mid"

    with open(mif_path, "w", encoding="utf-8", newline="") as mif:
        mif.write("Version 1520" + RN)
        mif.write('Charset "UTF-8"' + RN)
        mif.write('Delimiter ","' + RN)
        mif.write("CoordSys Earth Projection 1, 0" + RN)
        mif.write(f"Columns {len(definitions)}" + RN)
        for name, datatype in definitions:
            mif.write(f"  {name} {datatype}" + RN)
        mif.write("Data" + RN + RN)
        total = len(features)
        for index, feature in enumerate(features, 1):
            geometry = feature.get("geometry")
            mif.write(_geometry_text(geometry))
            mif.write(_style_text(feature.get("style"), geometry))
            if progress_cb and (index == total or index % 20000 == 0):
                progress_cb(10 + int(index / total * 65), f"MapInfo 几何 {index:,}/{total:,}")

    with open(mid_path, "w", encoding="utf-8", newline="") as mid:
        writer = csv.writer(mid, delimiter=",", quotechar='"', lineterminator=RN)
        total = len(features)
        for index, feature in enumerate(features, 1):
            properties = feature.get("properties", {})
            writer.writerow([_mid_value(properties.get(original)) for original in fields])
            if progress_cb and (index == total or index % 50000 == 0):
                progress_cb(75 + int(index / total * 10), f"MapInfo 属性 {index:,}/{total:,}")
    return fields


def write_styled_tab(features, tab_path, progress_cb=None, encoding="CP936"):
    """Create a ready-to-open native TAB set without MapInfo or osgeo."""
    output_dir = os.path.dirname(os.path.abspath(tab_path)) or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="plc_mapinfo_", dir=output_dir) as temp_dir:
        mif_path = os.path.join(temp_dir, "layer.mif")
        field_map = write_styled_mif(features, mif_path, progress_cb)
        if progress_cb:
            progress_cb(88, "转换为原生 TAB...")
        mif_to_tab_compatible(
            mif_path, tab_path, encoding=encoding, progress_cb=progress_cb
        )
    required = [os.path.splitext(tab_path)[0] + ext for ext in (".tab", ".dat", ".map", ".id")]
    missing = [path for path in required if not os.path.isfile(path)]
    if missing:
        raise RuntimeError("TAB 输出不完整: " + ", ".join(os.path.basename(p) for p in missing))
    if progress_cb:
        progress_cb(96, "TAB 样式与中文属性写入完成")
    return field_map


def _dataframe_field_map(columns):
    return _field_map([{"properties": OrderedDict((str(col), None) for col in columns)}])


def _series_type(series):
    if pd.api.types.is_integer_dtype(series.dtype):
        non_null = series.dropna()
        if non_null.empty or (non_null.min() >= -(2**31) and non_null.max() <= 2**31 - 1):
            return "Integer"
        return "Char(32)"
    if pd.api.types.is_float_dtype(series.dtype):
        return "Float"
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return "Char(32)"
    return "Char(254)"


def write_point_dataframe_mif(df, lon_col, lat_col, color_values, mif_path,
                              symbol_size=12, progress_cb=None):
    """Stream a point DataFrame to MIF/MID without building feature objects."""
    columns = list(df.columns)
    field_map = _dataframe_field_map(columns)
    mid_path = os.path.splitext(mif_path)[0] + ".mid"
    definitions = [(field_map[str(col)], _series_type(df[col])) for col in columns]
    lons = pd.to_numeric(df[lon_col], errors="coerce").to_numpy(dtype=np.float64)
    lats = pd.to_numeric(df[lat_col], errors="coerce").to_numpy(dtype=np.float64)
    colors = np.asarray(color_values, dtype=np.int64)
    total = len(df)
    chunk_size = 20000

    with open(mif_path, "w", encoding="utf-8", newline="") as mif:
        mif.write("Version 1520" + RN + 'Charset "UTF-8"' + RN)
        mif.write('Delimiter ","' + RN + "CoordSys Earth Projection 1, 0" + RN)
        mif.write(f"Columns {len(definitions)}" + RN)
        for name, datatype in definitions:
            mif.write(f"  {name} {datatype}" + RN)
        mif.write("Data" + RN + RN)
        for start in range(0, total, chunk_size):
            end = min(start + chunk_size, total)
            rows = []
            for index in range(start, end):
                rows.append(
                    f"Point {lons[index]:.7f} {lats[index]:.7f}{RN}"
                    f'  Symbol (35,{int(colors[index])},{int(symbol_size)},"MapInfo Symbols",0,0){RN}'
                )
            mif.write("".join(rows))
            if progress_cb:
                progress_cb(10 + int(end / total * 60), f"路测几何 {end:,}/{total:,}")

    with open(mid_path, "w", encoding="utf-8", newline="") as mid:
        writer = csv.writer(mid, delimiter=",", quotechar='"', lineterminator=RN)
        for index, row in enumerate(df.itertuples(index=False, name=None), 1):
            writer.writerow([_mid_value(value) for value in row])
            if progress_cb and (index == total or index % 50000 == 0):
                progress_cb(70 + int(index / total * 15), f"路测属性 {index:,}/{total:,}")
    return field_map


def write_point_dataframe_tab(df, lon_col, lat_col, color_values, tab_path,
                              symbol_size=12, progress_cb=None, encoding="CP936"):
    output_dir = os.path.dirname(os.path.abspath(tab_path)) or os.getcwd()
    with tempfile.TemporaryDirectory(prefix="plc_drive_", dir=output_dir) as temp_dir:
        mif_path = os.path.join(temp_dir, "points.mif")
        field_map = write_point_dataframe_mif(
            df, lon_col, lat_col, color_values, mif_path,
            symbol_size=symbol_size, progress_cb=progress_cb,
        )
        if progress_cb:
            progress_cb(88, "转换路测 TAB...")
        mif_to_tab_compatible(
            mif_path, tab_path, encoding=encoding, progress_cb=progress_cb
        )
    return field_map
