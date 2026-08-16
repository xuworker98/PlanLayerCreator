"""
format_engine.py — 图层格式互转引擎

核心设计：
  所有输入格式 → 统一 LayerData 内部模型 → 目标格式输出
  KML: 用 ElementTree（保留奥维 OvStyle 标签）
  SHP: 用 pyogrio/GDAL（含中文编码）
  TAB: 带样式 MIF → pyogrio 随包 GDAL 或本机 MapInfo
"""

import os
import numbers
import xml.etree.ElementTree as ET
from typing import Any

from shapely.geometry import shape, Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon
from shapely.geometry import mapping as geom_mapping


# ============================================================
# 编码检测（内联，原 shp_encoding.py 已移除）
# ============================================================

def _default_encoding():
    import locale
    try: return locale.getdefaultlocale()[1] or 'gbk'
    except: return 'gbk'

def _get_read_encoding(filepath, auto_detect):
    return _default_encoding()

def _detect_dbf_encoding(filepath):
    return _default_encoding(), 1.0

def _is_utf8_encoding(enc):
    return enc and enc.lower() in ('utf-8', 'utf8')

# ============================================================
# KML 命名空间
# ============================================================
KML_NS = "http://www.opengis.net/kml/2.2"
KML_NS_GE = "http://earth.google.com/kml/2.1"
KML_NSMAP = {"kml": KML_NS}
ET.register_namespace("", KML_NS)  # 默认命名空间

# ============================================================
# 内部数据模型
# ============================================================
# LayerData = {
#     "metadata": {
#         "source_format": "KML"|"SHP"|"TAB",
#         "source_crs": "EPSG:4326",
#         "encoding": "UTF-8",
#         "feature_count": 156,
#         "ov_tags": { ... },       # 奥维扩展标签（如有）
#         "style_tags": { ... },    # KML Style 标签（如有）
#     },
#     "features": [
#         {
#             "geometry": {"type": "Point", "coordinates": [lng, lat]},
#             "properties": {"name": "...", "field1": "..."}
#         },
#         ...
#     ]
# }


# ============================================================
# KML 读取
# ============================================================
def read_kml(filepath: str) -> dict:
    """?? KML/ovkml -> LayerData??? earth.google.com/kml/2.1"""
    tree = ET.parse(filepath)
    root = tree.getroot()
    _normalize_kml_ns(root)
    metadata = {"source_format":"KML","source_crs":"EPSG:4326","encoding":"UTF-8",
                "feature_count":0,"ov_tags":{},"style_tags":{}}
    doc_elem = None
    for tag in ("Document","Folder"):
        doc_elem = root.find(f"{{{KML_NS}}}{tag}")
        if doc_elem is not None: break
    if doc_elem is None: doc_elem = root
    _extract_ov_tags_from_element(doc_elem, metadata["ov_tags"])
    features = []
    for pm in doc_elem.findall(f".//{{{KML_NS}}}Placemark"):
        _extract_ov_tags_from_element(pm, metadata["ov_tags"])
        feat = _parse_placemark(pm)
        if feat: features.append(feat)
    metadata["feature_count"] = len(features)
    return {"metadata": metadata, "features": features}

def _extract_ov_tags_from_element(element: ET.Element, ov_tags: dict):
    """提取奥维扩展标签（OvStyle, OvCoordType 等），直接存原始 XML 文本"""
    for child in element:
        tag = child.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag.lower().startswith("ov"):
            # 存原始 XML 字符串（不含命名空间声明头）
            raw_xml = ET.tostring(child, encoding="unicode")
            ov_tags[tag] = raw_xml.strip()



def _find_first(parent: ET.Element, tag: str, ns_list: list) -> ET.Element | None:
    """Search tag in multiple namespaces. Handles .// prefix for descendants."""
    prefix = ""
    if tag.startswith(".//"):
        prefix = ".//"
        tag = tag[3:]
    for ns in ns_list:
        elem = parent.find(f"{prefix}{ns}{tag}")
        if elem is not None:
            return elem
    return None
    return None
