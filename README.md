# 通信规划图层生成工具 · PlanLayerCreator V2.0

面向通信规划、无线优化与网络维护的 Windows GIS 图层生成器。将 Excel、CSV、TXT 数据转换为站点、扇区、路测、MR 栅格、线路和面域图层，支持 KML、KMZ、TAB、SHP，路测及栅格另支持 MIF。

支持字段匹配、坐标纠偏、分级配色及中文属性；路测与栅格 KML/KMZ 支持图例。V2.0 修复 TAB 输出与 MIF 数量核验，面域默认无填充，制作页面保持单屏布局。

- [功能及格式说明](src/README.md)
- [更新记录](src/CHANGELOG.md)
- [V2.0 使用说明书](docs/说明书_通信规划图层生成工具（PlanLayerCreator）_V2.0.docx)
- [许可证：CC BY-NC 4.0](LICENSE)

## 从 GitHub 获取并运行

源码和打包配置位于 `src`。需要 Windows x64、Python 3.12：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\src\requirements-build.txt
.\.venv\Scripts\python.exe -B .\src\main.py
```

也可双击根目录的启动、自检或编译入口。脚本优先使用项目 `.venv`，其次使用 SuperCodex 共享环境。自检输出位于 `process_test`，新 EXE 位于 `output/build_日期时间`。这些生成文件及虚拟环境不提交 Git。

## 本机开发入口与来源


- 创建日期：2026-11-24
- 当前软件版本：V2.0（2.0.0.0）
- 固定开发目录：`D:\SuperCodex\41_PlanLayerCreator_20261124`
- 本项目直接复制自：`D:\09软件开发\通信规划图层生成工具（PlanLayerCreator）V2.0\源码`
- 来源为已修复 MIF 数量核验、面域默认无填充的 V2.0。迁入时不改软件功能和布局。

## 下次如何修改和更新

直接打开本项目，修改 `src` 中的源码。双击 `启动软件源码.cmd` 运行源码；双击 `运行自检.cmd` 检验；双击 `编译打包.cmd` 生成 EXE。

新编译成果进入 `output/build_日期时间/PlanLayerCreator.exe`，不会覆盖既有正式软件；发布前需检查并另行确认替换。根目录 output 中保留迁入时的正式 EXE、源码压缩包及核验记录，它们是迁入快照，后续修改不会自动更新这些快照。

## 目录

- `src`：完整源码、资源、依赖版本清单和 PyInstaller 配置。
- `scripts`：启动、自检、编译脚本，按脚本所在目录定位项目。
- `output`：正式软件快照及后续编译成果。
- `docs`：使用说明书。
- `process_test`：迁移验证、测试和编译中间文件。
- `data`、`refs`、`temp`：预留数据、参考材料和临时目录。

## 开发环境必须保留

使用共享环境 `D:\SuperCodex\.venvs\planlayercreator-hermes`，以及基础 Python `C:\Users\Administrator\AppData\Local\Programs\Python\Python312`。不依赖旧的 41_PlanLayerCreator 项目文件夹。清理旧项目时不要误删共享环境；EXE 自身运行不需要该环境。

若环境丢失，可使用 Python 3.12 创建虚拟环境并按 `src/requirements-build.txt` 恢复。脚本默认寻找 SuperCodex 下的共享环境，不自动联网或安装依赖。

## 迁移记录

2026-11-24：按用户指定目录复制最新 V2.0，未删除或移动原目录。源码逐文件 SHA256 校验见 `process_test/迁移源码校验.json`。历史核验记录中原路径仅用于追溯。
