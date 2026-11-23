# -*- coding: utf-8 -*-
"""Concise, implementation-aligned help with a balanced contact footer."""
from html import escape
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTextBrowser, QVBoxLayout, QWidget
from utils.constants import LEVEL_COLORS_6, LEVEL_COLORS_9
from utils.level_scheme import interval_label


class HelpTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        self.browser = QTextBrowser()
        self.browser.setObjectName('helpBrowser')
        self.browser.setFrameShape(QTextBrowser.NoFrame)
        self.browser.setOpenExternalLinks(False)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.browser.setStyleSheet('QTextBrowser {background:#fff;border:1px solid #e0e6ec;border-radius:8px;padding:10px;color:#293744;}')
        self.browser.setHtml(self._help_html())
        layout.addWidget(self.browser, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(8, 0, 8, 0)
        footer.addStretch(1)
        card = QWidget()
        card.setObjectName('helpContactCard')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(4)
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(16)
        contact = QWidget()
        contact.setObjectName('helpContactText')
        contact.setFixedHeight(96)
        lines = QVBoxLayout(contact)
        lines.setContentsMargins(0, 0, 0, 0)
        lines.setSpacing(0)
        for value in ['作者：通信民工', 'QQ：853665220', '网站：http://www.txmg.com', '微信公众号：@通信民工']:
            line = QLabel(value)
            line.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            line.setStyleSheet('font-size:12px;color:#536575;')
            lines.addWidget(line, 1)
        content.addWidget(contact, 0, Qt.AlignTop)
        qr_label = QLabel()
        qr_label.setObjectName('helpQrCode')
        qr_label.setFixedSize(96, 96)
        qr = QPixmap(':/res/qrcode.jpg')
        if not qr.isNull():
            qr_label.setPixmap(qr.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            qr_label.setText('二维码资源未加载')
        qr_label.setAlignment(Qt.AlignCenter)
        content.addWidget(qr_label, 0, Qt.AlignTop)
        card_layout.addLayout(content)
        caption = QLabel('扫码关注 | 合作交流')
        caption.setAlignment(Qt.AlignRight)
        caption.setStyleSheet('font-size:12px;color:#293744;font-weight:bold;')
        card_layout.addWidget(caption)
        footer.addWidget(card)
        layout.addLayout(footer)

    @staticmethod
    def _scheme_table(rows, meanings):
        output = ['<table width="100%" cellspacing="0"><tr><th>电平区间（dBm）</th><th>覆盖描述</th><th>颜色</th><th>色值</th></tr>']
        names = {'#9B9B9B':'灰色','#FF0000':'红色','#F5A623':'橙色','#FFFF00':'黄色',
                 '#00FFFF':'青色','#4990E2':'浅蓝色','#0000FF':'蓝色','#00FF00':'亮绿色',
                 '#007D00':'深绿色','#007F00':'深绿色'}
        for (lo, hi, color), meaning in zip(rows, meanings):
            output.append('<tr><td>' + escape(interval_label(lo, hi)) + '</td><td>' + meaning +
                '</td><td bgcolor="' + color + '" style="color:' + ('#fff' if color in ('#0000FF','#007D00','#007F00') else '#172b3a') +
                ';">' + names[color] + '</td><td>' + color + '</td></tr>')
        output.append('</table>')
        return ''.join(output)

    @staticmethod
    def _help_html():
        nine = HelpTab._scheme_table(LEVEL_COLORS_9, ['极弱覆盖','弱覆盖','偏弱覆盖','一般覆盖','中等覆盖','良好覆盖','好覆盖','很好覆盖','极好覆盖'])
        six = HelpTab._scheme_table(LEVEL_COLORS_6, ['弱覆盖','一般覆盖','中等覆盖','良好覆盖','好覆盖','很好覆盖'])
        return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body {color:#293744;background:#fff;font-family:'Microsoft YaHei UI','Microsoft YaHei',sans-serif;font-size:14px;margin:10px 16px;}
h1 {font-size:22px;color:#18384e;margin:0 0 6px;}
h2 {font-size:17px;color:#1769aa;margin:22px 0 8px;}
h3 {font-size:15px;color:#294c64;margin:14px 0 6px;}
p {margin:6px 0 9px;line-height:1.5;}
table {width:100%;border-collapse:collapse;margin:8px 0 12px;}
th {background:#edf5fb;color:#203d52;text-align:left;border:1px solid #cfdbe5;padding:7px 9px;}
td {border:1px solid #d9e2e9;padding:7px 9px;vertical-align:top;}
li {margin:4px 0;}
.lead {background:#f1f6fa;padding:10px 12px;color:#38546a;}
.note {color:#5b6f7e;font-size:13px;}
</style></head><body>
<h1>通信规划图层生成工具（PlanLayerCreator）V2.0</h1>
<p class="lead">把 Excel、CSV、TXT 数据生成通信规划图层。先准备数据并匹配字段，再选择样式、输出格式和坐标处理方式。</p>

<h2>一、软件名称与简介</h2>
<p>通信规划图层生成工具（PlanLayerCreator）是一款 GIS 图层生成器，主要面向通信规划、无线优化和网络维护人员，可将 Excel、CSV 或 TXT 数据快速生成站点、扇区、路测、MR 栅格、线路和面域等 GIS 图层。程序提供字段自动匹配、坐标纠偏、分级配色、中文属性保留和大数据优化能力，可用于 Google Earth、MapInfo、QGIS、ArcGIS 等软件中的浏览、制图和数据交换。</p>
<table width="100%" cellspacing="0"><tr><th>项目</th><th>说明</th></tr>
<tr><td>核心能力</td><td>一份业务数据可按图层类型输出 KML、KMZ、TAB、SHP 或 MIF；原生 TAB 支持对象配色、中文字段名和中文属性值。具体格式以对应选项卡为准。</td></tr>
<tr><td>适用场景</td><td>站点与小区规划、扇区覆盖展示、路测电平专题图、MR 栅格分析、线路与行政面域制作、跨 GIS 软件数据交换。</td></tr></table>
<h3>快速上手</h3>
<p>先在对应选项卡下载模板，按模板整理数据。红色星号标注的字段必须匹配。</p>
<ol><li>选择图层类型，点击“浏览”导入数据并选择工作表。</li><li>匹配经度、纬度、电平、方位角或 WKT 等字段。</li><li>设置配色、标签和图层参数；路测和栅格可设置图例、无填充、边框及填充透明度。</li><li>选择格式、输出目录与文件名，核对坐标系后点击“生成图层”。</li></ol>

<h2>二、数据准备</h2>
<p>推荐使用 .xlsx、.xls、.csv 或 .txt。表头应清楚、唯一，电平和坐标列尽量使用数值；CSV/TXT 的实际分隔符和编码应与文件一致。</p>
<table width="100%" cellspacing="0"><tr><th>数据</th><th>准备要点</th></tr>
<tr><td>经纬度</td><td>推荐十进制度数，经度在前、纬度在后，如 108.3752、22.8185。MR 栅格请先统一为十进制度数。</td></tr>
<tr><td>电平</td><td>填写 RSRP、SS-RSRP 等测量值；默认分档按 dBm 电平设置，其他指标请按项目门限自定义。</td></tr>
<tr><td>扇区参数</td><td>提供方位角；半径和波瓣宽度可映射数据字段，也可使用界面默认值。</td></tr>
<tr><td>WKT 几何</td><td>线路 KML/KMZ 使用 LINESTRING，复合线请先拆分。面域建议采用简单 POLYGON，并核对外边界。</td></tr></table>

<h2>三、图层功能</h2>
<p>按数据类型选用图层。原始 MR 样本与已聚合栅格采用不同处理方式，选择“栅格编号”前请确认每行已代表一个栅格。</p>
<table width="100%" cellspacing="0"><tr><th>图层</th><th>主要设置与结果</th></tr>
<tr><td>站点</td><td>由经纬度生成点位，可设置图标颜色、大小、标签字段及标签颜色。</td></tr>
<tr><td>扇区</td><td>由方位角、覆盖半径和波瓣宽度生成扇形；支持分扇区配色和小区名称标签。</td></tr>
<tr><td>路测</td><td>按电平分档着色，支持 6/9 档预设、自定义阈值和颜色、区间边界、标签及点符号样式。</td></tr>
<tr><td>MR 栅格</td><td>原始样本按米制网格聚合，可选平均值/中位数和最少样本数；选择已有栅格编号时按行直接生成；支持按档位填充、独立边框、无填充和图例。</td></tr>
<tr><td>线路</td><td>由 WKT 线几何生成图层，设置线色和线宽。</td></tr>
<tr><td>面域</td><td>由 WKT 面几何生成图层，设置填充、边框颜色和边框宽度；可独立勾选“无填充”或“无边框”。KML/KMZ/TAB 保存对应对象样式，SHP 的面样式需在 GIS 中设置。</td></tr></table>

<h2>四、输出格式与属性</h2>
<p>浏览展示优先选 KMZ，需要属性查询和后续编辑时选 TAB 或 SHP。各选项卡提供的格式以界面下拉列表为准。</p>
<h3>4.1 格式、样式与属性</h3>
<table width="100%" cellspacing="0"><tr><th>格式</th><th>样式</th><th>属性与用途</th></tr>
<tr><td>KML / KMZ</td><td>点、线、面配色及标签；路测及栅格图层的 KML/KMZ 格式支持图例。</td><td>站点/扇区保留输入属性，线路/面域以弹出信息显示属性；路测/MR 保留电平。适合 Google Earth、奥维浏览。</td></tr>
<tr><td>TAB</td><td>原生着色 TAB，保留对象样式。</td><td>支持中文属性，适合 MapInfo 制图和查询；兼容性见第六节。</td></tr>
<tr><td>SHP</td><td>路测/MR 附同名 QML 样式。</td><td>保留可写入的属性。QML 用于 QGIS 着色，SHP 本身不保存渲染样式。</td></tr>
<tr><td>MIF / MID</td><td>MIF 保存几何和对象样式。</td><td>MID 保存属性，两者一起携带，用于 MapInfo 格式交换。</td></tr></table>
<p class="note">MR 原始样本聚合后，属性为栅格位置、聚合电平和采样点数等结果；已有栅格编号模式保留对应输入属性。SHP 字段名可能因格式限制被缩短。</p>

<h3>4.2 默认分档与颜色</h3>
<p>下表为工具默认电平分档，使用左开右闭规则。项目有明确门限时，请通过“编辑分档”调整。</p>
<h3>9 档 · 路测默认</h3>__NINE__
<h3>6 档 · MR 默认</h3>__SIX__

<h3>4.3 自定义与边界</h3>
<p>“编辑分档”可修改阈值及颜色、拆分或合并为 2～20 档。首末档向无穷延伸，各档连续且不重叠；方案可保存为 JSON 后再次加载。</p>
<table width="100%" cellspacing="0"><tr><th>边界规则</th><th>归档示例（9 档默认门限）</th></tr>
<tr><td>(下限, 上限] · 左开右闭</td><td>−120 归灰色档；−115 归红色档。</td></tr>
<tr><td>[下限, 上限) · 左闭右开</td><td>−120 归红色档；−115 归橙色档。</td></tr></table>

<h3>4.4 路测图例与文件携带</h3>
<p>路测及栅格图层的 KML/KMZ 格式支持图例，按当前电平字段、配色和边界生成。图例固定在左下角，大小可选小、标准、大；在 Google Earth 地点列表中可取消对应图例显示。</p>
<table width="100%" cellspacing="0"><tr><th>输出</th><th>需要携带的文件</th></tr>
<tr><td>路测 KML</td><td>.kml、与 .kml 同名的 _kml_legend.png 及全部 _kml_point*.png 放在同一目录一起携带；栅格只需图例 PNG。</td></tr>
<tr><td>路测 KMZ</td><td>图例和点图标已内嵌，可传送单个 KMZ；另存的 _kmz_legend.png 可用于报告；栅格同样内嵌图例。</td></tr></table>

<h3>4.5 边框、填充与透明度</h3>
<p>栅格填充颜色按当前档位方案设置，边框可独立设置颜色、宽度或关闭，也可选择无填充。填充透明度 0% 表示不透明，100% 表示完全透明；边框保持独立。</p>
<table><tr><th>格式</th><th>样式保存方式</th></tr><tr><td>KML/KMZ</td><td>栅格保存面样式；路测使用内嵌或配套点符号图片，支持空心、边框和填充透明度。</td></tr><tr><td>SHP + QML</td><td>QML 保存分档、填充、透明度和边框，在 QGIS 中应用；SHP 几何和属性本身不保存渲染。</td></tr><tr><td>TAB/MIF</td><td>栅格保存填充开关及边框颜色/宽度；经典对象样式不保存百分比透明度。路测保留原生点配色和大小，独立点轮廓、空心及透明度控件在此格式下不可用。</td></tr></table>
<p>无填充且无边框时，几何仍然存在，但可能在地图上不可见。</p>
<h2>五、坐标与数据检查</h2>
<p>坐标处理应与数据来源一致。WGS84 数据直接输出；GCJ-02 数据用于 Google Earth 时选择“GCJ-02 → WGS84”，避免重复纠偏。软件不会把点自动吸附到道路；点穿过建筑也可能来自采集误差、原始坐标系或影像差异。坐标系不明确时先向数据提供方核实。</p>
<table width="100%" cellspacing="0"><tr><th>检查项</th><th>建议</th></tr>
<tr><td>坐标类型</td><td>所有数据优先统一为十进制度数。站点、扇区、路测支持部分度分秒文本，导出后仍应核对点位。</td></tr>
<tr><td>空值和非法数值</td><td>检查经纬度、电平及必要参数列；无效记录可能被剔除。清洗、聚合及异常结论以同名结果日志为准。</td></tr>
<tr><td>空间位置</td><td>先输出少量已知位置的数据，与地图核对后再批量生成。</td></tr></table>

<h2>六、TAB、中文与标签</h2>
<p>TAB 是一组文件。复制或发送时应保留全部同名组成文件；需要自动标签时，打开相应工作空间。</p>
<table width="100%" cellspacing="0"><tr><th>项目</th><th>说明</th></tr>
<tr><td>文件组成</td><td>.tab、.dat、.map、.id 应一起携带；需要标签且设置了标签字段的导出路径可生成同名 .wor。</td></tr>
<tr><td>版本兼容</td><td>所有选项卡只提供一个“TAB (MapInfo)”选项，无需安装 MapInfo 即可生成原生着色 TAB。输出面向现代 GIS；非常旧的 MapInfo 若无法读取，请使用交换格式或在目标 GIS 中转换。</td></tr>
<tr><td>中文属性</td><td>主要按 CP936/WindowsSimpChinese 编码处理；字段名和文本长度受目标格式约束，特殊字符应核对。</td></tr></table>

<h2>七、性能、进度与大数据建议</h2>
<p>轻量 KML/KMZ 适合浏览大量路测点和栅格，完整属性查询优先使用 TAB/SHP。生成时显示处理阶段与已用时间，完成后显示实际耗时，并保存同名“_结果日志.txt”，记录输入文件、工作表与数量、输出路径与要素数、坐标方式、实际耗时及问题结论。成功、失败均合并到该日志，不写处理过程或程序堆栈。进度百分比代表处理阶段，并非剩余时间估算。所有 TAB 使用内置生成方式，界面无需选择后端或软件版本。</p>
<table width="100%" cellspacing="0"><tr><th>场景</th><th>建议</th></tr>
<tr><td>大量路测点</td><td>优先 KMZ；达到 100000 点后自动分片，按地图视野加载，图例与标签设置同时保留。</td></tr>
<tr><td>原始 MR 样本</td><td>设置合适的网格边长和最少样本数；均值适合常规汇总，中位数可减少异常值影响。</td></tr>
<tr><td>已聚合 MR</td><td>匹配栅格编号后按行输出，网格边长应与原始成果一致。</td></tr></table>

<h2>八、常见问题</h2>
<p>遇到问题先核对输入、输出路径和格式，再查看同名结果日志。</p>
<table width="100%" cellspacing="0"><tr><th>现象</th><th>处理方法</th></tr>
<tr><td>输出文件已存在</td><td>同一名称可分别输出 KML 和 KMZ，图片按格式独立。已有同名成果时程序保留旧成果，自动另存为 _2、_3 等新名称；以完成提示及结果日志中的实际路径为准。</td></tr>
<tr><td>Google Earth 提示仅打开可信来源文件</td><td>这是来源安全确认，不是图层解析错误。先核实文件来源，是否继续打开由用户决定。</td></tr>
<tr><td>图例太小或档位较多</td><td>在路测样式中调整“图例大小”；地图窗口较小或档位较多时可选择小图例。</td></tr>
<tr><td>TAB 标签未显示</td><td>确认导出时启用了标签并生成了相应 WOR；打开同名 .wor，而非只打开 TAB。</td></tr>
<tr><td>点位偏移或缺失</td><td>核对坐标类型、经纬度顺序和有效记录，先用已知点位检查结果。</td></tr>
<tr><td>生成异常</td><td>核对必选字段及目录权限，避免其他软件占用输出文件，并查看同名“_结果日志.txt”。</td></tr></table>
</body></html>""".replace('__NINE__', nine).replace('__SIX__', six)
