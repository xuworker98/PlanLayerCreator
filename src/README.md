# PlanLayerCreator V2.0

2026-11-23，基于 V1.4.1 完整依赖版更新，文件版本 2.0.0.0。

- 所有选项卡只有一个 TAB (MapInfo)，使用内置运行库，不再启动 MapInfo 或让用户选择生成版本。
- 先在私有目录生成并核对数量，再发布成果。同名输出自动另存 _2、_3，保留原成果。
- 修复已有同名 TAB 导致的 GDAL 更新失败；收集底层错误信息。
- 栅格 SHP 改为批量矩形几何和按列属性写入，本机 237722 行样例约 8.1 秒；边界与属性和原 99.282 秒成果一致。单次结果不含读入和 EXE 首次启动，不构成耗时承诺。
- 路测和栅格 KML/KMZ 均带当前分档图例，KMZ 内嵌。KML 需一起携带同名 _kml_legend.png 及路测的全部 _kml_point*.png。
- 栅格支持独立边框颜色、宽度、无边框、无填充及填充透明度。路测在 KML/KMZ/QML 中支持空心、独立轮廓和填充透明度。
- 百分比透明度写入 KML/KMZ 和配套 QML；经典 TAB/MIF 原生对象不保存此参数，路测原生点不保存独立轮廓设置，界面按格式启用控件。
- 每个成果仅写同名 _结果日志.txt，成功/失败统一记录输入、输出、数量、坐标方式、用时和问题结论，无过程或堆栈。
- 仅使用帮助保留 8px 圆角滚动条与双端箭头；六个制作页面保持一屏，参数自然宽度靠左，完整状态可悬停查看。

本次仅作 V2.0 布局微调：恢复原布局，制作页面不加滚动条；输入框与浏览按钮留出间距，样式行首左对齐，不按整页宽度均分控件。版本号、功能、默认参数及导出引擎保持不变。

本次V2.0细节修复：MIF数量元数据为未知值时实际统计后再核验，仍拒绝真实数量不符的成果；面域默认勾选无填充，可取消勾选恢复填充。保持现有单屏左排布局及版本号。

以下为历史版本记录，当前行为以前述内容及 V2.0 使用帮助为准。

---

# PlanLayerCreator V1.4.1

2026-11-22，基于 V1.4 完整依赖版维护修订，产品/文件版本 1.4.1.0。V1.4、V1.5 原目录保持独立。

- 面域新增“无填充”“无边框”，修复线宽传递；KML/KMZ/TAB 保存设置。SHP 本身不保存面渲染样式。
- 同名路测 KML/KMZ 可分别生成，资源文件按格式隔离。KML 须携带 `_kml_legend.png`、`_kml_point.png`；KMZ 内嵌图片，另存 `_kmz_legend.png`。
- 修复 GCJ-02 常量缺失及静默失败。原坐标模式保持输入；只有确认来源为 GCJ-02 时才选择纠偏。
- 路测 SHP 批量写入，保留坐标、中文属性、空值与字段名冲突处理。
- TAB 默认保留本机 MapInfo 兼容转换，去掉固定等待并提前进入隐藏转换入口；新增“TAB (快速，MapInfo 15.2+)”，不再启动 MapInfo。快速模式不能用于 MapInfo 2012。
- 移除未校准的预计秒数，显示处理阶段、已用时间和实际总耗时，保存同名 `_运行记录.txt`。
- 按软件用途、数据准备、操作、格式与属性、坐标、兼容性、性能与常见问题重整帮助。

实际数据核对：同名 CSV 的 109,189 条记录与新导出的 KML/KMZ 经纬度、电平一致，TAB/SHP 点坐标也一致。该结论不能证明源坐标属于 WGS84 或采集轨迹准确。

以下保留历史版本说明；携带文件名称以本节及程序内 V1.4.1 帮助为准。

---

# PlanLayerCreator V1.4

本轮更新路测图例可读性、三档图例大小、帮助章节与作者卡片布局。源码版本 V1.4，产品/文件版本 1.4.0.0，按原有依赖打包。界面进一步美化和依赖精简留待后续处理。

# PlanLayerCreator V1.3

V1.3（2026-11-22）：路测/MR 自定义分档、区间开闭选择、配色 JSON 保存与加载；路测 KML/KMZ 自动导出高清图例并使用本地点图标。分档详情见程序内“使用帮助”和 CHANGELOG.md。

路测 KML 需连同同名 `_legend.png`、`_point.png` 携带；KMZ 已内嵌资源，单文件可离线分享。输出存在同名文件时请更换名称。Google Earth 图例采用 ScreenOverlay，奥维尚需实机验收。

# 通信规划图层生成工具 · PlanLayerCreator

**PlanLayerCreator — Communication Planning GIS Layer Generator**

一款面向通信规划、无线优化和网络维护人员的桌面 GIS 图层生成工具。将 Excel、CSV 或 TXT 数据快速生成站点、扇区、路测、MR 栅格、线路和面域等 GIS 图层，可用于 Google Earth、MapInfo、QGIS、ArcGIS 等软件的浏览、制图与数据交换。

A desktop GIS layer generator for telecom planning, RF optimization, and network maintenance. Convert Excel/CSV/TXT data into GIS layers (sites, sectors, drive tests, MR grids, polylines, polygons) for Google Earth, MapInfo, QGIS, and ArcGIS.

> ⚠️ **界面语言 / UI Language**：本软件界面为**简体中文**（Simplified Chinese only）。英文读者可通过本 README 了解功能与使用方法。
> The application UI is **Simplified Chinese only**. English readers can learn about features and usage from this README.

---

## ✨ 主要功能及特点 / Features

