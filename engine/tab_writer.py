# -*- coding: utf-8 -*-
"""
纯 Python MapInfo TAB 写入器
直接写 .tab/.map/.dat/.id/.ind，绕过 GDAL mitab C 库崩溃
"""
import os
import struct
import datetime


def hex_to_mapinfo_color(hex_str):
    """#RRGGBB → MapInfo 颜色整数"""
    r = int(hex_str[1:3], 16)
    g = int(hex_str[3:5], 16)
    b = int(hex_str[5:7], 16)
    return r * 65536 + g * 256 + b


def rgb_to_mapinfo_color(r, g, b):
    """R,G,B (0-255) → MapInfo 颜色整数"""
    return r * 65536 + g * 256 + b


# ============================================================
# ToolDefTable: Pen/Brush 引用计数颜色定义表
# ============================================================

class ToolDefTable:
    def __init__(self):
        self._pens = []
        self._brushes = []

    def get_pen_index(self, color, pattern=2, width=1):
        if color is None:
            return 0
        for i, (c, p, w, _) in enumerate(self._pens):
            if c == color and p == pattern and w == width:
                return i + 1
        self._pens.append((color, pattern, width, 0))
        return len(self._pens)

    def add_pen_ref(self, index):
        if index > 0:
            c, p, w, n = self._pens[index - 1]
            self._pens[index - 1] = (c, p, w, n + 1)

    def get_brush_index(self, fg_color, bg_color=0xFFFFFF, pattern=2, transparent=False):
        if fg_color is None:
            return 0
        for i, (fg, bg, p, t, _) in enumerate(self._brushes):
            if fg == fg_color and bg == bg_color and p == pattern and t == transparent:
                return i + 1
        self._brushes.append((fg_color, bg_color, pattern, transparent, 0))
        return len(self._brushes)

    def add_brush_ref(self, index):
        if index > 0:
            fg, bg, p, t, n = self._brushes[index - 1]
            self._brushes[index - 1] = (fg, bg, p, t, n + 1)

    def build_tool_blocks(self):
        blocks = []
        for color, pattern, width, count in self._pens:
            if count == 0:
                continue
            buf = bytearray()
            buf.append(0x07)  # TABMAP_TOOL_PEN
            buf += struct.pack('<I', count)
            buf.append(min(max(width, 1), 7))
            buf.append(pattern)
            buf.append(0)  # point_width
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            buf += struct.pack('>BBB', r, g, b)
            blocks.append(bytes(buf))
        for fg, bg, pattern, transparent, count in self._brushes:
            if count == 0:
                continue
            buf = bytearray()
            buf.append(0x08)  # TABMAP_TOOL_BRUSH
            buf += struct.pack('<I', count)
            buf.append(pattern)
            buf.append(1 if transparent else 0)
            r = (fg >> 16) & 0xFF
            g = (fg >> 8) & 0xFF
            b = fg & 0xFF
            buf += struct.pack('>BBB', r, g, b)
            r = (bg >> 16) & 0xFF
            g = (bg >> 8) & 0xFF
            b = bg & 0xFF
            buf += struct.pack('>BBB', r, g, b)
            blocks.append(bytes(buf))
        return blocks


# ============================================================
# .TAB 文本头
# ============================================================

def _write_tab_header(tab_path, field_defs):
    """写入 .tab 文本头（用 GBK 编码支持中文字段名）"""
    lines = [
        '!table',
        '!version 300',
        '!charset WindowsSimpChinese',
        '',
        'Definition Table',
        '  Type NATIVE Charset "WindowsSimpChinese"',
        f'  Fields {len(field_defs)}',
    ]
    for item in field_defs:
        name = item[0]
        ftype = item[1]
        if ftype == 'F' and len(item) > 2:
            lines.append(f'    {name} Float ;')
        elif ftype == 'N':
            lines.append(f'    {name} Integer ;')
        else:
            sz = item[2] if len(item) > 2 else 254
            lines.append(f'    {name} Char({sz}) ;')
    lines.append('begin_metadata')
    lines.append('"\\IsReadOnly" = "FALSE"')
    lines.append('end_metadata')
    with open(tab_path, 'wb') as f:
        f.write('\r\n'.join(lines).encode('gbk'))


# ============================================================
# .MAP 二进制
# ============================================================

