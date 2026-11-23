# -*- coding: utf-8 -*-
"""
QGIS .qml 样式文件生成器
SHP 格式不存样式，生成 .qml 让 QGIS 自动着色
"""
import os


def write_qml_style(output_path, layer_name, geom_type, level_colors, level_field, options=None):
    """分级渲染 QML"""
    if not output_path.lower().endswith('.qml'):
        output_path = os.path.splitext(output_path)[0] + '.qml'
    qml = _build_qml_categorized(layer_name, geom_type, level_colors, level_field, options)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(qml)


def write_qml_sector_style(output_path, layer_name, sector_colors):
    """扇区固定配色 QML"""
    if not output_path.lower().endswith('.qml'):
        output_path = os.path.splitext(output_path)[0] + '.qml'
    qml = _build_qml_sector(layer_name, sector_colors)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(qml)


def _build_qml_categorized(layer_name, geom_type, level_colors, level_field, options=None):
    options=options or {}
    # Rules express both interval conventions exactly; categories cannot match ranges.
    import math
    import xml.etree.ElementTree as ET
    from utils.level_scheme import interval_label
    kind = {'point': 'Point', 'line': 'LineString', 'polygon': 'Polygon'}.get(geom_type, geom_type)
    root = ET.Element('qgis', version='3.28.0', styleCategories='Symbology')
    renderer = ET.SubElement(root, 'renderer-v2', type='RuleRenderer', symbollevels='0')
    rules = ET.SubElement(renderer, 'rules')
    symbols = ET.SubElement(renderer, 'symbols')
    boundary = getattr(level_colors, 'boundary', 'right')
    field = '"' + str(level_field).replace('"', '""') + '"'
    for index, (low, high, color) in enumerate(level_colors):
        filters = []
        if math.isfinite(low): filters.append(f'{field} {">=" if boundary == "left" else ">"} {low:g}')
        if math.isfinite(high): filters.append(f'{field} {"<" if boundary == "left" else "<="} {high:g}')
        ET.SubElement(rules, 'rule', symbol=str(index), filter=' AND '.join(filters) or 'TRUE',
                      label=interval_label(low, high, boundary, str(level_field)))
        symbol = ET.SubElement(symbols, 'symbol', name=str(index), type=_qml_symbol_type(kind), alpha='1')
        layer = ET.SubElement(symbol, 'layer', **{'class': _qml_layer_class(kind), 'enabled': '1', 'pass': '0'})
        rgba = ','.join(str(int(color[i:i+2], 16)) for i in (1, 3, 5)) + ',' + str(round(255*(1-float(options.get('transparency',20))/100)) if options.get('fill_enabled',True) else 0)
        border=options.get('border_color','#000000')
        border_rgba=','.join(str(int(border[i:i+2],16)) for i in (1,3,5))+',255'
        props={'color':rgba,'outline_style':'solid' if options.get('outline_enabled',True) else 'no',
               'outline_color':border_rgba,'outline_width':str(options.get('border_width',1)),
               'outline_width_unit':'Pixel','size':str(2*float(options.get('scale',1))),
               'style':'solid' if options.get('fill_enabled',True) else 'no'}
        if kind == 'Point': props['name'] = 'circle'
        for key, value in props.items(): ET.SubElement(layer, 'prop', k=key, v=value)
    ET.SubElement(root, 'layerGeometryType').text = _qml_geom_id(kind)
    return ET.tostring(root, encoding='unicode')


def _build_qml_sector(layer_name, sector_colors):
    """sector_colors: {1: '#FF0000', 2: '#00FF00', ...}"""
    categories = ''
    for sec_num, hex_color in sector_colors.items():
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        categories += f'''
        <category symbol="{sec_num}" value="{sec_num}" label="扇区{sec_num}" render="true">
          <symbol type="fill" alpha="0.5">
            <layer class="SimpleFill">
              <prop k="color" v="{r},{g},{b},128"/>
              <prop k="outline_color" v="{r},{g},{b},255"/>
              <prop k="outline_width" v="0"/>
              <prop k="outline_style" v="solid"/>
            </layer>
          </symbol>
        </category>'''

    return f'''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.28.0" styleCategories="Symbology">
  <renderer-v2 type="categorizedSymbol" attr="_SectorNumber" symbollevels="0">
    {categories}
  </renderer-v2>
  <layerGeometryType>2</layerGeometryType>
</qgis>'''


def _qml_symbol_type(geom_type):
    return {'Point': 'marker', 'LineString': 'line', 'Polygon': 'fill'}.get(geom_type, 'fill')


def _qml_layer_class(geom_type):
    return {'Point': 'SimpleMarker', 'LineString': 'SimpleLine', 'Polygon': 'SimpleFill'}.get(geom_type, 'SimpleFill')


def _qml_geom_id(geom_type):
    return {'Point': '0', 'LineString': '1', 'Polygon': '2'}.get(geom_type, '2')
