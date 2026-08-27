# -*- coding: utf-8 -*-
"""
图层生成引擎：从 DataFrame 生成 KML/KMZ/TAB/SHP 图层
"""
import os
import math
import numpy as np
import pandas as pd
import simplekml
from shapely.geometry import Point as ShpPoint, Polygon as ShpPolygon
from xml.sax.saxutils import escape as xml_escape

from engine.grid_engine import grid_aggregate
from utils.sector_utils import assign_sector_numbers_rule1, assign_sector_numbers_rule2, make_sector_vertex_generator
from utils.wkt_parser import parse_wkt
from utils.constants import LEVEL_COLORS_9


# ============================================================
# 通用方法
# ============================================================

def _clean_coords(df, lon_col, lat_col):
    """清洗经纬度数据"""
    df = df.dropna(subset=[lon_col, lat_col])
    df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
    df = df.dropna(subset=[lon_col, lat_col])
    df = df[(df[lon_col].between(-180, 180)) & (df[lat_col].between(-90, 90))]
    return df


def _get_level_color(value, level_colors):
    """根据电平值查找对应颜色"""
    for low, high, color in level_colors:
        if low < value <= high:
            return color
    return '#000000'


def _add_ext_data(pm, row, exclude_cols=None):
    """添加 ExtendedData + HTML description 到 KML Placemark"""
    if exclude_cols is None:
        exclude_cols = set()
    import re
    from xml.sax.saxutils import escape as _xml_escape
    _CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
    # 构建 HTML 表格
    html_parts = ['<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">']
    html_parts.append('<tr style="background:#0984e3;color:white"><th>字段</th><th>值</th></tr>')
    for col, val in row.items():
        if col in exclude_cols:
            continue
        col_str = _CTRL.sub('', str(col))
        if pd.isna(val):
            val = ''
        else:
            val = str(val)
            val = _CTRL.sub('', val)       # 移除非法 XML 控制字符
            val = _xml_escape(val)          # 转义 & < >（simplekml 的 Data.value 不转义，必须手动）
        html_parts.append(f'<tr><td>{col_str}</td><td>{val}</td></tr>')
        pm.extendeddata.newdata(name=col_str, value=val, displayname=col_str)
    html_parts.append('</table>')
    pm.description = '<![CDATA[' + '\n'.join(html_parts) + ']]>'


def _apply_coord_correction(df, lon_col, lat_col, do_correct):
    """坐标纠偏：GCJ-02 → WGS84"""
    if not do_correct:
        return df
    try:
        from utils.gcj02 import gcj02_to_wgs84
        new_lons, new_lats = [], []
        for _, row in df.iterrows():
            wgs_lon, wgs_lat = gcj02_to_wgs84(float(row[lon_col]), float(row[lat_col]))
            new_lons.append(wgs_lon)
            new_lats.append(wgs_lat)
        df = df.copy()
        df[lon_col] = new_lons
        df[lat_col] = new_lats
    except Exception:
        pass
    return df


def _save_kml(kml, output_path):
    """保存为 KML 或 KMZ（format=False 跳过 minidom 解析，避免非法字符报错）"""
    ext = os.path.splitext(output_path)[1].lower()
    if ext == '.kmz':
        kml.savekmz(output_path, format=False)
    else:
        kml.save(output_path, format=False)


def _write_clean_log(output_path, stats, total_rows, final_rows):
    """将数据清洗日志写入输出目录（生成日志.txt）"""
    try:
        from engine.data_clean import format_clean_log
        log_text = format_clean_log(stats, total_rows, final_rows)
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            log_path = os.path.join(out_dir, '生成日志.txt')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(log_text)
    except Exception:
        pass


def _write_illegal_log(output_path, illegal_details):
    """将非法字符明细写入输出目录（错误日志.txt）"""
    try:
        if not illegal_details:
            return
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if not out_dir:
            return
        log_path = os.path.join(out_dir, '错误日志.txt')
        from collections import Counter
        by_col = Counter(d[1] for d in illegal_details)
        lines = [
            "=" * 60,
            "数据错误日志（非法字符）",
            "=" * 60,
            f"发现 {len(illegal_details)} 处非法字符（已自动清洗，不影响生成）：",
            "",
            "【按字段分类汇总】",
        ]
        for col, cnt in by_col.most_common():
            lines.append(f"  - {col}: {cnt} 处")
        lines.append("")
        lines.append("【明细（前 100 条）】")
        lines.append("  行号\t字段\t原值(含非法字符)")
        for idx, col, val in illegal_details[:100]:
            lines.append(f"  {idx}\t{col}\t{repr(val)[:80]}")
        if len(illegal_details) > 100:
            lines.append(f"  ...（共 {len(illegal_details)} 条，仅显示前 100 条）")
        lines.append("")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    except Exception:
        pass