### 图层制作能力 / Layer Types

| 图层 | 用途 | 必需数据 |
|------|------|---------|
| 站点 Site | 按经纬度生成点位，可设图标、标签颜色及大小 | 经度、纬度、站点名称 |
| 扇区 Sector | 按方位角生成扇形面，可设波束宽度、覆盖半径与填充边框 | 经度、纬度、名称、方位角 |
| 路测 Drive Test | 按 RSRP/RSSI 等电平分级显示海量采样点 | 经度、纬度、测量电平 |
| MR 栅格 Grid | 按实际米制网格聚合样本或直接使用已有栅格编号 | 经度、纬度、测量电平 |
| 线路 Line | 解析 LINESTRING/MULTILINESTRING WKT 并设置线型 | WKT 几何列 |
| 面域 Polygon | 解析 POLYGON/MULTIPOLYGON WKT 并设置填充及边框 | WKT 几何列 |

### 重点增强能力 / Key Enhancements

- **原生着色 TAB Native-colored TAB**：点、扇区、线路、面域、路测和栅格的 Symbol、Pen、Brush 样式可直接写入 TAB，不再依赖手工 MIF 转换。
- **中文属性 Chinese Attributes**：TAB 保留中文字段名和中文数据，仅对 MapInfo 不允许的符号或超长字段名做最小调整，并生成字段名对照文件。
- **标签工作空间 Label Workspace**：需要自动标签时同步生成同名 `.wor`，打开即可恢复标签字段、颜色和地图窗口状态。
- **轻量 KML/KMZ Lightweight KML/KMZ**：路测和 MR 栅格仅保留所选电平值，避免完整 Excel 属性在每个对象中重复写入。
- **大数据分片 Tiled Loading**：超大路测 KMZ 自动分区，通过 NetworkLink 按视野加载，降低 Google Earth 首次打开压力。
- **稳定聚合 Stable Aggregation**：MR 原始样本在 UTM 投影中按实际米数聚合，可选平均值或中位数，并过滤样本数不足的网格。
- **坐标纠偏 Coordinate Correction**：GCJ-02 → WGS84 一键纠偏。

## 🖼️ 软件截图 / Screenshots

![主界面](screenshots/main.png)

*更多截图见 [screenshots/](screenshots/) 目录。*

## 📁 支持格式 / Supported Formats

| 图层类型 | KML/KMZ | TAB | SHP | MIF |
|---------|:---:|:---:|:---:|:---:|
| 站点 Site | ✅ 着色 | ✅ 符号 | ✅ | — |
| 扇区 Sector | ✅ 填充 | ✅ Brush/Pen | ✅ | — |
| 路测 Drive Test | ✅ 分级点色 | ✅ 分级 Symbol | ✅ | ✅ |
| MR 栅格 Grid | ✅ 分级面色 | ✅ Brush/Pen | ✅ | ✅ |
| 线路 Line | ✅ 样式 | ✅ Pen | ✅ | — |
| 面域 Polygon | ✅ 填充 | ✅ Brush/Pen | ✅ | — |

**说明 / Notes**：
- TAB 输出为同名文件组（.tab/.dat/.map/.id），须整体交付。
- V2.0 统一使用内置运行库生成 TAB，不依赖本机 MapInfo；面向 MapInfo 15.2+。
- SHP 标准不存渲染样式，路测/MR 附同名 QML 供 QGIS 使用。

## 🚀 快速开始 / Quick Start

1. 从 [Releases](https://github.com/xuworker98/PlanLayerCreator/releases) 下载 `PlanLayerCreator.exe`
2. 双击运行（无需安装 Python，支持 Windows 10/11 x64）
3. 选择图层类型 → 导入数据 → 映射字段 → 设置样式 → 生成

### 数据要求 / Data Requirements

- 第一行为字段名称；必须包含**经度列**和**纬度列**
- 栅格/路测图层额外需要**电平值列**（如 RSRP）
- 扇区图层额外需要**方位角列**
- 经纬度须为十进制度数（如 116.397128），不支持度分秒
- 样例数据见 [`data/`](data/) 目录

## 🧪 开发者 / For Developers

```bash
# 创建虚拟环境（须用 CPython，非 conda）
python -m venv .venv
.venv\Scripts\pip install -r requirements-build.txt

# 运行源码自检
set QT_QPA_PLATFORM=offscreen
set PLANLAYER_TAB_BACKEND=gdal
python main.py --self-test test_output

# 构建单文件 EXE
python -m PyInstaller --clean PlanLayerCreator.spec
```

## 🏗️ 技术栈 / Tech Stack

Python 3.12 · PySide6 · pandas · numpy · pyogrio (GDAL) · shapely · pyproj · simplekml

## 📄 许可证 / License

本项目采用 [CC BY-NC 4.0（署名-非商业性使用）](LICENSE) 许可协议。

- ✅ 可自由查看、下载、修改、分享源码
- ✅ 使用时须保留作者署名
- ❌ **禁止商业用途**（销售、集成到收费产品、有偿服务需单独商业授权）

This project is licensed under [CC BY-NC 4.0](LICENSE) (Attribution-NonCommercial). Free for personal/non-commercial use. Commercial use requires a separate license.

## 📞 联系方式 / Contact

- **作者 Author**：通信民工（许景渊 / Jerry Xu）
- **哔哩哔哩 Bilibili**：@通信民工（UID：482597398）
- **微信公众号 WeChat**：@通信民工（ComDesigner）
- **QQ**：853665220（@qq.com）
- **著作 Book**：《5G网络规划与工程实践》（清华大学出版社出版，当当、京东、淘宝等平台均可购买）
