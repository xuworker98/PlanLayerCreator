# 更新日志 / Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)（Semantic Versioning）。

## [1.1.3] - 2026-08-18

### 修复
- 扇区 KML/KMZ 报错：改用 format=False 跳过 simplekml 的 minidom 解析，根除 not well-formed
- 非法字符清洗：扩展为控制字符 + 非字符（\uFFFE/\uFFFF），并生成错误日志

### 新增
- 错误日志（错误日志.txt）：记录非法字符明细（行号/字段/原值）+ 生成异常详细堆栈

## [1.1.2] - 2026-08-18

### 修复
- 扇区 KML/KMZ 报错：字段值含非法 XML 控制字符时清洗，避免 not well-formed
- 扇区 TAB 着色错误：编号改为始终按经纬度分组（不依赖基站标识），填/不填结果一致
- MIF 字符集：输出改 GBK + WindowsSimpChinese，MapInfo 2012 可直接打开

## [1.1.1] - 2026-08-18

### 修复
- 扇区编号规则一：修正边界判定（60°/300° 含边界）+ 夹角相同的 tie-break 规则
- 扇区 KML/KMZ 崩溃：基站标识为空时 groupby 丢行导致 astype(int) 报错
- 扇区性能：pyproj CRS/Transformer 移出循环，2 万行从 10 分钟降至秒级

### 新增
- 全图层统一数据清洗：度分秒→十进制度、类型强制（经纬度浮点/角度整数）、空值剔除
- 数据清洗日志：自动写入输出目录「生成日志.txt」，记录剔除明细
- 全图层进度回调 + 预估时间提示（进度条不再卡 0%）

## [1.1.0] - 2026-08-11

### 新增
- 原生着色 TAB：对象级 Symbol/Pen/Brush 样式（通过 MIF + MapInfo/GDAL 双后端）
- 中文字段名与属性值完整保留（不再拼音化），字段 Char(254) 避免 CP936 截断
- 路测/MR KML/KMZ 轻量模式：只保留电平字段，10 万点以上 Region/NetworkLink 分片
- MR 栅格 UTM 米制网格聚合，支持平均值/中位数/最少样本数
- 同名 .wor 工作空间：自动标签、颜色、字号恢复
- 图标与二维码通过 Qt Resource System 嵌入 EXE
- `--self-test` / `--gui-smoke` 内置回归测试

### 修复
- 彻底移除 fiona/osgeo 依赖，改用 pyogrio.raw（解决 PyInstaller 打包崩溃）
- 打包体积从 219MB 降至 82MB（单文件 EXE）

## [1.0.0] - 2026-08-07

### 新增
- 首个版本：六类图层生成（站点/扇区/路测/栅格/线路/面域）
- KML/KMZ/MIF 输出与配色
- GCJ-02 → WGS84 坐标纠偏