def _parse_placemark(pm: ET.Element) -> dict | None:
    """解析单个 Placemark → feature dict"""
    props = {}
    # 尝试两个命名空间
    ns_list = [f"{{{KML_NS}}}", f"{{{KML_NS_GE}}}"]

    # name
    name_elem = _find_first(pm, "name", ns_list)
    if name_elem is not None and name_elem.text:
        props["name"] = name_elem.text

    # description
    desc_elem = _find_first(pm, "description", ns_list)
    if desc_elem is not None and desc_elem.text:
        props["description"] = desc_elem.text

    # ExtendedData
    ext_data = _find_first(pm, "ExtendedData", ns_list)
    if ext_data is not None:
        for data_elem in ext_data:
            tag = data_elem.tag.split("}", 1)[-1]
            if tag in ("Data", "SimpleData"):
                key = data_elem.get("name") or data_elem.tag
                value_elem = _find_first(data_elem, "value", ns_list)
                if value_elem is not None and value_elem.text:
                    props[key] = value_elem.text

    # Geometry
    geom = None
    for geom_tag in ("Point", "LineString", "Polygon",
                     "MultiGeometry", "LinearRing"):
        geom_elem = _find_first(pm, f".//{geom_tag}", ns_list)
        if geom_elem is not None:
            geom = _parse_kml_geometry(geom_elem, geom_tag)
            break

    if geom is None:
        return None  # 无几何，跳过

    return {"geometry": geom, "properties": props}


def _parse_kml_geometry(elem: ET.Element, geom_type: str) -> dict:
    """解析 KML 几何元素 → GeoJSON 几何 dict"""
    ns_list = [f"{{{KML_NS}}}", f"{{{KML_NS_GE}}}"]

    if geom_type == "Point":
        coord_elem = _find_first(elem, "coordinates", ns_list)
        if coord_elem is not None and coord_elem.text:
            parts = coord_elem.text.strip().split(",")
            return {
                "type": "Point",
                "coordinates": [float(parts[0]), float(parts[1])]
            }

    elif geom_type in ("LineString", "LinearRing"):
        coord_elem = _find_first(elem, "coordinates", ns_list)
        if coord_elem is not None and coord_elem.text:
            coords = _parse_coordinate_string(coord_elem.text)
            return {
                "type": "LineString",
                "coordinates": coords
            }

    elif geom_type == "Polygon":
        # outer ring
        outer_coords = []
        for ns in ns_list:
            outer = elem.find(f"{ns}outerBoundaryIs/{ns}LinearRing/{ns}coordinates")
            if outer is not None and outer.text:
                outer_coords = _parse_coordinate_string(outer.text)
                break
        # inner rings
        inner_rings = []
        for ns in ns_list:
            for inner in elem.findall(f"{ns}innerBoundaryIs/{ns}LinearRing/{ns}coordinates"):
                if inner.text:
                    inner_rings.append(_parse_coordinate_string(inner.text))
        return {"type": "Polygon", "coordinates": [outer_coords] + inner_rings if outer_coords else []}
    elif geom_type == "MultiGeometry":
        # MultiGeometry → 取第一个子几何
        for child in elem:
            child_tag = child.tag.split("}", 1)[-1]
            if child_tag in ("Point", "LineString", "Polygon"):
                return _parse_kml_geometry(child, child_tag)

    return None


def _parse_coordinate_string(text: str) -> list:
    """解析 KML coordinates 字符串 → [[lng, lat], ...]"""
    coords = []
    for triple in text.strip().split():
        parts = triple.split(",")
        if len(parts) >= 2:
            coords.append([float(parts[0]), float(parts[1])])
    return coords


# ============================================================


def _normalize_kml_ns(element: ET.Element):
    """递归将所有 GE KML 2.1 命名空间的标签转为 OGC KML 2.2"""
    ge_ns = f"{{{KML_NS_GE}}}"
    kml_ns = f"{{{KML_NS}}}"
    if element.tag.startswith(ge_ns):
        element.tag = element.tag.replace(ge_ns, kml_ns)
    for child in element:
        _normalize_kml_ns(child)

# SHP / TAB reading (pyogrio)
# ============================================================

def _detect_tab_encoding(filepath: str) -> str:
    """MapInfo declares its charset in the TAB header; let GDAL honor it."""
    import pyogrio.raw
    pyogrio.read_info(filepath)
    return "auto"

def _read_fiona(filepath: str, driver: str, auto_detect_encoding: bool = True) -> dict:
    """Read SHP or TAB into the common LayerData structure."""
    import pyogrio.raw
    if driver == "ESRI Shapefile":
        encoding = _get_read_encoding(filepath, auto_detect_encoding)
        detected_enc, conf = _detect_dbf_encoding(filepath)
    else:
        # TAB 文件默认使用 GBK（国内 MapInfo 通用编码）
        encoding = "gbk" if auto_detect_encoding else "utf-8"
        detected_enc, conf = encoding, 1.0

    metadata = {
        "source_format": "SHP" if "Shapefile" in driver else "TAB",
        "source_crs": "EPSG:4326",
        "encoding": encoding,
        "detected_encoding": detected_enc,
        "encoding_confidence": conf,
        "feature_count": 0,
        "ov_tags": {},
        "style_tags": {},
    }

    from shapely import from_wkb
    raw_meta, _, geometry_wkb, field_data = pyogrio.raw.read(filepath)
    metadata["source_crs"] = raw_meta.get("crs") or "EPSG:4326"
    attribute_columns = list(raw_meta["fields"])
    geometries = from_wkb(geometry_wkb)
    features = []
    for row_index, geometry in enumerate(geometries):
        properties = {
            key: field_data[field_index][row_index]
            for field_index, key in enumerate(attribute_columns)
        }
        features.append({"geometry": geom_mapping(geometry), "properties": properties})

    metadata["feature_count"] = len(features)
    return {"metadata": metadata, "features": features}


