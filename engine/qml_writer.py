# -*- coding: utf-8 -*-
"""
QGIS .qml 样式文件生成器
SHP 格式不存样式，生成 .qml 让 QGIS 自动着色
"""
import os


def write_qml_style(output_path, layer_name, geom_type, level_colors, level_field):
    """分级渲染 QML"""
    if not output_path.lower().endswith('.qml'):
        output_path = os.path.splitext(output_path)[0] + '.qml'
    qml = _build_qml_categorized(layer_name, geom_type, level_colors, level_field)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(qml)


def write_qml_sector_style(output_path, layer_name, sector_colors):
    """扇区固定配色 QML"""
    if not output_path.lower().endswith('.qml'):
        output_path = os.path.splitext(output_path)[0] + '.qml'
    qml = _build_qml_sector(layer_name, sector_colors)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(qml)


def _build_qml_categorized(layer_name, geom_type, level_colors, level_field):
    sym_type = _qml_symbol_type(geom_type)
    layer_class = _qml_layer_class(geom_type)

    categories = ''
    for idx, (low, high, hex_color) in enumerate(level_colors):
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        label = f'{int(low)}~{int(high)}'
        categories += f'''
        <category symbol="{idx}" value="{low}-{high}" label="{label}" render="true">
          <symbol type="{sym_type}" alpha="0.7">
            <layer class="{layer_class}">
              <prop k="color" v="{r},{g},{b},180"/>
              <prop k="outline_color" v="{r},{g},{b},255"/>
              <prop k="outline_width" v="0"/>
              <prop k="outline_style" v="solid"/>
            </layer>
          </symbol>
        </category>'''

    return f'''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.28.0" styleCategories="Symbology">
  <renderer-v2 type="categorizedSymbol" attr="{level_field}" symbollevels="0">
    {categories}
  </renderer-v2>
  <layerGeometryType>{_qml_geom_id(geom_type)}</layerGeometryType>
</qgis>'''


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
