# -*- coding: utf-8 -*-
"""源码和冻结 EXE 共用的内部回归测试。"""
import json
import os
import tempfile
import traceback
import zipfile


def _verify_vector(path, expected_count, expected_geometry):
    import pyogrio
    info = pyogrio.read_info(path)
    count = int(info["features"])
    actual = str(info.get("geometry_type", ""))
    if count != expected_count:
        raise AssertionError(f"{path}: expected {expected_count}, got {count}")
    if expected_geometry not in actual and actual != "Unknown":
        raise AssertionError(f"{path}: expected {expected_geometry}, geometry={actual}")
    return {"count": count, "geometry": actual, "fields": list(info["fields"])}


def run_self_test(output_dir=None):
    output_dir = output_dir or tempfile.mkdtemp(prefix="PlanLayerCreator_selftest_")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "self_test.json")
    report = {"success": False, "output_dir": output_dir, "checks": {}}

    try:
        from PySide6.QtWidgets import QApplication, QLabel
        from PySide6.QtGui import QIcon, QPixmap
        app = QApplication.instance() or QApplication([])
        icon = QIcon(":/res/icon.ico")
        qr = QPixmap(":/res/qrcode.jpg")
        if icon.isNull() or qr.isNull():
            raise AssertionError("embedded icon or QR code is unavailable")
        report["checks"]["embedded_resources"] = {"qr": [qr.width(), qr.height()]}

        # 加载并实例化全部界面，覆盖 Qt 插件和延迟导入。
        from tabs.site_tab import SiteTab
        from tabs.sector_tab import SectorTab
        from tabs.drive_tab import DriveTab
        from tabs.grid_tab import GridTab
        from tabs.line_tab import LineTab
        from tabs.polygon_tab import PolygonTab
        from tabs.help_tab import HelpTab
        help_widget = HelpTab()
        widgets = [SiteTab(), SectorTab(), DriveTab(), GridTab(), LineTab(), PolygonTab(), help_widget]
        app.processEvents()
        report["checks"]["ui_tabs"] = len(widgets)
        help_text = help_widget.browser.toPlainText()
        required_help_terms = (
            "原生着色 TAB", "中文属性", "MapInfo 15.2+", "轻量 KML/KMZ",
            "最少样本数", "同名 .wor",
        )
        missing_help_terms = [term for term in required_help_terms if term not in help_text]
        qr_widget = help_widget.findChild(QLabel, "helpQrCode")
        if missing_help_terms or qr_widget is None or qr_widget.pixmap().isNull():
            raise AssertionError(
                "help content/resource check failed: " + ", ".join(missing_help_terms)
            )
        report["checks"]["help_page"] = {
            "required_terms": list(required_help_terms),
            "characters": len(help_text),
            "qr_loaded": True,
        }

        import pandas as pd
        import pyogrio
        import pyogrio.raw
        from engine.layer_engine import (
            generate_site_layer, generate_sector_layer, generate_drive_layer,
            generate_grid_layer, generate_wkt_layer,
        )

        if "MapInfo File" not in pyogrio.list_drivers():
            raise AssertionError("GDAL MapInfo File driver is unavailable")

        site_df = pd.DataFrame({
            "站点名称": ["北京测试站", "上海测试站"],
            "经度": [116.397, 121.473],
            "纬度": [39.908, 31.230],
            "数值": [1.5, 2.5],
            "超长字段名称甲": ["甲", "乙"],
            "超长字段名称乙": ["丙", "丁"],
        })
        mapping = {"lon": "经度", "lat": "纬度", "name": "站点名称", "label": "站点名称"}
        style = {"icon_color": "#0078FF", "label_color": "#FF0000", "scale": 1.0, "show_label": True}
        paths = {ext: os.path.join(output_dir, "site" + ext) for ext in (".kml", ".kmz", ".shp", ".tab")}
        for path in paths.values():
            generate_site_layer(site_df.copy(), mapping, style, path)
        if not os.path.isfile(paths[".kml"]):
            raise AssertionError("KML was not created")
        with zipfile.ZipFile(paths[".kmz"], "r") as archive:
            if not any(name.lower().endswith(".kml") for name in archive.namelist()):
                raise AssertionError("KMZ does not contain KML")
        report["checks"]["site_shp"] = _verify_vector(paths[".shp"], 2, "Point")
        report["checks"]["site_tab"] = _verify_vector(paths[".tab"], 2, "Point")
        raw_meta, _, _, raw_fields = pyogrio.raw.read(paths[".tab"])
        tab_fields = list(raw_meta["fields"])
        site_name_index = tab_fields.index("站点名称") if "站点名称" in tab_fields else -1
        if site_name_index < 0 or raw_fields[site_name_index][0] != "北京测试站":
            raise AssertionError("TAB Chinese field name/value roundtrip failed")
        from engine.gdal_runtime import first_feature_style
        if "SYMBOL" not in first_feature_style(paths[".tab"]).upper():
            raise AssertionError("site TAB point style is missing")

        sector_df = pd.DataFrame({
            "小区名称": ["小区A"], "经度": [116.40], "纬度": [39.90], "方位角": [30.0]
        })
        sector_mapping = {"lon": "经度", "lat": "纬度", "name": "小区名称", "azimuth": "方位角"}
        sector_style = {"colors": {1: "#FF0000", 2: "#00FF00", 3: "#0000FF"}}
        sector_tab = os.path.join(output_dir, "sector.tab")
        sector_shp = os.path.join(output_dir, "sector.shp")
        generate_sector_layer(sector_df.copy(), sector_mapping, sector_style, sector_tab)
        generate_sector_layer(sector_df.copy(), sector_mapping, sector_style, sector_shp)
        report["checks"]["sector_tab"] = _verify_vector(sector_tab, 1, "Polygon")
        report["checks"]["sector_shp"] = _verify_vector(sector_shp, 1, "Polygon")
        sector_style_text = first_feature_style(sector_tab).upper()
        if "BRUSH" not in sector_style_text or "PEN" not in sector_style_text:
            raise AssertionError("sector TAB fill/outline style is missing")

        line_df = pd.DataFrame({"名称": ["测试线"], "WKT": ["LINESTRING (116.4 39.9, 116.5 40.0)"]})
        line_tab = os.path.join(output_dir, "line.tab")
        line_shp = os.path.join(output_dir, "line.shp")
        line_mapping = {"wkt_col": "WKT", "type_col": "名称"}
        generate_wkt_layer(line_df, line_mapping, {}, line_tab)
        generate_wkt_layer(line_df, line_mapping, {}, line_shp)
        report["checks"]["line_tab"] = _verify_vector(line_tab, 1, "LineString")
        report["checks"]["line_shp"] = _verify_vector(line_shp, 1, "LineString")
        if "PEN" not in first_feature_style(line_tab).upper():
            raise AssertionError("line TAB pen style is missing")

        polygon_df = pd.DataFrame({
            "名称": ["测试面"],
            "WKT": ["POLYGON ((116.4 39.9, 116.5 39.9, 116.5 40.0, 116.4 40.0, 116.4 39.9))"],
        })
        polygon_tab = os.path.join(output_dir, "polygon.tab")
        polygon_shp = os.path.join(output_dir, "polygon.shp")
        generate_wkt_layer(polygon_df, line_mapping, {}, polygon_tab)
        generate_wkt_layer(polygon_df, line_mapping, {}, polygon_shp)
        report["checks"]["polygon_tab"] = _verify_vector(polygon_tab, 1, "Polygon")
        report["checks"]["polygon_shp"] = _verify_vector(polygon_shp, 1, "Polygon")
        if "BRUSH" not in first_feature_style(polygon_tab).upper():
            raise AssertionError("polygon TAB brush style is missing")

        drive_df = pd.DataFrame({
            "经度": [116.4, 116.401], "纬度": [39.9, 39.901],
            "RSRP": [-95.0, -105.0], "地市": ["北京", "北京"],
        })
        drive_mif = os.path.join(output_dir, "drive.mif")
        generate_drive_layer(drive_df, {"lon": "经度", "lat": "纬度", "level": "RSRP"}, {}, drive_mif)
        if not os.path.isfile(drive_mif) or not os.path.isfile(os.path.join(output_dir, "drive.mid")):
            raise AssertionError("drive MIF/MID was not created")
        drive_tab = os.path.join(output_dir, "drive.tab")
        generate_drive_layer(drive_df, {"lon": "经度", "lat": "纬度", "level": "RSRP"}, {}, drive_tab)
        report["checks"]["drive_tab"] = _verify_vector(drive_tab, 2, "Point")
        if "SYMBOL" not in first_feature_style(drive_tab).upper():
            raise AssertionError("drive TAB classified symbol style is missing")
        drive_kmz = os.path.join(output_dir, "drive_light.kmz")
        generate_drive_layer(
            drive_df, {"lon": "经度", "lat": "纬度", "level": "RSRP"}, {}, drive_kmz,
            extra={"regionate_threshold": 1, "points_per_tile": 1},
        )
        with zipfile.ZipFile(drive_kmz, "r") as archive:
            payload = b"".join(
                archive.read(name) for name in archive.namelist() if name.startswith("tiles/")
            )
            if b"RSRP" not in payload or "地市".encode("utf-8") in payload:
                raise AssertionError("drive KMZ is not using the signal-only lightweight schema")

        grid_mif = os.path.join(output_dir, "grid.mif")
        generate_grid_layer(drive_df, {"lon": "经度", "lat": "纬度", "level": "RSRP"}, {}, grid_mif)
        if not os.path.isfile(grid_mif) or not os.path.isfile(os.path.join(output_dir, "grid.mid")):
            raise AssertionError("grid MIF/MID was not created")
        grid_tab = os.path.join(output_dir, "grid.tab")
        grid_count = generate_grid_layer(drive_df, {"lon": "经度", "lat": "纬度", "level": "RSRP"}, {}, grid_tab)
        report["checks"]["grid_tab"] = _verify_vector(grid_tab, grid_count, "Polygon")
        if "BRUSH" not in first_feature_style(grid_tab).upper():
            raise AssertionError("grid TAB classified fill style is missing")
        grid_kmz = os.path.join(output_dir, "grid_light.kmz")
        generate_grid_layer(drive_df, {"lon": "经度", "lat": "纬度", "level": "RSRP"}, {}, grid_kmz)
        with zipfile.ZipFile(grid_kmz, "r") as archive:
            payload = b"".join(archive.read(name) for name in archive.namelist())
            if b"RSRP" not in payload or "地市".encode("utf-8") in payload:
                raise AssertionError("grid KMZ is not using the signal-only lightweight schema")
        report["checks"]["mif_mid"] = True

        xlsx_path = os.path.join(output_dir, "input.xlsx")
        site_df.to_excel(xlsx_path, index=False)
        loaded = pd.read_excel(xlsx_path)
        if len(loaded) != len(site_df):
            raise AssertionError("Excel roundtrip failed")
        report["checks"]["excel"] = len(loaded)
        report["success"] = True
        code = 0
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()
        code = 1

    with open(report_path, "w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    return code
