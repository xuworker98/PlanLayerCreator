"""Regression checks for preview sizing and the revised help hierarchy."""
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


def run_checks(output_dir):
    import resources_rc  # noqa: F401 - also allow direct focused checks.
    import pandas as pd
    from PySide6.QtWidgets import QWidget, QLabel, QApplication
    from PySide6.QtGui import QImage
    from tabs.help_tab import HelpTab
    from tabs.drive_tab import DriveTab
    from engine.layer_engine import generate_drive_layer
    from engine.drive_export import overlay_xml
    from utils.constants import LEVEL_COLORS_6, LEVEL_COLORS_9

    def check(condition, message):
        if not condition: raise AssertionError(message)

    folder = Path(output_dir) / 'v14'
    folder.mkdir(parents=True, exist_ok=True)
    help_widget = HelpTab()
    help_widget.resize(1024, 680); help_widget.show()
    QApplication.processEvents()
    text = help_widget.browser.toPlainText()
    section4 = text.index('四、输出格式与属性')
    section5 = text.index('五、坐标与数据检查')
    check(section4 < text.index('9 档 · 路测默认') < section5, '9-band table outside chapter 4')
    check(section4 < text.index('6 档 · MR 默认') < section5, '6-band table outside chapter 4')
    check('覆盖描述' in text and '色值' in text, 'palette columns missing')
    check('路测图层的 KML/KMZ 格式支持图例' in text, 'legend wording changed')
    check('路测分档、边界与图例（V1.3）' not in text, 'old standalone section retained')
    for _, _, color in LEVEL_COLORS_6 + LEVEL_COLORS_9:
        check(color in text, 'help palette differs from default scheme')
    qr = help_widget.findChild(QLabel, 'helpQrCode')
    contact = help_widget.findChild(QWidget, 'helpContactText')
    check(contact.height() == qr.height() == 96, 'footer heights differ')
    check(contact.mapTo(help_widget, contact.rect().topLeft()).y() ==
          qr.mapTo(help_widget, qr.rect().topLeft()).y(), 'footer top edges differ')
    check(not qr.pixmap().isNull(), 'QR code missing')

    tab = DriveTab()
    check(tab.get_extra_params()['legend_width'] == 360, 'default width differs')
    df = pd.DataFrame({'经度': [108.37, 108.38], '纬度': [22.8, 22.81], 'SS-RSRP': [-120., -80.]})
    mapping = {'lon': '经度', 'lat': '纬度', 'level': 'SS-RSRP'}
    ns = {'k': 'http://www.opengis.net/kml/2.2'}
    for index, width in enumerate((300, 360, 420)):
        tab.legend_size_combo.setCurrentIndex(index)
        params = tab.get_extra_params()
        check(params['legend_width'] == width, 'UI width parameter lost')
        for suffix in ('.kml', '.kmz'):
            path = folder / f'legend_{width}_{suffix[1:]}{suffix}'
            count = generate_drive_layer(df, mapping, {}, str(path), extra=params)
            check(count == 2, 'wrong export count')
            if suffix == '.kml':
                root = ET.parse(path).getroot()
            else:
                with zipfile.ZipFile(path) as archive:
                    root = ET.fromstring(archive.read('route.kml'))
                    check(archive.testzip() is None, 'KMZ CRC failed')
            size = root.find('.//k:ScreenOverlay/k:size', ns)
            check(size is not None and int(size.get('x')) == width, 'overlay width not exported')
            check(int(size.get('y')) == round(646 * width / 600), 'image aspect ratio changed')
            image = QImage(str(path.with_name(path.stem + '_' + path.suffix[1:].lower() + '_legend.png')))
            check(image.size().width() == 600 and image.size().height() == 646, 'unexpected PNG size')
            check(image.pixelColor(40, 140 + 8 * 52).name().upper() == '#9B9B9B', 'default grey changed')
    try: overlay_xml('legend.png', 9, 0)
    except ValueError: pass
    else: raise AssertionError('invalid legend width accepted')
    help_widget.close()
    return {'help_hierarchy_and_palette': True, 'contact_qr_alignment': True,
            'three_legend_sizes_kml_kmz': True, 'default_gray_preserved': True}