def _write_map_file(map_path, features):
    """写入 .map 二进制文件（含 ToolDefTable 样式）"""
    tt = ToolDefTable()

    # 第一遍：收集 Pen/Brush
    for feat in features:
        style = feat.get('style', {})
        pen_idx = tt.get_pen_index(
            style.get('pen_color'),
            style.get('pen_pattern', 2),
            style.get('pen_width', 1)
        )
        brush_idx = tt.get_brush_index(
            style.get('brush_fg'),
            style.get('brush_bg', 0xFFFFFF),
            style.get('brush_pattern', 2),
            style.get('brush_transparent', False)
        )
        tt.add_pen_ref(pen_idx)
        tt.add_brush_ref(brush_idx)
        feat['_pen_idx'] = pen_idx
        feat['_brush_idx'] = brush_idx

    # 第二遍：计算对象字节大小
    obj_offsets = []
    current_off = 512  # header block
    for feat in features:
        obj_offsets.append(current_off)
        feat['_obj_len'] = _calc_object_size(feat)
        current_off += feat['_obj_len']

    # 索引表
    idx_table_size = 4 * len(features)
    data_start = current_off + idx_table_size

    with open(map_path, 'wb') as f:
        # Header block (512 bytes)
        f.write(struct.pack('<I', 512))  # block size
        f.write(b'\x00' * 508)

        # Index table
        for off in obj_offsets:
            f.write(struct.pack('<I', off))

        # Object data
        for feat in features:
            _write_object_block(f, feat)

        # ToolDefTable blocks
        for block in tt.build_tool_blocks():
            f.write(block)


def _calc_object_size(feat):
    geom = feat['geometry']
    gtype = geom['type']
    if gtype == 'Point':
        return 1 + 32 + 16 + 5 + 2
    elif gtype == 'Polygon':
        rings = _extract_rings(geom)
        size = 1 + 32 + 4  # type + bbox + num_polygons
        for ring in rings:
            size += 4 + len(ring) * 16 + 4 + 16  # pts + centers
        size += 5 + 5 + 2 + 4 + 4  # pen + brush + symbol + smooth + font
        return size
    elif gtype == 'LineString':
        coords = geom['coordinates']
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        return 1 + 32 + 4 + len(coords) * 16 + 4 + 16 + 5 + 2 + 4 + 4
    elif gtype == 'MultiPolygon':
        rings = _extract_rings(geom)
        size = 1 + 32 + 4
        for ring in rings:
            size += 4 + len(ring) * 16 + 4 + 16
        size += 5 + 5 + 2 + 4 + 4
        return size
    raise ValueError(f"Unknown geometry type: {gtype}")


def _extract_rings(geom):
    gtype = geom['type']
    if gtype == 'Polygon':
        return [geom['coordinates'][0]]
    elif gtype == 'MultiPolygon':
        rings = []
        for poly_coords in geom['coordinates']:
            rings.append(poly_coords[0])
        return rings
    return []


def _write_object_block(f, feat):
    geom = feat['geometry']
    gtype = geom['type']

    if gtype == 'Point':
        coords = geom['coordinates']
        x, y = float(coords[0]), float(coords[1])
        obj_len = 1 + 32 + 16 + 5 + 2
        f.write(struct.pack('<I', obj_len))
        f.write(struct.pack('<B', 1))  # POINT
        f.write(struct.pack('<dddd', x, y, x, y))
        f.write(struct.pack('<dd', x, y))
        _write_pen(f, feat)
        f.write(struct.pack('<H', 0))  # symbol

    elif gtype in ('Polygon', 'MultiPolygon'):
        rings = _extract_rings(geom)
        all_x, all_y = [], []
        for r in rings:
            for x, y in r:
                all_x.append(x); all_y.append(y)
        bbox = (min(all_x), min(all_y), max(all_x), max(all_y))
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0

        obj_len = _calc_object_size(feat)
        f.write(struct.pack('<I', obj_len))
        f.write(struct.pack('<B', 5))  # REGION
        f.write(struct.pack('<dddd', *bbox))
        f.write(struct.pack('<I', len(rings)))

        for ring in rings:
            pts = list(ring)
            if len(pts) > 1 and pts[0] == pts[-1]:
                pts = pts[:-1]
            f.write(struct.pack('<I', len(pts)))
            for x, y in pts:
                f.write(struct.pack('<dd', float(x), float(y)))
            f.write(struct.pack('<I', 1))  # center_count
            f.write(struct.pack('<dd', cx, cy))

        _write_pen(f, feat)
        _write_brush(f, feat)
        f.write(struct.pack('<H', 0))  # symbol
        f.write(struct.pack('<I', 0))  # smooth
        f.write(struct.pack('<I', 0))  # font_len

    elif gtype == 'LineString':
        coords = list(geom['coordinates'])
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        xs = [c[0] for c in coords]; ys = [c[1] for c in coords]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0

        obj_len = _calc_object_size(feat)
        f.write(struct.pack('<I', obj_len))
        f.write(struct.pack('<B', 4))  # PLINE
        f.write(struct.pack('<dddd', *bbox))
        f.write(struct.pack('<I', 1))  # num_lines
        f.write(struct.pack('<I', len(coords)))
        for x, y in coords:
            f.write(struct.pack('<dd', float(x), float(y)))
        f.write(struct.pack('<I', 1))  # center_count
        f.write(struct.pack('<dd', cx, cy))
        _write_pen(f, feat)
        f.write(struct.pack('<H', 0))  # symbol
        f.write(struct.pack('<I', 0))  # smooth
        f.write(struct.pack('<I', 0))  # font_len