def _fix_tab_encoding(tab_path):
    """兼容旧驱动：仅修正 TAB 文本头，不改写已经由 GDAL 编码的 DAT。"""
    try:
        with open(tab_path, 'rb') as f:
            data = f.read()
        data = data.replace(b'!charset Neutral', b'!charset WindowsSimpChinese')
        data = data.replace(b'Charset "Neutral"', b'Charset "WindowsSimpChinese"')
        with open(tab_path, 'wb') as f:
            f.write(data)
    except Exception:
        pass


def _save_via_fiona(layer_data, output_path, driver):
    """通过格式引擎保存为 SHP/TAB"""
    if 'metadata' not in layer_data:
        layer_data['metadata'] = {}
    from shapely.geometry import mapping as _geom_to_dict
    for feat in layer_data.get('features', []):
        geom = feat.get('geometry')
        if geom is not None and hasattr(geom, '__geo_interface__'):
            feat['geometry'] = _geom_to_dict(geom)
    try:
        from engine.format_engine import write_fiona
        field_map = write_fiona(layer_data, output_path, driver)
        # SHP: 写 .cpg 编码声明
        if 'Shapefile' in driver:
            cpg_path = output_path.replace('.shp', '.cpg')
            with open(cpg_path, 'w', encoding='ascii') as f:
                f.write('GBK')
        # TAB: 补丁 .tab 头编码（Fiona 默认 Neutral → 改为 WindowsSimpChinese）
        if 'MapInfo' in driver:
            _fix_tab_encoding(output_path)
        # TAB: 写字段名对照文件
        if field_map and 'MapInfo' in driver:
            fld_path = output_path.replace('.tab', '_字段名对照.txt')
            with open(fld_path, 'w', encoding='utf-8') as f:
                f.write('TAB字段名 → 原始字段名 对照:\n')
                for safe, orig in sorted(field_map.items()):
                    f.write(f'{safe} = {orig}\n')
        return True
    except Exception as e:
        raise RuntimeError(f"格式写入失败: {e}")


def _save_styled_tab(features, output_path, progress_cb=None,
                     label_field=None, label_color="#000000",
                     label_size=9, show_label=False):
    """Write a native styled TAB set and an optional label workspace."""
    from engine.mapinfo_writer import write_styled_tab
    field_map = write_styled_tab(features, output_path, progress_cb=progress_cb)
    changed = {safe: original for original, safe in field_map.items() if safe != original}
    if changed:
        fld_path = os.path.splitext(output_path)[0] + '_字段名对照.txt'
        with open(fld_path, 'w', encoding='utf-8') as stream:
            stream.write('TAB字段名 → Excel原始字段名 对照:\n')
            for safe, original in changed.items():
                stream.write(f'{safe} = {original}\n')
    if label_field:
        from engine.mapinfo_workspace import write_label_workspace
        write_label_workspace(
            output_path,
            field_map.get(str(label_field), str(label_field)),
            color=label_color,
            size=label_size,
            enabled=show_label,
        )
    return field_map


# ============================================================
# 站点图层
# ============================================================