def read_shp(filepath: str, auto_detect_encoding: bool = True) -> dict:
    """读取 SHP → LayerData"""
    return _read_fiona(filepath, "ESRI Shapefile", auto_detect_encoding)


def read_tab(filepath: str, auto_detect_encoding: bool = True) -> dict:
    """读取 TAB → LayerData"""
    return _read_fiona(filepath, "MapInfo File", auto_detect_encoding)


# ============================================================
# 统一读取入口
# ============================================================
def read_layer(filepath: str, auto_detect_encoding: bool = True) -> dict:
    """根据扩展名自动选择读取器"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".kml", ".ovkml"):
        return read_kml(filepath)
    elif ext == ".shp":
        return read_shp(filepath, auto_detect_encoding)
    elif ext == ".tab":
        return read_tab(filepath, auto_detect_encoding)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


# ============================================================
# 格式写入
# ============================================================
def write_kml(layer: dict, filepath: str, name_field: str = None):
    """LayerData → KML 文件"""
    root = ET.Element("kml", {"xmlns": KML_NS})
    doc = ET.SubElement(root, "Document")

    meta = layer["metadata"]

    # 文档名称
    name_elem = ET.SubElement(doc, "name")
    name_elem.text = os.path.splitext(os.path.basename(filepath))[0]

    for feat in layer["features"]:
        pm = ET.SubElement(doc, "Placemark")

        props = feat.get("properties", {})

        # --- 自动选择名称字段 ---
        name_candidates = ["name", "名称", "网格名称", "站点名称", "基站名称", "站名", "Name", "NAME"]
        place_name = None
        for cand in name_candidates:
            if cand in props and props[cand]:
                place_name = str(props[cand])
                break
        if place_name is None:
            # 取第一个字符串字段作为名称
            for k, v in props.items():
                if v and k.lower() not in ("fid", "id", "唯一id"):
                    place_name = str(v)
                    break
        if place_name:
            n = ET.SubElement(pm, "name")
            n.text = place_name

        # --- 生成描述（HTML 表格） ---
        desc_parts = ["<br><br><br>", '<table border="1" padding="0">']
        for key, val in props.items():
            desc_parts.append(f'<tr><td>{key}</td><td>{val}</td></tr>')
        desc_parts.append("</table>")
        desc_html = "\n".join(desc_parts)
        d = ET.SubElement(pm, "description")
        d.text = desc_html

        # --- ExtendedData（所有属性） ---
        if props:
            ext = ET.SubElement(pm, "ExtendedData")
            for key, val in props.items():
                data = ET.SubElement(ext, "Data", {"name": key})
                value = ET.SubElement(data, "value")
                value.text = str(val)

        # 几何
        geom = feat.get("geometry")
        if geom:
            _write_kml_geometry(pm, geom)

    # 序列化 XML
    xml_bytes = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
    xml_str = xml_bytes.decode("UTF-8")

    # 在 <Document> 后注入奥维标签（避免命名空间冲突）
    ov_xml = ""
    for tag, xml_str_frag in meta.get("ov_tags", {}).items():
        import re
        cleaned = re.sub(r'\s+xmlns(:\w+)?="[^"]*"', '', xml_str_frag)
        ov_xml += cleaned + "\n"

    if ov_xml:
        xml_str = xml_str.replace("<Document>", "<Document>\n" + ov_xml)

    with open(filepath, "w", encoding="UTF-8") as f:
        f.write(xml_str)


def _write_kml_geometry(parent: ET.Element, geom: dict):
    """写入 KML 几何"""
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])

    if gtype == "Point":
        pt = ET.SubElement(parent, "Point")
        c = ET.SubElement(pt, "coordinates")
        c.text = f"{coords[0]},{coords[1]},0"

    elif gtype == "LineString":
        ls = ET.SubElement(parent, "LineString")
        c = ET.SubElement(ls, "coordinates")
        c.text = " ".join(f"{p[0]},{p[1]},0" for p in coords)

    elif gtype == "Polygon":
        poly = ET.SubElement(parent, "Polygon")
        outer = ET.SubElement(poly, "outerBoundaryIs")
        lr = ET.SubElement(outer, "LinearRing")
        c = ET.SubElement(lr, "coordinates")
        outer_coords = coords[0] if coords else []
        c.text = " ".join(f"{p[0]},{p[1]},0" for p in outer_coords)
        for ring in coords[1:]:
            inner = ET.SubElement(poly, "innerBoundaryIs")
            lr2 = ET.SubElement(inner, "LinearRing")
            c2 = ET.SubElement(lr2, "coordinates")
            c2.text = " ".join(f"{p[0]},{p[1]},0" for p in ring)

    elif gtype == "MultiPolygon":
        mg = ET.SubElement(parent, "MultiGeometry")
        for poly_coords in coords:
            poly = ET.SubElement(mg, "Polygon")
            outer = ET.SubElement(poly, "outerBoundaryIs")
            lr = ET.SubElement(outer, "LinearRing")
            c = ET.SubElement(lr, "coordinates")
            outer_c = poly_coords[0] if poly_coords else []
            c.text = " ".join(f"{p[0]},{p[1]},0" for p in outer_c)
            for ring in poly_coords[1:]:
                inner = ET.SubElement(poly, "innerBoundaryIs")
                lr2 = ET.SubElement(inner, "LinearRing")
                c2 = ET.SubElement(lr2, "coordinates")
                c2.text = " ".join(f"{p[0]},{p[1]},0" for p in ring)


def write_fiona(layer: dict, filepath: str, driver: str):
    """LayerData → vector file through pyogrio's compact GDAL runtime.

    The historical function name is retained to keep older callers working.
    Native styled TAB output now goes through ``mapinfo_writer``; this function
    is primarily the SHP writer.
    """
    import numpy as np
    import pyogrio.raw
    from shapely import to_wkb
    from shapely.geometry import shape

    features = layer["features"]
    if not features:
        return {}

    meta = layer["metadata"]
    field_names = _build_field_name_map(features, driver)

    # Infer a stable type for each output column.
    schema_props = {}
    for feat in features:
        for key, val in feat.get("properties", {}).items():
            safe_key = field_names[str(key)]
            if val is None:
                continue
            ftype = _infer_fiona_type(val)
            schema_props[safe_key] = _merge_fiona_types(schema_props.get(safe_key), ftype)

    # 全为空的字段仍保留为文本字段。
    for safe_key in field_names.values():
        schema_props.setdefault(safe_key, "str:254")

    crs = meta.get("source_crs") or "EPSG:4326"

    geometries = []
    for feat in features:
        geom = feat.get("geometry")
        geometries.append(shape(geom) if isinstance(geom, dict) else geom)
    geometry_wkb = np.asarray(to_wkb(geometries), dtype=object)

    ordered_fields = list(schema_props)
    field_data = []
    field_masks = []
    original_by_safe = {safe: original for original, safe in field_names.items()}
    for safe_name in ordered_fields:
        original = original_by_safe[safe_name]
        expected = schema_props[safe_name]
        raw_values = [feat.get("properties", {}).get(original) for feat in features]
        mask = np.asarray([_is_null_value(value) for value in raw_values], dtype=bool)
        if expected == "int":
            values = np.asarray([
                0 if missing else int(_cast_value(value, expected))
                for value, missing in zip(raw_values, mask)
            ], dtype=np.int64)
        elif expected == "float":
            values = np.asarray([
                np.nan if missing else float(_cast_value(value, expected))
                for value, missing in zip(raw_values, mask)
            ], dtype=np.float64)
        else:
            values = np.asarray([
                "" if missing else str(_cast_value(value, expected))
                for value, missing in zip(raw_values, mask)
            ], dtype=object)
        field_data.append(values)
        field_masks.append(mask)

    pyogrio.raw.write(
        filepath,
        geometry_wkb,
        field_data,
        np.asarray(ordered_fields, dtype=object),
        field_mask=field_masks,
        driver=driver,
        geometry_type=_infer_geom_type(features),
        crs=crs,
        encoding="GBK" if "Shapefile" in driver else "CP936",
    )

    return {safe: original for original, safe in field_names.items() if safe != original}


def _is_null_value(value):
    import numpy as np
    import pandas as pd
    if value is None:
        return True
    try:
        missing = pd.isna(value)
        return bool(missing) if np.isscalar(missing) else False
    except Exception:
        return False


def _build_field_name_map(features: list, driver: str) -> dict:
    """一次性生成稳定且不冲突的输出字段名。"""
    result = {}
    used = set()
    for feat in features:
        for key in feat.get("properties", {}):
            original = str(key)
            if original in result:
                continue
            base = _safe_field_name(original, driver)
            candidate = _fit_field_name(base, "", driver)
            index = 2
            while candidate.casefold() in used:
                suffix = f"_{index}"
                candidate = _fit_field_name(base, suffix, driver)
                index += 1
            result[original] = candidate
            used.add(candidate.casefold())
    return result


def _fit_field_name(base: str, suffix: str, driver: str) -> str:
    if "Shapefile" not in driver:
        return base[:31 - len(suffix)] + suffix
    budget = 10 - len(suffix.encode("ascii"))
    data = base.encode("gbk", errors="replace")[:budget]
    while data:
        try:
            return data.decode("gbk") + suffix
        except UnicodeDecodeError:
            data = data[:-1]
    return "field"[:10 - len(suffix)] + suffix

def _safe_field_name(name: str, driver: str) -> str:
    """生成 Fiona-safe 字段名"""
    s = str(name).strip()
    if not s:
        return 'unnamed'
    if "Shapefile" in driver:
        # dBASE 字段名上限为 10 字节；按 GBK 安全截断。
        data = s.encode("gbk", errors="replace")[:10]
        while data:
            try:
                return data.decode("gbk")
            except UnicodeDecodeError:
                data = data[:-1]
        return "field"
    if "MapInfo" in driver:
        return s[:31]
    return s


def _to_ascii_field(name):
    """Backward-compatible name; modern TAB keeps Chinese identifiers."""
    return str(name).strip()[:31] or "字段"


def _to_pinyin_abbr(chinese_str):
    return str(chinese_str).strip()[:10]

def _infer_fiona_type(value: Any) -> str:
    """推断 Fiona 字段类型"""
    if isinstance(value, bool):
        return "str:254"
    elif isinstance(value, numbers.Integral):
        return "int"
    elif isinstance(value, numbers.Real):
        return "float"
    else:
        return "str:254"


def _merge_fiona_types(current: str | None, new: str) -> str:
    if current is None or current == new:
        return new
    if current.startswith("str") or new.startswith("str"):
        return "str:254"
    if "float" in (current, new):
        return "float"
    return "int"


def _infer_geom_type(features: list) -> str:
    """推断主导几何类型，混合时使用最高兼容类型"""
    types = set()
    for f in features:
        g = f.get("geometry", {})
        if g.get("type"):
            types.add(g["type"])
    if not types:
        return "Unknown"
    if len(types) == 1:
        return types.pop()
    # 混合类型：用最高兼容类型
    if "MultiPolygon" in types or "Polygon" in types:
        return "MultiPolygon"
    if "MultiLineString" in types or "LineString" in types:
        return "MultiLineString"
    if "MultiPoint" in types or "Point" in types:
        return "MultiPoint"
    return list(types)[0]


def _cast_value(value: Any, target_type: str) -> Any:
    """类型转换"""
    if value is None:
        return ""
    if target_type.startswith("str"):
        return str(value)
    elif target_type == "int":
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return 0
    elif target_type == "float":
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return 0.0
    return str(value)


def write_shp(layer: dict, filepath: str):
    """LayerData → SHP"""
    write_fiona(layer, filepath, "ESRI Shapefile")


def write_tab(layer: dict, filepath: str):
    """LayerData → TAB"""
    write_fiona(layer, filepath, "MapInfo File")


# ============================================================
# 格式互转入口
# ============================================================
def convert_format(input_path: str, output_path: str,
                   auto_detect_encoding: bool = True,
                   name_field: str = None) -> dict:
    """
    格式互转主函数。

    参数:
        input_path:  输入文件路径
        output_path: 输出文件路径（扩展名决定目标格式）
    返回:
        {"success": True/False, "message": "...", "output": "..."}
    """
    try:
        layer = read_layer(input_path, auto_detect_encoding)

        out_ext = os.path.splitext(output_path)[1].lower()
        if out_ext in (".kml", ".ovkml"):
            write_kml(layer, output_path)
        elif out_ext == ".shp":
            write_shp(layer, output_path)
        elif out_ext == ".tab":
            write_tab(layer, output_path)
        else:
            return {"success": False, "message": f"不支持的目标格式: {out_ext}", "output": None}

        return {
            "success": True,
            "message": f"✅ {os.path.basename(input_path)} → {os.path.basename(output_path)} "
                       f"({layer['metadata']['feature_count']} 个要素)",
            "output": output_path,
        }
    except Exception as e:
        return {"success": False, "message": f"❌ 转换失败: {e}", "output": None}

