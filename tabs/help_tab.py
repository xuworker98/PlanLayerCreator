# -*- coding: utf-8 -*-
"""程序内置使用帮助。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class HelpTab(QWidget):
    """使用统一 HTML 文档排版，避免多块 QLabel 的缩进和行高不一致。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        self.browser = QTextBrowser()
        self.browser.setObjectName("helpBrowser")
        self.browser.setFrameShape(QTextBrowser.NoFrame)
        self.browser.setOpenExternalLinks(False)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.browser.setStyleSheet(
            "QTextBrowser { background: #ffffff; border: 1px solid #e6e9ed; "
            "border-radius: 8px; padding: 10px; color: #2d3436; }"
        )
        self.browser.setHtml(self._help_html())
        layout.addWidget(self.browser, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(8, 0, 8, 0)
        footer.setSpacing(12)
        footer.addStretch(1)

        footer_text = QLabel(
            "<div style='color:#636e72; font-size:12px; line-height:150%;'>"
            "扫码关注公众号<br><b style='color:#2d3436;'>ComDesigner（通信民工）</b>"
            "</div>"
        )
        footer_text.setTextFormat(Qt.RichText)
        footer_text.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        footer.addWidget(footer_text)

        qr_label = QLabel()
        qr_label.setObjectName("helpQrCode")
        qr = QPixmap(":/res/qrcode.jpg")
        if not qr.isNull():
            qr_label.setPixmap(
                qr.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            qr_label.setText("二维码资源未加载")
        qr_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        footer.addWidget(qr_label)
        layout.addLayout(footer)

    @staticmethod
    def _help_html():
        return """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    color: #2d3436;
    background: #ffffff;
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
    font-size: 14px;
    line-height: 1.65;
    margin: 10px 18px 22px 18px;
  }
  h1 {
    color: #1f2937;
    font-size: 22px;
    font-weight: 700;
    margin: 0 0 4px 0;
  }
  h2 {
    color: #1769aa;
    font-size: 17px;
    font-weight: 700;
    margin: 24px 0 9px 0;
  }
  h3 {
    color: #2d3436;
    font-size: 15px;
    font-weight: 700;
    margin: 14px 0 5px 0;
  }
  p { margin: 6px 0; }
  ul, ol { margin: 6px 0 8px 24px; padding: 0; }
  li { margin: 4px 0; }
  table { width: 100%; border-collapse: collapse; margin: 9px 0 7px 0; }
  th {
    color: #1f2937;
    background: #edf5fb;
    border: 1px solid #cfd8e3;
    padding: 7px 8px;
    text-align: left;
    vertical-align: middle;
  }
  td {
    border: 1px solid #d9e0e7;
    padding: 7px 8px;
    text-align: left;
    vertical-align: top;
  }
  .subtitle { color: #636e72; font-size: 13px; margin: 0 0 14px 0; }
  .lead {
    color: #334155;
    background: #f5f9fc;
    border-left: 4px solid #0984e3;
    padding: 10px 12px;
    margin: 12px 0 8px 0;
  }
  .tip {
    color: #38536b;
    background: #eef7ff;
    border: 1px solid #cfe7fb;
    padding: 9px 11px;
    margin: 8px 0;
  }
  .warn {
    color: #714f13;
    background: #fff8e6;
    border: 1px solid #f2d58a;
    padding: 9px 11px;
    margin: 8px 0;
  }
  .ok { color: #18864b; font-weight: 700; }
  .muted { color: #687481; font-size: 13px; }
  .center { text-align: center; }
</style>
</head>
<body>
  <h1>通信规划图层生成工具（PlanLayerCreator）V1.1</h1>
  <p class="subtitle">作者：通信民工　|　QQ：853665220　|　公众号：ComDesigner（通信民工）</p>

  <div class="lead">
    将 Excel、CSV 或 TXT 数据快速生成通信规划 GIS 图层，支持站点、扇区、路测、MR 栅格、线路和面域。
    可输出 KML、KMZ、原生 TAB、SHP 和 MIF，并保留相应的属性与配色。
  </div>

  <h2>一、快速使用</h2>
  <ol>
    <li>在顶部选择图层类型：站点、扇区、路测、栅格、线路或面域。</li>
    <li>单击“浏览”，导入 Excel、CSV 或 TXT 文件。</li>
    <li>匹配经度、纬度、名称、电平、方位角或 WKT 等字段；红色星号为必选项。</li>
    <li>选择配色方案并设置图标、标签、线宽、覆盖半径或栅格参数。</li>
    <li>选择 KML、KMZ、TAB、SHP 或 MIF，指定输出位置后单击“生成”。</li>
  </ol>

  <h2>二、新增与增强功能</h2>
  <table cellspacing="0" cellpadding="0">
    <tr><th width="24%">功能</th><th>说明</th></tr>
    <tr><td><b>原生着色 TAB</b></td><td>点、扇区、线和栅格的 Symbol、Pen、Brush 样式直接写入 TAB，不再需要先生成 MIF 后手工转换。</td></tr>
    <tr><td><b>中文属性</b></td><td>TAB 保留中文字段名和中文数据；仅对 MapInfo 不允许的标点或超长字段名做最小化调整，并输出字段对照文件。</td></tr>
    <tr><td><b>标签工作空间</b></td><td>需要自动标签时同步生成同名 WOR。打开 WOR 可恢复标签字段、颜色及地图窗口状态。</td></tr>
    <tr><td><b>米制 MR 聚合</b></td><td>原始样本在 UTM 投影中按实际米数划分网格，可选平均值或中位数，并可过滤样本数不足的网格。</td></tr>
    <tr><td><b>轻量 KML/KMZ</b></td><td>路测和 MR 栅格只保留所选电平值，减少文件体积。超大路测 KMZ 会自动分片并通过 NetworkLink 按视野加载。</td></tr>
  </table>

  <h2>三、图层功能</h2>
  <table cellspacing="0" cellpadding="0">
    <tr><th width="18%">图层</th><th>主要能力</th></tr>
    <tr><td><b>站点</b></td><td>由经纬度生成点位；支持自定义图标颜色、标签颜色、图标大小和坐标纠偏。</td></tr>
    <tr><td><b>扇区</b></td><td>根据方位角、波瓣宽度和覆盖半径生成扇形面；支持三扇区自动配色及自定义填充、边框。</td></tr>
    <tr><td><b>路测</b></td><td>按 RSRP、RSSI 等电平分级显示；支持 6 档或 9 档配色，适合大批量点数据。</td></tr>
    <tr><td><b>MR 栅格</b></td><td>原始样本可按指定米数聚合；也可选择已有栅格编号，按已聚合记录直接输出。</td></tr>
    <tr><td><b>线路</b></td><td>解析 LINESTRING/MULTILINESTRING 等 WKT 几何，输出带属性的线图层并设置线型。</td></tr>
    <tr><td><b>面域</b></td><td>解析 POLYGON/MULTIPOLYGON 等 WKT 几何，输出带属性的面图层并设置填充、边框。</td></tr>
  </table>

  <h2>四、输出格式与属性</h2>
  <table cellspacing="0" cellpadding="0">
    <tr>
      <th width="15%">格式</th><th width="24%">样式</th><th width="25%">属性</th><th>适用场景</th>
    </tr>
    <tr><td><b>KML/KMZ</b></td><td><span class="ok">支持配色</span></td><td>站点/扇区/线路/面域保留属性；路测/MR 仅保留电平</td><td>Google Earth、奥维等浏览展示</td></tr>
    <tr><td><b>TAB</b></td><td><span class="ok">原生点/线/面样式</span></td><td>支持中文表头和中文数据</td><td>MapInfo 正式制图与属性查询</td></tr>
    <tr><td><b>SHP</b></td><td>路测、栅格另附同名 QML</td><td>保留可写入 SHP 的属性</td><td>QGIS、ArcGIS 数据交换</td></tr>
    <tr><td><b>MIF</b></td><td>保留 MapInfo 对象样式</td><td>MID 保存属性</td><td>交换、兼容或人工导入</td></tr>
  </table>
  <p class="muted">说明：SHP 标准本身不保存渲染样式；QML 是供 QGIS 加载的同名样式文件。</p>

  <h2>五、TAB、中文与标签说明</h2>
  <div class="tip">
    <b>TAB 图层不是单个文件。</b>一次输出通常包含 .tab、.dat、.map、.id；移动或复制时请保持这些同名文件在同一目录。
    程序本身仍是单一 EXE，无需安装 Python、Fiona 或 GDAL。
  </div>
  <ul>
    <li>安装了 MapInfo 的电脑：程序优先调用本机 MapInfo，生成兼容旧版 MapInfo（包括 2012）的 TAB。</li>
    <li>未安装 MapInfo 的电脑：使用 EXE 内置运行库生成 MapInfo 15.2+ TAB，中文字段及配色可在新版 MapInfo 或 QGIS 中使用。</li>
    <li>自动标签属于地图窗口/工作空间设置，不是单纯的 TAB 对象样式。需要标签时请打开程序生成的同名 .wor。</li>
    <li>常用简体中文按 CP936/WindowsSimpChinese 写入。生僻字、繁体扩展字或部分特殊符号可能超出该编码范围。</li>
  </ul>
  <div class="warn">
    未安装 MapInfo 时生成的 15.2+ TAB 不能保证被 MapInfo 2012 打开。若目标电脑固定使用 MapInfo 2012，建议在生成 TAB 的电脑上安装 MapInfo，程序会自动选择兼容转换路径。
  </div>

  <h2>六、大数据建议</h2>
  <ul>
    <li><b>路测 / MR 的 KML、KMZ：</b>仅写入电平值，避免把整张 Excel 属性表重复写入每个对象。</li>
    <li><b>超大路测：</b>优先选择 KMZ；达到大数据阈值后程序会自动分片，Google Earth 按区域加载。</li>
    <li><b>原始 MR 样本：</b>设置合理的栅格边长、最少样本数；中位数抗异常值更稳，平均值速度更快且便于常规统计。</li>
    <li><b>已聚合 MR：</b>选择“栅格编号”字段后直接生成图层，不再重复聚合，并尽量保留原始属性。</li>
    <li><b>需要完整属性：</b>优先使用 TAB 或 SHP；Google Earth 只承担浏览展示，避免加载百万行完整属性。</li>
  </ul>

  <h2>七、数据要求与常见问题</h2>
  <ul>
    <li>经纬度必须是十进制度数，例如 116.397128、39.916527；当前不支持度分秒文本。</li>
    <li>扇区必须提供方位角；覆盖半径、波瓣宽度未映射时使用界面设置值。</li>
    <li>WKT 字段应包含完整、合法的线或面几何文本，坐标顺序为经度在前、纬度在后。</li>
    <li>GCJ-02 数据用于 Google Earth 时，可选择“GCJ-02 → WGS84”；已经是 WGS84 的数据不要重复纠偏。</li>
    <li>输出目录应具有写权限；生成时不要让 MapInfo、Excel 或同步软件锁定同名目标文件。</li>
  </ul>

  <h2>八、联系作者</h2>
  <table cellspacing="0" cellpadding="0">
    <tr><th width="18%">作者</th><td>通信民工</td></tr>
    <tr><th>QQ</th><td>853665220（@qq.com）</td></tr>
    <tr><th>公众号</th><td>ComDesigner（通信民工）</td></tr>
    <tr><th>交流内容</th><td>通信工具定制、使用反馈及技术交流</td></tr>
  </table>
</body>
</html>
"""
