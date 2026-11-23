"""Behavioral regressions also exercised inside the frozen executable."""
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

def _check(condition, message='V1.3 regression check failed'):
    if not condition:
        raise AssertionError(message)

def run_checks(output_dir):
    import numpy as np
    import pandas as pd
    from PySide6.QtGui import QImage
    from tabs.drive_tab import DriveTab
    from tabs.grid_tab import GridTab
    from widgets.level_editor import LevelEditor
    from utils.constants import LEVEL_COLORS_6, LEVEL_COLORS_9
    from utils.level_scheme import LevelColors, validate_scheme, interval_label
    from engine.kml_writer import _get_hex_for_level
    from engine.mif_writer import _map_colors
    from engine.layer_engine import generate_drive_layer, generate_grid_layer
    folder = Path(output_dir) / 'v13'
    folder.mkdir(parents=True, exist_ok=True)
    checks = {}
    for preset in (LEVEL_COLORS_6, LEVEL_COLORS_9):
        for boundary in ('right', 'left'):
            colors = validate_scheme(preset, boundary)
            for i in range(len(colors) - 1):
                value = colors[i][1]
                expected = colors[i if boundary == 'right' else i + 1][2]
                _check(_get_hex_for_level(value, colors) == expected, 'V1.3 regression check failed')
                _check(int(_map_colors(np.array([value]), colors)[0]) == int(expected[1:], 16), 'V1.3 regression check failed')
                for delta, band in ((-0.001, i), (0.001, i + 1)):
                    _check(_get_hex_for_level(value + delta, colors) == colors[band][2], 'V1.3 regression check failed')
    checks['all_preset_boundaries'] = True
    for rows in ([[-float('inf'), -100, '#ff0000'], [-99, float('inf'), '#00ff00']], [[-float('inf'), -100, '#ff0000'], [-101, float('inf'), '#00ff00']], [[-120, -100, '#ff0000'], [-100, float('inf'), '#00ff00']]):
        try:
            validate_scheme(rows)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid intervals accepted')
    checks['gap_overlap_finite_tail_rejected'] = True
    for cls in (DriveTab, GridTab):
        tab = cls()
        for index in (1, 0, 1, 0):
            tab.preset_combo.setCurrentIndex(index)
            _check(len(tab._color_btns) == len(tab.style['level_colors']), 'V1.3 regression check failed')
            for button, (lo, hi, color) in zip(tab._color_btns, tab.style['level_colors']):
                _check(button.toolTip() == interval_label(lo, hi), 'V1.3 regression check failed')
        tab.boundary_combo.setCurrentIndex(1)
        _check(tab.get_current_colors().boundary == 'left', 'V1.3 regression check failed')
        _check('≤' in tab._color_btns[-1].toolTip() or '≥' in tab._color_btns[-1].toolTip(), 'V1.3 regression check failed')
    editor = LevelEditor(LEVEL_COLORS_9)
    editor.table.setCurrentCell(2, 1)
    editor.split_band()
    _check(len(editor.values()) == 10, 'V1.3 regression check failed')
    editor.merge_band()
    _check(len(editor.values()) == 9, 'V1.3 regression check failed')
    checks['dynamic_buttons_and_editor'] = True
    metric = 'SS-"RSRP&<测试>'
    df = pd.DataFrame({'lon': [108.37, 108.38, 108.39], 'lat': [22.8, 22.81, 22.82], metric: [-120.0, -100.0, -80.0]})
    mapping = {'lon': 'lon', 'lat': 'lat', 'level': metric}
    colors = LevelColors([(-float('inf'), -100, '#AB12CD'), (-100, float('inf'), '#34EF56')], 'left')
    extra = {'level_colors': colors, 'show_label': True}
    ns = {'k': 'http://www.opengis.net/kml/2.2'}
    kml = folder / '带空格 路测.kml'
    _check(generate_drive_layer(df, mapping, {}, str(kml), extra=extra) == 3, 'V1.3 regression check failed')
    root = ET.parse(kml).getroot()
    _check(len(root.findall('.//k:ScreenOverlay', ns)) == 1, 'V1.3 regression check failed')
    names = root.findall('.//k:Placemark/k:name', ns)
    _check(len(names) == 3, 'V1.3 regression check failed')
    _check(root.find('.//k:Data', ns).get('name') == metric, 'V1.3 regression check failed')
    styles = [node.text for node in root.findall('.//k:IconStyle/k:color', ns)]
    _check('CCCD12AB' in styles and 'CC56EF34' in styles, 'V1.3 regression check failed')
    _check(len(root.findall('.//k:Placemark/k:styleUrl', ns)) == 3, 'V1.3 regression check failed')
    _check(root.findall('.//k:Placemark/k:styleUrl', ns)[1].text == '#s1', 'V1.3 regression check failed')
    image = QImage(str(kml.with_name(kml.stem + '_kml_legend.png')))
    _check(not image.isNull() and image.pixelColor(40, 140).name().upper() == '#34EF56', 'V1.3 regression check failed')
    checks['custom_kml_colors_labels_png_and_special_field'] = True
    for tiled in (False, True):
        target = folder / ('tiled.kmz' if tiled else 'normal.kmz')
        sibling = target.with_suffix('.kml')
        sibling.write_bytes(b'KEEP EXISTING KML')
        params = dict(extra)
        if tiled:
            params.update(regionate_threshold=1, points_per_tile=1)
        generate_drive_layer(df, mapping, {}, str(target), extra=params)
        _check(sibling.read_bytes() == b'KEEP EXISTING KML', 'V1.3 regression check failed')
        with zipfile.ZipFile(target) as archive:
            _check(archive.testzip() is None, 'V1.3 regression check failed')
            _check({'files/legend.png', 'files/point.png'} <= set(archive.namelist()), 'V1.3 regression check failed')
            count, overlays = (0, 0)
            for name in archive.namelist():
                if not name.endswith('.kml'):
                    continue
                data = archive.read(name)
                _check(b'http://maps.google.com' not in data, 'V1.3 regression check failed')
                doc = ET.fromstring(data)
                count += len(doc.findall('.//k:Placemark/k:name', ns))
                overlays += len(doc.findall('.//k:ScreenOverlay', ns))
                for node in doc.findall('.//k:Data', ns):
                    _check(node.get('name') == metric, 'V1.3 regression check failed')
            _check(count == 3 and overlays == 1, 'V1.3 regression check failed')
        try:
            generate_drive_layer(df, mapping, {}, str(target), extra=params)
        except FileExistsError:
            pass
        else:
            raise AssertionError('Existing KMZ silently overwritten')
    checks['normal_tiled_kmz_offline_overlay_labels_no_clobber'] = True
    target = folder / 'grid.kmz'
    sibling = target.with_suffix('.kml')
    sibling.write_bytes(b'KEEP GRID SIBLING')
    generate_grid_layer(df, mapping, {}, str(target), extra={'level_colors': colors})
    _check(sibling.read_bytes() == b'KEEP GRID SIBLING', 'V1.3 regression check failed')
    with zipfile.ZipFile(target) as archive:
        ET.fromstring(archive.read('doc.kml'))
    _check(not list(folder.glob('.plc_*')), 'V1.3 regression check failed')
    checks['grid_kmz_preserves_sibling_and_cleans_staging'] = True
    from engine.qml_writer import write_qml_style
    for boundary in ('right', 'left'):
        scheme = validate_scheme(LEVEL_COLORS_9, boundary)
        path = folder / f'style_{boundary}.qml'
        write_qml_style(str(path), '路测', 'point', scheme, metric)
        root = ET.parse(path).getroot()
        rules = root.findall('.//rules/rule')
        _check(len(rules) == 9 and len(root.findall('.//symbols/symbol')) == 9, 'V1.3 regression check failed')
        _check(root.find('layerGeometryType').text == '0', 'V1.3 regression check failed')
        _check(rules[0].get('filter').endswith('<= -120' if boundary == 'right' else '< -120'), 'V1.3 regression check failed')
        _check(rules[-1].get('filter').endswith('> -80' if boundary == 'right' else '>= -80'), 'V1.3 regression check failed')
    checks['qml_infinite_bounds_and_exact_interval_rules'] = True
    return checks
