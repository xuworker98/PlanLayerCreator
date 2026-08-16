# 更新日志 / Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)（Semantic Versioning）。

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