def _write_pen(f, feat):
    """5字节 Pen: [pattern(u1)][width(u1)][BGR big-endian(3)]"""
    style = feat.get('style', {})
    color = style.get('pen_color', 0)
    width = style.get('pen_width', 1)
    pattern = style.get('pen_pattern', 2)
    f.write(struct.pack('<B', pattern))
    f.write(struct.pack('<B', min(max(width, 1), 7)))
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    f.write(struct.pack('>BBB', r, g, b))


def _write_brush(f, feat):
    """5字节 Brush: [pattern(u1)][BGR big-endian(3)][transparent(u1)]"""
    style = feat.get('style', {})
    fg = style.get('brush_fg', 0xFFFFFF)
    bg = style.get('brush_bg', 0xFFFFFF)
    pattern = style.get('brush_pattern', 2)
    transparent = style.get('brush_transparent', False)
    f.write(struct.pack('<B', pattern))
    r = (fg >> 16) & 0xFF
    g = (fg >> 8) & 0xFF
    b = fg & 0xFF
    f.write(struct.pack('>BBB', r, g, b))
    f.write(struct.pack('<B', 1 if transparent else 0))


# ============================================================
# .DAT dBASE III
# ============================================================

def _write_dat_file(dat_path, features, field_defs):
    """field_defs: [('name', 'C', 64), ('name2', 'F', 20, 6), ...]"""
    field_sizes = {}
    total_len = 1  # delete flag
    for name, ftype, *args in field_defs:
        if ftype == 'C':
            size = args[0] if args else 254
        elif ftype == 'N':
            size = args[0] if args else 10
        elif ftype == 'F':
            size = args[0] if args else 20
        else:
            size = 254
        field_sizes[name] = size
        total_len += size

    header_len = 32 + len(field_defs) * 32 + 1
    now = datetime.datetime.now()

    with open(dat_path, 'wb') as f:
        # dBASE III Header
        f.write(struct.pack('<B', 0x03))
        f.write(struct.pack('<BBB', now.year % 100, now.month, now.day))
        f.write(struct.pack('<I', len(features)))
        f.write(struct.pack('<H', header_len))
        f.write(struct.pack('<H', total_len))
        f.write(b'\x00' * 20)

        # Field descriptors
        for name, ftype, *args in field_defs:
            fname = name.encode('ascii', errors='replace')[:10].ljust(11, b'\x00')
            f.write(fname)
            f.write(ftype.encode('ascii'))
            f.write(b'\x00' * 4)
            if ftype == 'C':
                flen = args[0] if args else 254
                fdec = 0
            elif ftype == 'N':
                flen = args[0] if args else 10
                fdec = 0
            elif ftype == 'F':
                flen = args[0] if args else 20
                fdec = args[1] if len(args) > 1 else 6
            f.write(struct.pack('<B', flen))
            f.write(struct.pack('<B', fdec))
            f.write(b'\x00' * 14)
        f.write(b'\x0D')

        # Records
        for feat in features:
            props = feat['properties']
            f.write(b'\x20')  # not deleted
            for name, ftype, *args in field_defs:
                val = props.get(name, '')
                if val is None:
                    val = ''
                if ftype in ('C',):
                    bval = str(val).encode('gbk', errors='replace')[:field_sizes[name]]
                    bval = bval.ljust(field_sizes[name], b'\x20')
                    f.write(bval)
                elif ftype in ('N', 'F'):
                    try:
                        num = float(val)
                        if ftype == 'N':
                            s = f'{int(num):>{field_sizes[name]}d}'
                        else:
                            dec = args[1] if len(args) > 1 else 6
                            s = f'{num:>{field_sizes[name]}.{dec}f}'
                    except (ValueError, TypeError):
                        s = ' ' * field_sizes[name]
                    f.write(s.encode('ascii'))


# ============================================================
# .ID / .IND
# ============================================================

def _write_id_file(id_path, count):
    with open(id_path, 'wb') as f:
        for i in range(1, count + 1):
            f.write(struct.pack('<I', i))


def _write_ind_file(ind_path, count):
    with open(ind_path, 'wb') as f:
        for i in range(count):
            f.write(struct.pack('<I', i))


# ============================================================
# 公共 API
# ============================================================

def write_tab_layer(output_path, features, crs='EPSG:4326'):
    """写入 MapInfo TAB 图层（纯 Python，不依赖 GDAL mitab C 库）"""
    base = output_path.replace('.tab', '').replace('.TAB', '')

    # 从第一个 feature 推断字段定义
    field_defs = _infer_field_defs(features)

    _write_tab_header(base + '.tab', field_defs)
    _write_map_file(base + '.map', features)
    _write_dat_file(base + '.dat', features, field_defs)
    _write_id_file(base + '.id', len(features))
    _write_ind_file(base + '.ind', len(features))


def _infer_field_defs(features):
    """从 features 推断字段定义"""
    if not features:
        return []
    props = features[0]['properties']
    defs = []
    for name, val in props.items():
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if isinstance(val, int) or (isinstance(val, float) and val == int(val)):
                defs.append((name, 'N', 10))
            else:
                defs.append((name, 'F', 20, 6))
        else:
            defs.append((name, 'C', 254))
    return defs
