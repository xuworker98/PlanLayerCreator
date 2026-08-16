# -*- coding: utf-8 -*-
"""
栅格图层 KML 快速写入器 — 分色级样式 + 精简坐标 + 80%透明度
"""
import numpy as np
import os
import zipfile
from xml.sax.saxutils import escape as xml_escape
from engine.mif_writer import _map_colors


def _hex_to_kml_abgr(hex_color, alpha=0xCC):
    """#RRGGBB → KML AABBGGRR 格式（alpha 80%=CC）"""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f'{alpha:02X}{b:02X}{g:02X}{r:02X}'


def write_grid_kml_fast(grid_df, lon_col, lat_col, level_col,
                        half_lon, half_lat, level_colors, columns, output_path,
                        border_width=0):
    """Compact grid KML: only the signal-level attribute is retained."""
    lons = grid_df[lon_col].values.astype(np.float64)
    lats = grid_df[lat_col].values.astype(np.float64)
    levels = grid_df[level_col].values.astype(np.float64)
    color_ints = _map_colors(levels, level_colors)
    n = len(grid_df)

    x0 = lons - half_lon
    x1 = lons + half_lon
    y0 = lats - half_lat
    y1 = lats + half_lat

    # 分色级：先建 style → 再写 placemark
    style_colors = list(dict.fromkeys(tuple(c) for c in level_colors))

    is_kmz = output_path.lower().endswith('.kmz')
    kml_path = output_path.replace('.kmz', '.kml') if is_kmz else output_path

    with open(kml_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n')
        f.write('  <name>MR栅格图层</name>\n')

        # 各色级 Style（80%透明 CC，无边框）
        for idx, (lo, hi, hex_c) in enumerate(style_colors):
            abgr = _hex_to_kml_abgr(hex_c, 0xCC)
            f.write(f'  <Style id="s{idx}">\n')
            outline = 1 if border_width > 0 else 0
            line_color = 'FF000000' if outline else '00000000'
            f.write(f'    <PolyStyle><color>{abgr}</color><outline>{outline}</outline></PolyStyle>\n')
            f.write(f'    <LineStyle><color>{line_color}</color><width>{max(0, border_width)}</width></LineStyle>\n')
            f.write(f'  </Style>\n')

        # 预设 color_hex → style_id 映射
        hex_to_sid = {}
        for idx, (lo, hi, hex_c) in enumerate(style_colors):
            hex_to_sid[hex_c] = idx

        # 分块写 placemark（无 name，无扩展数据）
        chunk = 10000
        for ci in range(0, n, chunk):
            end = min(ci + chunk, n)
            lines = []
            for i in range(ci, end):
                # 6位精度坐标
                coord = (
                    f'{x0[i]:.6f},{y0[i]:.6f} '
                    f'{x1[i]:.6f},{y0[i]:.6f} '
                    f'{x1[i]:.6f},{y1[i]:.6f} '
                    f'{x0[i]:.6f},{y1[i]:.6f} '
                    f'{x0[i]:.6f},{y0[i]:.6f}'
                )
                # 根据电平值找颜色 → style_id
                level_val = levels[i]
                hex_c = _get_hex_for_level(level_val, level_colors)
                sid = hex_to_sid.get(hex_c, 0)
                level_text = f'{float(level_val):.2f}'
                field_xml = xml_escape(str(level_col))
                lines.append(f'  <Placemark>'
                             f'<styleUrl>#s{sid}</styleUrl>'
                             f'<ExtendedData><Data name="{field_xml}"><value>{level_text}</value></Data></ExtendedData>'
                             f'<Polygon><outerBoundaryIs><LinearRing>'
                             f'<coordinates>{coord}</coordinates>'
                             f'</LinearRing></outerBoundaryIs></Polygon>'
                             f'</Placemark>')
            f.write('\n'.join(lines) + '\n')

        f.write('</Document>\n</kml>\n')

    if is_kmz:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(kml_path, os.path.basename(kml_path))
        os.remove(kml_path)


def _get_hex_for_level(level_val, level_colors):
    """根据电平值找对应的颜色 hex"""
    for lo, hi, hex_c in level_colors:
        if lo < level_val <= hi:
            return hex_c
    return level_colors[-1][2]


def write_drive_kmz_tiled(lons, lats, levels, level_colors, level_field,
                          output_path, icon_scale=0.8,
                          target_points_per_tile=20000):
    """Write a regionated KMZ so Google Earth loads large drive tests by view."""
    lons = np.asarray(lons, dtype=np.float64)
    lats = np.asarray(lats, dtype=np.float64)
    levels = np.asarray(levels, dtype=np.float64)
    count = len(lons)
    if count == 0:
        raise ValueError("没有可写入的路测点")

    bins = max(1, int(np.ceil(np.sqrt(count / max(1, target_points_per_tile)))))
    min_lon, max_lon = float(lons.min()), float(lons.max())
    min_lat, max_lat = float(lats.min()), float(lats.max())
    lon_step = max((max_lon - min_lon) / bins, 1e-9)
    lat_step = max((max_lat - min_lat) / bins, 1e-9)
    ix = np.minimum(((lons - min_lon) / lon_step).astype(np.int32), bins - 1)
    iy = np.minimum(((lats - min_lat) / lat_step).astype(np.int32), bins - 1)
    tile_ids = iy * bins + ix
    order = np.argsort(tile_ids, kind="stable")
    sorted_ids = tile_ids[order]
    split_at = np.flatnonzero(np.diff(sorted_ids)) + 1
    groups = np.split(order, split_at)

    field_xml = xml_escape(str(level_field))
    style_colors = list(dict.fromkeys(tuple(item) for item in level_colors))
    hex_to_sid = {item[2]: index for index, item in enumerate(style_colors)}

    def style_block():
        rows = []
        for index, (_, _, hex_color) in enumerate(style_colors):
            rows.append(
                f'<Style id="s{index}"><IconStyle><color>{_hex_to_kml_abgr(hex_color)}</color>'
                f'<scale>{float(icon_scale):.2f}</scale><Icon><href>'
                'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
                '</href></Icon></IconStyle></Style>'
            )
        return ''.join(rows)

    root_links = []
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for group_index, indexes in enumerate(groups):
            west, east = float(lons[indexes].min()), float(lons[indexes].max())
            south, north = float(lats[indexes].min()), float(lats[indexes].max())
            tile_name = f"tiles/tile_{group_index:04d}.kml"
            region = (
                f'<Region><LatLonAltBox><north>{north:.7f}</north><south>{south:.7f}</south>'
                f'<east>{east:.7f}</east><west>{west:.7f}</west></LatLonAltBox>'
                '<Lod><minLodPixels>64</minLodPixels><maxLodPixels>-1</maxLodPixels></Lod></Region>'
            )
            root_links.append(
                f'<NetworkLink><name>路测分片 {group_index + 1}</name>{region}'
                f'<Link><href>{tile_name}</href><viewRefreshMode>onRegion</viewRefreshMode></Link>'
                '</NetworkLink>'
            )
            placemarks = []
            for index in indexes:
                level = float(levels[index])
                color = _get_hex_for_level(level, level_colors)
                sid = hex_to_sid.get(color, 0)
                value = f"{level:.2f}"
                placemarks.append(
                    f'<Placemark><styleUrl>#s{sid}</styleUrl><ExtendedData>'
                    f'<Data name="{field_xml}"><value>{value}</value></Data></ExtendedData>'
                    f'<Point><coordinates>{lons[index]:.6f},{lats[index]:.6f}</coordinates></Point>'
                    '</Placemark>'
                )
            payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
                + style_block() + region + ''.join(placemarks) + '</Document></kml>'
            )
            archive.writestr(tile_name, payload.encode('utf-8'))
        root = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>路测图层（分片）</name>'
            + ''.join(root_links) + '</Document></kml>'
        )
        archive.writestr('doc.kml', root.encode('utf-8'))
    return len(groups)
