"""Behavioral regression checks for the V1.4.1 maintenance release."""
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import hashlib

def _check(condition, message):
    if not condition:
        raise AssertionError(message)

def run_checks(output_dir):
    import numpy as np
    import pandas as pd
    import pyogrio.raw
    from shapely import from_wkb, get_coordinates
    from PySide6.QtWidgets import QApplication
    from tabs.polygon_tab import PolygonTab
    from engine.layer_engine import generate_drive_layer, generate_wkt_layer, _apply_coord_correction
    from engine.mapinfo_writer import write_styled_mif
    from engine.gdal_runtime import first_feature_style
    from utils.gcj02 import wgs84_to_gcj02, gcj02_to_wgs84
    from utils.level_scheme import LevelColors
    out = Path(output_dir) / 'v141'
    out.mkdir(parents=True, exist_ok=True)
    ns = {'k': 'http://www.opengis.net/kml/2.2'}
    df = pd.DataFrame({'lon': [108.37, 108.38], 'lat': [22.8, 22.81], 'level': [-120.0, -80.0]})
    mapping = {'lon': 'lon', 'lat': 'lat', 'level': 'level'}
    for order in [('kmz', 'kml'), ('kml', 'kmz')]:
        stem = 'order_' + '_'.join(order)
        saved = {}
        for i, ext in enumerate(order):
            scheme = LevelColors([(-float('inf'), -100, '#FF0000' if i == 0 else '#FFFF00'), (-100, float('inf'), '#007D00')], 'right')
            target = out / (stem + '.' + ext)
            _check(generate_drive_layer(df, mapping, {}, str(target), extra={'level_colors': scheme}) == 2, 'V1.4.1 regression failed')
            legend = out / (stem + '_' + ext + '_legend.png')
            _check(legend.is_file(), 'V1.4.1 regression failed')
            saved[legend] = hashlib.sha256(legend.read_bytes()).hexdigest()
            for previous, digest in saved.items():
                _check(hashlib.sha256(previous.read_bytes()).hexdigest() == digest, 'V1.4.1 regression failed')
        root = ET.parse(out / (stem + '.kml')).getroot()
        from urllib.parse import unquote
        for node in root.findall('.//k:Icon/k:href', ns):
            _check((out / unquote(node.text)).is_file(), 'V1.4.1 regression failed')
        try:
            generate_drive_layer(df, mapping, {}, str(target))
        except FileExistsError:
            pass
        else:
            raise AssertionError('Existing output was overwritten')
    original = (108.37, 22.8)
    gcj = wgs84_to_gcj02(*original)
    _check(max((abs(a - b) for a, b in zip(gcj02_to_wgs84(*gcj), original))) < 2e-08, 'V1.4.1 regression failed')
    _check(gcj02_to_wgs84(-73.98, 40.75) == (-73.98, 40.75), 'V1.4.1 regression failed')
    gcjdf = pd.DataFrame({'lon': [gcj[0]], 'lat': [gcj[1]]})
    _check(_apply_coord_correction(gcjdf, 'lon', 'lat', False).equals(gcjdf), 'V1.4.1 regression failed')
    fixed = _apply_coord_correction(gcjdf, 'lon', 'lat', True)
    _check(np.max(np.abs(fixed[['lon', 'lat']].to_numpy() - np.asarray(original))) < 2e-08, 'V1.4.1 regression failed')
    tab = PolygonTab()
    tab.line_width_spin.setValue(3.5)
    tab.no_fill_check.setChecked(True)
    tab.no_outline_check.setChecked(True)
    params = tab.get_extra_params()
    _check(params['line_width'] == 3.5 and (not params['fill_enabled']) and (not params['outline_enabled']), 'V1.4.1 regression failed')
    poly = pd.DataFrame({'名称': ['测试面'], 'WKT': ['POLYGON ((108 22,109 22,109 23,108 23,108 22))']})
    for fill in (False, True):
        for outline in (False, True):
            style = {'fill_color': '#74b9ff', 'line_color': '#0984e3', 'line_width': 1}
            extra = {'fill_enabled': fill, 'outline_enabled': outline, 'line_width': 3.5}
            name = f'poly_{int(fill)}_{int(outline)}'
            for ext in ('kml', 'kmz', 'tab'):
                target = out / (name + '.' + ext)
                _check(generate_wkt_layer(poly, {'wkt_col': 'WKT', 'type_col': '名称'}, style, str(target), extra=extra) == 1, 'V1.4.1 regression failed')
                if ext == 'tab':
                    _check(len(pyogrio.raw.read(str(target))[2]) == 1, 'V1.4.1 regression failed')
                    actual_style = first_feature_style(str(target))
                    _check(f'mapinfo-brush-{(2 if fill else 1)},' in actual_style, 'V1.4.1 regression failed')
                    _check(f'mapinfo-pen-{(2 if outline else 1)},' in actual_style, 'V1.4.1 regression failed')
                else:
                    if ext == 'kmz':
                        with zipfile.ZipFile(target) as z:
                            root = ET.fromstring(z.read('doc.kml'))
                    else:
                        root = ET.parse(target).getroot()
                    _check(root.find('.//k:PolyStyle/k:fill', ns).text == str(int(fill)), 'V1.4.1 regression failed')
                    _check(root.find('.//k:PolyStyle/k:outline', ns).text == str(int(outline)), 'V1.4.1 regression failed')
                    _check(float(root.find('.//k:LineStyle/k:width', ns).text) == 3.5, 'V1.4.1 regression failed')
            from shapely.geometry import Polygon
            mif = out / (name + '.mif')
            write_styled_mif([{'geometry': Polygon([(108, 22), (109, 22), (109, 23), (108, 22)]), 'properties': {'名称': '测试面'}, 'style': {**style, **extra}}], str(mif))
            text = mif.read_text(encoding='gbk')
            _check(f'Pen (4,{(2 if outline else 1)},' in text, 'V1.4.1 regression failed')
            _check(f'Brush ({(2 if fill else 1)},' in text, 'V1.4.1 regression failed')
    complex_df = df.copy()
    complex_df['超长属性名称甲'] = ['南宁', None]
    complex_df['超长属性名称乙'] = ['甲', '乙']
    complex_df['整数'] = pd.Series([1, None], dtype='Int64')
    complex_df['布尔'] = [True, False]
    target = out / 'attributes.shp'
    generate_drive_layer(complex_df, mapping, {}, str(target))
    meta, _, geom, fields = pyogrio.raw.read(str(target))
    _check(len(geom) == 2 and len(set(meta['fields'])) == len(complex_df.columns), 'V1.4.1 regression failed')
    _check(np.array_equal(get_coordinates(from_wkb(geom)), df[['lon', 'lat']].to_numpy()), 'V1.4.1 regression failed')
    _check(any(('南宁' in list(values) for values in fields)), 'V1.4.1 regression failed')
    from widgets.worker_thread import GenerateWorker
    from engine.gdal_runtime import TAB_BACKEND
    import json
    selected = tab.format_combo.findText('TAB (快速，MapInfo 15.2+)')
    _check(selected >= 0, 'V1.4.1 regression failed')
    tab.format_combo.setCurrentIndex(selected)
    tab._on_gen_start()
    worker = GenerateWorker('site', df, {'lon': 'lon', 'lat': 'lat', 'name': 'level'}, tab.style, str(out / 'worker_fast.tab'))
    failures = []
    success = []
    worker.error.connect(failures.append)
    worker.finished.connect(success.append)
    worker.run()
    tab._on_gen_done()
    _check(success and (not failures), failures)
    record = json.loads((out / 'worker_fast_运行记录.txt').read_text(encoding='utf-8').strip().splitlines()[-1])
    _check(record['TAB实际后端'] == 'gdal' and record['输出要素数'] == 2, 'V1.4.1 regression failed')
    _check('耗时' in success[0], 'V1.4.1 regression failed')
    _check(TAB_BACKEND.get() is None, 'V1.4.1 regression failed')
    tab.close()
    return {'legend_both_orders_and_immutable_resources': True, 'coordinate_modes_roundtrip': True, 'polygon_four_style_combinations': True, 'polygon_width_propagation': True, 'shp_coordinates_nullable_chinese_fields': True}