def generate_site_layer(df, mapping, style, output_path, do_correct=False, progress_cb=None):
    """
    生成站点图层

    Args:
        df: DataFrame
        mapping: {'lon': '列名', 'lat': '列名', 'name': '列名', 'label': '列名'(可选)}
        style: {'icon_color': '#xxx', 'label_color': '#xxx', 'scale': 1.0, 'show_label': True}
        output_path: 输出路径
        do_correct: 是否 GCJ-02→WGS84 纠偏
    """
    lon_col, lat_col = mapping['lon'], mapping['lat']
    name_col = mapping.get('name', lon_col)
    label_col = mapping.get('label', name_col)

    total_rows = len(df)
    from engine.data_clean import clean_numeric
    col_specs = {
        lon_col: {'kind': 'float', 'lo': -180, 'hi': 180, 'dms': True},
        lat_col: {'kind': 'float', 'lo': -90, 'hi': 90, 'dms': True},
    }
    df, stats = clean_numeric(df, col_specs)
    if do_correct:
        df = _apply_coord_correction(df, lon_col, lat_col, True)

    if df.empty:
        raise ValueError("无有效数据")

    ext = os.path.splitext(output_path)[1].lower()

    if ext in ('.kml', '.kmz'):
        kml = simplekml.Kml()
        folder = kml.newfolder(name='站点图层')
        icon_color = style.get('icon_color', '#0078FF')
        label_color = style.get('label_color', '#FF0000')
        scale = style.get('scale', 1.0)
        show_label = style.get('show_label', True)

        for idx, (_, row) in enumerate(df.iterrows()):
            lon, lat = float(row[lon_col]), float(row[lat_col])
            label_text = str(row[label_col]) if label_col in row else f"Site_{idx}"
            name = label_text if show_label else ""
            pnt = folder.newpoint(name=name, coords=[(lon, lat)])
            pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png'
            pnt.style.iconstyle.color = simplekml.Color.hexa(icon_color[1:] + 'ff')
            pnt.style.iconstyle.scale = scale
            pnt.style.labelstyle.color = simplekml.Color.hexa(label_color[1:] + 'ff')
            _add_ext_data(pnt, row)
            if idx % max(1, len(df) // 20) == 0 and progress_cb:
                progress_cb(idx * 90 // max(1, len(df)), f"生成站点 {idx}/{len(df)}")
        _save_kml(kml, output_path)
        if progress_cb:
            progress_cb(100, f"完成 {len(df)} 个站点")
        _write_clean_log(output_path, stats, total_rows, len(df))
        return len(df)

    elif ext == '.tab':
        features = []
        for _, row in df.iterrows():
            props = {k: row[k] for k in df.columns if not pd.isna(row[k])}
            features.append({
                'geometry': ShpPoint(float(row[lon_col]), float(row[lat_col])),
                'properties': props,
                'style': {
                    'symbol': 35,
                    'symbol_color': style.get('icon_color', '#0078FF'),
                    'symbol_size': 12 * float(style.get('scale', 1.0)),
                },
            })
        _save_styled_tab(
            features, output_path, progress_cb=progress_cb,
            label_field=label_col,
            label_color=style.get('label_color', '#FF0000'),
            label_size=max(7, int(round(9 * float(style.get('scale', 1.0))))),
            show_label=style.get('show_label', True),
        )
        _write_clean_log(output_path, stats, total_rows, len(df))
        return len(df)

    elif ext == '.shp':
        driver = 'ESRI Shapefile'
        features = []
        for _, row in df.iterrows():
            props = {k: row[k] for k in df.columns if not pd.isna(row[k])}
            features.append({'geometry': ShpPoint(float(row[lon_col]), float(row[lat_col])), 'properties': props})
        _save_via_fiona({'features': features}, output_path, driver)
        _write_clean_log(output_path, stats, total_rows, len(df))
        return len(df)

    raise ValueError(f"不支持的输出格式: {ext}")


# ============================================================
# 扇区图层
# ============================================================

def generate_sector_layer(df, mapping, style, output_path, do_correct=False, extra=None, progress_cb=None):
    """
    生成扇区图层
    extra: {'rule': 2, 'bw_default': 65, 'r_default': 100, 'bw_col': '', 'r_col': '', ...}
    progress_cb: callable(percent, message) — 可选进度回调
    """
    if extra is None:
        extra = {}

    lon_col, lat_col = mapping['lon'], mapping['lat']
    name_col = mapping.get('name', lon_col)
    az_col = mapping['azimuth']

    total_rows = len(df)

    # 统一清洗：度分秒 + 类型强制 + 空值剔除 + 非法字符清洗
    from engine.data_clean import clean_numeric
    col_specs = {
        lon_col: {'kind': 'float', 'lo': -180, 'hi': 180, 'dms': True},
        lat_col: {'kind': 'float', 'lo': -90, 'hi': 90, 'dms': True},
        az_col: {'kind': 'int', 'lo': 0, 'hi': 360},
    }
    illegal_details = []
    df, stats = clean_numeric(df, col_specs, illegal_details)
    _write_illegal_log(output_path, illegal_details)

    if df.empty:
        raise ValueError("无有效方位角数据")

    if do_correct:
        df = _apply_coord_correction(df, lon_col, lat_col, True)

    # 参数
    rule = extra.get('rule', 2)
    bw_def = extra.get('bw_default', 65.0)
    r_def = extra.get('r_default', 100.0)
    bw_col = extra.get('bw_col', '')
    r_col = extra.get('r_col', '')
    site_col = extra.get('site_col', '')
    other_color = extra.get('other_color', '#800080')
    add_label = extra.get('add_label', True)
    label_color = extra.get('label_color', '#FFFF00')
    colors = style.get('colors', {1: '#FF0000', 2: '#00FF00', 3: '#0000FF'})

    # 波束宽度/半径（整数）
    if bw_col and bw_col in df.columns:
        df['_Beamwidth'] = pd.to_numeric(df[bw_col], errors='coerce').fillna(bw_def).round().astype(int)
    else:
        df['_Beamwidth'] = int(bw_def)
    if r_col and r_col in df.columns:
        df['_Radius'] = pd.to_numeric(df[r_col], errors='coerce').fillna(r_def).round().astype(int)
    else:
        df['_Radius'] = int(r_def)
    df = df[(df['_Beamwidth'] > 0) & (df['_Radius'] > 0)]

    if df.empty:
        raise ValueError("无有效扇区数据")

    # 扇区编号：始终按经纬度分组（同一位置的扇区归一组），组内按方位角排序编号
    # 不依赖基站标识，保证填/不填基站标识结果一致
    df['_group_key'] = df.apply(lambda r: f"{r[lon_col]:.6f}_{r[lat_col]:.6f}", axis=1)
    group_col = '_group_key'

    sector_numbers = pd.Series(index=df.index, dtype='int64')
    for _, group in df.groupby(group_col):
        azs = group[az_col].tolist()
        if rule == 1:
            nums = assign_sector_numbers_rule1(azs)
        else:
            nums = assign_sector_numbers_rule2(azs)
        sector_numbers.loc[group.index] = [int(n) for n in nums]
    df['_SectorNumber'] = sector_numbers.astype(int)

    alpha = style.get('alpha', 128)
    line_color = style.get('line_color', '#000000')
    line_width = style.get('line_width', 1.0)

    ext = os.path.splitext(output_path)[1].lower()
    success = 0
    total = len(df)

    def _progress(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    # 顶点生成器缓存（同基站复用 transformer，避免循环内重复创建）
    gen_cache = {}

    def get_gen(lon, lat):
        key = (round(lon, 6), round(lat, 6))
        if key not in gen_cache:
            gen_cache[key] = make_sector_vertex_generator(lon, lat)
        return gen_cache[key]

    if ext in ('.kml', '.kmz'):
        kml = simplekml.Kml()
        folder_sectors = kml.newfolder(name='扇区')
        folder_labels = kml.newfolder(name='标签') if add_label else None

        # 标签共享 Style：空 <Icon/>（无 href）→ Google Earth 与奥维均不显示图钉
        label_style = None
        if add_label:
            label_style = simplekml.Style()
            label_style.iconstyle.icon.href = None  # 空 Icon，无图钉
            label_style.labelstyle.scale = 1.2
            label_style.labelstyle.color = simplekml.Color.hexa(label_color[1:] + 'ff')

        # 扇区面共享 Style：按填充色缓存复用（同色扇区共用一个 Style）
        poly_style_cache = {}

        for idx, (_, row) in enumerate(df.iterrows()):
            try:
                lon, lat = float(row[lon_col]), float(row[lat_col])
                az = float(row[az_col])
                bw = int(row['_Beamwidth'])
                radius = int(row['_Radius'])
                sec_num = int(row['_SectorNumber'])

                color_hex = colors.get(sec_num, other_color)
                kml_color = simplekml.Color.hexa(color_hex[1:] + f'{alpha:02x}')

                poly_style = poly_style_cache.get(kml_color)
                if poly_style is None:
                    poly_style = simplekml.Style()
                    poly_style.polystyle.color = kml_color
                    poly_style.linestyle.color = simplekml.Color.hexa(line_color[1:] + 'ff')
                    poly_style.linestyle.width = line_width
                    poly_style_cache[kml_color] = poly_style

                gen = get_gen(lon, lat)
                verts = gen(az, bw, radius)
                name = str(row[name_col]) if name_col in row else f"Sector_{success}"

                # 扇区面 → "扇区"文件夹（name 保留作气泡标题）
                pol = folder_sectors.newpolygon(name=name, outerboundaryis=verts)
                pol.style = poly_style
                _add_ext_data(pol, row, exclude_cols={'_SectorNumber', '_Beamwidth', '_Radius', '_group_key'})

                # 标签 → "标签"文件夹（Point，空 Icon，纯文字）
                if add_label:
                    glon, glat = gen.label_position(az, radius)
                    pnt = folder_labels.newpoint(name=name, coords=[(glon, glat)])
                    pnt.style = label_style

                success += 1
            except Exception:
                continue
            if idx % max(1, total // 20) == 0:
                _progress(int(idx / total * 90), f"生成扇区 {idx}/{total}")

        _save_kml(kml, output_path)
        _progress(100, f"完成 {success} 个扇区")
        _write_clean_log(output_path, stats, total_rows, success)
        return success

    elif ext in ('.shp', '.tab'):
        features = []
        for idx, (_, row) in enumerate(df.iterrows()):
            try:
                lon, lat = float(row[lon_col]), float(row[lat_col])
                az = float(row[az_col])
                bw = int(row['_Beamwidth'])
                radius = int(row['_Radius'])
                gen = get_gen(lon, lat)
                verts = gen(az, bw, radius)
                props = {k: row[k] for k in df.columns
                         if k not in ('_SectorNumber', '_Beamwidth', '_Radius', '_group_key')
                         and not pd.isna(row[k])}
                sec_num = int(row['_SectorNumber'])
                features.append({
                    'geometry': ShpPolygon(verts),
                    'properties': props,
                    'style': {
                        'fill_color': colors.get(sec_num, other_color),
                        'line_color': line_color,
                        'line_width': line_width,
                    },
                })
                success += 1
            except Exception:
                continue
            if idx % max(1, total // 20) == 0:
                _progress(int(idx / total * 90), f"生成扇区 {idx}/{total}")

        if ext == '.tab':
            _save_styled_tab(
                features, output_path,
                label_field=name_col,
                label_color=line_color,
                show_label=True,
            )
        else:
            _save_via_fiona({'features': features}, output_path, 'ESRI Shapefile')
        _progress(100, f"完成 {success} 个扇区")
        _write_clean_log(output_path, stats, total_rows, success)
        return success

    raise ValueError(f"不支持的输出格式: {ext}")


# ============================================================
# 路测图层
# ============================================================

def generate_drive_layer(df, mapping, style, output_path, do_correct=False, extra=None, progress_cb=None):
    """生成路测图层（KML/KMZ: 快速 numpy 点，MIF: COM → TAB）"""
    if extra is None:
        extra = {}
    lon_col, lat_col = mapping['lon'], mapping['lat']
    level_col = mapping['level']
    total_rows = len(df)
    from engine.data_clean import clean_numeric
    col_specs = {
        lon_col: {'kind': 'float', 'lo': -180, 'hi': 180, 'dms': True},
        lat_col: {'kind': 'float', 'lo': -90, 'hi': 90, 'dms': True},
        level_col: {'kind': 'float'},
    }
    df, stats = clean_numeric(df, col_specs)
    if df.empty:
        raise ValueError("无有效数据")
    _write_clean_log(output_path, stats, total_rows, len(df))
    if do_correct:
        df = _apply_coord_correction(df, lon_col, lat_col, True)

    level_colors = extra.get('level_colors', LEVEL_COLORS_9)
    ext = os.path.splitext(output_path)[1].lower()

    if ext in ('.kml', '.kmz'):
        from engine.kml_writer import _get_hex_for_level, _hex_to_kml_abgr
        lons = df[lon_col].values.astype(np.float64)
        lats = df[lat_col].values.astype(np.float64)
        levels = df[level_col].values.astype(np.float64)
        n = len(df)
        show_label = bool(extra.get('show_label', False))
        icon_scale = float(extra.get('scale', 0.8))
        style_colors = list(dict.fromkeys(tuple(c) for c in level_colors))
        hex_to_sid = {c[2]: i for i, c in enumerate(style_colors)}

        is_kmz = ext == '.kmz'
        if is_kmz and n >= int(extra.get('regionate_threshold', 100000)):
            from engine.kml_writer import write_drive_kmz_tiled
            if progress_cb:
                progress_cb(10, "大数据路测按区域分片...")
            tile_count = write_drive_kmz_tiled(
                lons, lats, levels, level_colors, level_col, output_path,
                icon_scale=icon_scale,
                target_points_per_tile=int(extra.get('points_per_tile', 20000)),
            )
            if progress_cb:
                progress_cb(98, f"KMZ 分片完成（{tile_count} 片）")
            return n
        kml_path = output_path.replace('.kmz', '.kml') if is_kmz else output_path

        with open(kml_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n')
            f.write('  <name>路测图层</name>\n')
            for idx, (lo, hi, hex_c) in enumerate(style_colors):
                abgr = _hex_to_kml_abgr(hex_c)
                f.write(f'  <Style id="s{idx}"><IconStyle><color>{abgr}</color><scale>{icon_scale:.2f}</scale>'
                        f'<Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>\n')
            chunk = 10000
            for ci in range(0, n, chunk):
                end = min(ci + chunk, n)
                lines = []
                for i in range(ci, end):
                    hex_c = _get_hex_for_level(float(levels[i]), level_colors)
                    sid = hex_to_sid.get(hex_c, 0)
                    level_text = f'{float(levels[i]):.2f}'
                    name_xml = f'<name>{level_text}</name>' if show_label else ''
                    field_xml = xml_escape(str(level_col))
                    lines.append(f'<Placemark>{name_xml}<styleUrl>#s{sid}</styleUrl>'
                                 f'<ExtendedData><Data name="{field_xml}"><value>{level_text}</value></Data></ExtendedData>'
                                 f'<Point><coordinates>{lons[i]:.6f},{lats[i]:.6f}</coordinates></Point></Placemark>')
                f.write('\n'.join(lines) + '\n')
            f.write('</Document>\n</kml>\n')

        if is_kmz:
            import zipfile
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(kml_path, os.path.basename(kml_path))
            os.remove(kml_path)
        return n

    elif ext in ('.mif', '.tab', '.shp'):
        from engine.mif_writer import _map_colors
        lons = df[lon_col].values.astype(np.float64)
        lats = df[lat_col].values.astype(np.float64)
        levels = df[level_col].values.astype(np.float64)
        colors = _map_colors(levels, level_colors)
        symbol_size = max(1, int(round(12 * float(extra.get('scale', 0.8)))))
        if ext == '.mif':
            from engine.mapinfo_writer import write_point_dataframe_mif
            write_point_dataframe_mif(
                df, lon_col, lat_col, colors, output_path,
                symbol_size=symbol_size, progress_cb=progress_cb,
            )
        elif ext == '.tab':
            from engine.mapinfo_writer import write_point_dataframe_tab
            field_map = write_point_dataframe_tab(
                df, lon_col, lat_col, colors, output_path,
                symbol_size=symbol_size, progress_cb=progress_cb,
            )
            if extra.get('show_label'):
                from engine.mapinfo_workspace import write_label_workspace
                write_label_workspace(
                    output_path, field_map.get(str(level_col), str(level_col)),
                    color='#000000', size=max(7, symbol_size), enabled=True,
                )
        else:
            features = []
            for index, (_, row) in enumerate(df.iterrows()):
                props = {key: row[key] for key in df.columns if not pd.isna(row[key])}
                features.append({
                    'geometry': ShpPoint(float(lons[index]), float(lats[index])),
                    'properties': props,
                })
            _save_via_fiona({'features': features}, output_path, 'ESRI Shapefile')
            try:
                from engine.qml_writer import write_qml_style
                write_qml_style(output_path, '路测图层', 'point', level_colors, level_col)
            except Exception:
                pass
        return len(df)

    raise ValueError(f"不支持的输出格式: {ext}")


# ============================================================
# MR 栅格图层
# ============================================================

def generate_grid_layer(df, mapping, style, output_path, do_correct=False, extra=None, progress_cb=None):
    """
    生成 MR 栅格图层
    extra: {'grid_size_m': 50, 'level_colors': [...], 'grid_id_col': ''}
    progress_cb: callable(percent, message) — 可选进度回调
    """
    if extra is None:
        extra = {}

    lon_col, lat_col = mapping['lon'], mapping['lat']
    level_col = mapping['level']
    grid_id_col = mapping.get('grid_id', '')
    grid_size_m = extra.get('grid_size_m', 50)
    level_colors = extra.get('level_colors', LEVEL_COLORS_9)

    df = _clean_coords(df, lon_col, lat_col)
    total_rows = len(df)
    from engine.data_clean import clean_numeric
    col_specs = {
        lon_col: {'kind': 'float', 'lo': -180, 'hi': 180, 'dms': True},
        lat_col: {'kind': 'float', 'lo': -90, 'hi': 90, 'dms': True},
        level_col: {'kind': 'float'},
    }
    df, stats = clean_numeric(df, col_specs)

    if grid_id_col and grid_id_col in df.columns:
        # A selected grid id means every input row already represents a grid.
        # Preserve the Excel attribute table exactly in this mode.
        grid_df = df.copy()
    else:
        # Raw MR samples: aggregate many points into a deterministic metre grid.
        grid_df = df.copy()
        if do_correct:
            grid_df = _apply_coord_correction(grid_df, lon_col, lat_col, True)
        grid_df = grid_aggregate(
            grid_df, lon_col, lat_col, level_col, grid_size_m,
            aggregation=extra.get('aggregation', 'mean'),
            min_samples=extra.get('min_samples', 1),
            weight_col=extra.get('weight_col') or None,
        )

    if do_correct and grid_id_col and grid_id_col in df.columns:
        grid_df = _apply_coord_correction(grid_df, lon_col, lat_col, True)

    if grid_df.empty:
        raise ValueError("无有效网格数据")
    _write_clean_log(output_path, stats, total_rows, len(grid_df))

    mid_lat = grid_df[lat_col].mean()
    deg_per_m_lat = 1.0 / 111320.0
    deg_per_m_lon = 1.0 / (111320.0 * math.cos(math.radians(mid_lat)))
    half_lon = grid_size_m / 2.0 * deg_per_m_lon
    half_lat = grid_size_m / 2.0 * deg_per_m_lat

    ext = os.path.splitext(output_path)[1].lower()
    columns = list(grid_df.columns)

    if ext in ('.kml', '.kmz'):
        from engine.kml_writer import write_grid_kml_fast
        if progress_cb:
            progress_cb(85, "KML...")
        write_grid_kml_fast(grid_df, lon_col, lat_col, level_col,
                            half_lon, half_lat, level_colors,
                            columns, output_path,
                            border_width=int(extra.get('border_width', 0)))
        return len(grid_df)

    elif ext in ('.tab', '.mif'):
        # Styled UTF-8 MIF; TAB is converted by the bundled GDAL runtime.
        from engine.mif_writer import write_grid_mif_fast
        if ext == '.mif':
            write_grid_mif_fast(
                grid_df, lon_col, lat_col, level_col,
                half_lon, half_lat, level_colors,
                columns, output_path, progress_cb=progress_cb,
                border_width=int(extra.get('border_width', 1)),
            )
        else:
            import tempfile
            from engine.gdal_runtime import mif_to_tab_compatible
            output_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
            with tempfile.TemporaryDirectory(prefix='plc_grid_', dir=output_dir) as temp_dir:
                mif_path = os.path.join(temp_dir, 'grid.mif')
                write_grid_mif_fast(
                    grid_df, lon_col, lat_col, level_col,
                    half_lon, half_lat, level_colors,
                    columns, mif_path, progress_cb=progress_cb,
                    border_width=int(extra.get('border_width', 1)),
                )
                if progress_cb:
                    progress_cb(96, "转换为原生着色 TAB...")
                mif_to_tab_compatible(
                    mif_path, output_path, encoding='CP936', progress_cb=progress_cb
                )
        return len(grid_df)

    elif ext == '.shp':
        features = []
        for _, row in grid_df.iterrows():
            lon, lat = float(row[lon_col]), float(row[lat_col])
            polygon = ShpPolygon([
                (lon - half_lon, lat - half_lat), (lon + half_lon, lat - half_lat),
                (lon + half_lon, lat + half_lat), (lon - half_lon, lat + half_lat),
                (lon - half_lon, lat - half_lat),
            ])
            props = {key: row[key] for key in columns if not pd.isna(row[key])}
            features.append({'geometry': polygon, 'properties': props})
        _save_via_fiona({'features': features}, output_path, 'ESRI Shapefile')
        try:
            from engine.qml_writer import write_qml_style
            write_qml_style(output_path, 'MR栅格图层', 'polygon', level_colors, level_col)
        except Exception:
            pass
        return len(grid_df)

    raise ValueError(f"不支持的输出格式: {ext}")


# ============================================================
# WKT 线路/面域图层
# ============================================================

def generate_wkt_layer(df, mapping, style, output_path, do_correct=False, extra=None, progress_cb=None):
    """
    生成 WKT 图层（线条或面域）
    progress_cb: callable(percent, message) — 可选进度回调
    """
    wkt_col = mapping.get('wkt_col', 'WKT')

    ext = os.path.splitext(output_path)[1].lower()
    features = []
    total = len(df)

    def _progress(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    for idx, (_, row) in enumerate(df.iterrows()):
        try:
            wkt_text = str(row[wkt_col])
            geom = parse_wkt(wkt_text)
            if geom is None or geom.is_empty:
                continue
            # 坐标纠偏（如果需要）
            if do_correct:
                from utils.gcj02 import gcj02_to_wgs84
                from shapely import ops
                def _correct_callback(x, y, z=None):
                    return gcj02_to_wgs84(x, y) + ((z,) if z is not None else ())
                geom = ops.transform(_correct_callback, geom)
            props = {k: row[k] for k in df.columns if not pd.isna(row[k])}
            feature_style = {
                'line_color': style.get('line_color', '#0984e3'),
                'line_width': style.get('line_width', 2.0),
            }
            if 'Polygon' in geom.geom_type:
                feature_style['fill_color'] = style.get('fill_color', '#74b9ff')
            features.append({'geometry': geom, 'properties': props, 'style': feature_style})
        except Exception:
            pass
        finally:
            if idx % max(1, total // 20) == 0:
                _progress(int(idx / total * 90), f"解析 WKT {idx}/{total}")

    if not features:
        raise ValueError("无有效的 WKT 几何数据")

    if ext in ('.kml', '.kmz'):
        kml = simplekml.Kml()
        folder = kml.newfolder(name='WKT图层')
        line_color = style.get('line_color', '#0984e3')
        line_width = style.get('line_width', 2.0)
        fill_color = style.get('fill_color', '')
        id_col = mapping.get('type_col', '')

        for i, feat in enumerate(features):
            geom = feat['geometry']
            props = feat['properties']
            # 名称：唯一标识列 > 序号 > Feature_i
            if id_col and id_col in props:
                name = str(props[id_col])
            elif '序号' in props:
                name = str(props['序号'])
            else:
                name = f'Feature_{i}'
            # HTML 属性表（剔除 WKT 列，避免超长字符串）
            wkt_col_actual = mapping.get('wkt_col', 'WKT')
            desc_lines = ['<table border="1" cellpadding="4" style="border-collapse:collapse;">']
            for k, v in props.items():
                if k == wkt_col_actual or k.upper() == 'WKT':
                    continue
                try:
                    desc_lines.append(f'<tr><td><b>{k}</b></td><td>{v}</td></tr>')
                except Exception:
                    desc_lines.append(f'<tr><td><b>{k}</b></td><td> </td></tr>')
            desc_lines.append('</table>')
            desc = ''.join(desc_lines)

            gtype = geom.geom_type.upper()

            if gtype == 'POINT':
                pnt = folder.newpoint(name=str(name), description=desc, coords=[(geom.x, geom.y)])
            elif gtype == 'LINESTRING':
                coords = [(c[0], c[1]) for c in geom.coords]
                ln = folder.newlinestring(name=str(name), description=desc, coords=coords)
                ln.style.linestyle.color = simplekml.Color.hexa(line_color[1:] + 'ff')
                ln.style.linestyle.width = line_width
            elif gtype in ('POLYGON', 'MULTIPOLYGON'):
                if fill_color:
                    kml_fill = simplekml.Color.hexa(fill_color[1:] + '80')
                else:
                    kml_fill = simplekml.Color.hexa('00000000')
                if gtype == 'POLYGON':
                    outer = [(c[0], c[1]) for c in geom.exterior.coords]
                    pol = folder.newpolygon(name=str(name), description=desc, outerboundaryis=outer)
                    pol.style.polystyle.color = kml_fill
                    pol.style.linestyle.color = simplekml.Color.hexa(line_color[1:] + 'ff')
                    pol.style.linestyle.width = line_width
                else:
                    for poly in geom.geoms:
                        outer = [(c[0], c[1]) for c in poly.exterior.coords]
                        pol = folder.newpolygon(name=str(name), description=desc, outerboundaryis=outer)
                        pol.style.polystyle.color = kml_fill
                        pol.style.linestyle.color = simplekml.Color.hexa(line_color[1:] + 'ff')
                        pol.style.linestyle.width = line_width

        _save_kml(kml, output_path)
        _progress(100, f"完成 {len(features)} 个要素")
        return len(features)

    elif ext in ('.shp', '.tab'):
        if ext == '.tab':
            _save_styled_tab(
                features, output_path,
                label_field=mapping.get('type_col') or mapping.get('id_col'),
                label_color=style.get('line_color', '#0984e3'),
                show_label=bool(mapping.get('type_col') or mapping.get('id_col')),
            )
        else:
            _save_via_fiona({'features': features}, output_path, 'ESRI Shapefile')
        _progress(100, f"完成 {len(features)} 个要素")
        return len(features)

    raise ValueError(f"不支持的输出格式: {ext}")
