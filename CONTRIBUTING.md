# 贡献指南 / Contributing

感谢您对 PlanLayerCreator 的关注！欢迎提交 Issue 和 Pull Request。

## 报告 Bug / Reporting Bugs

请提供以下信息：
1. 软件版本（帮助 → 关于）
2. 操作系统（Windows 10/11，x64）
3. 复现步骤
4. 错误截图或日志

## 提交代码 / Submitting Code

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/xxx`
3. 提交前运行源码自检：

```bash
set QT_QPA_PLATFORM=offscreen
set PLANLAYER_TAB_BACKEND=gdal
python main.py --self-test test_output
```

4. 确保自检通过（退出码 0）后再提交 PR

## 代码规范 / Code Style

- 遵循现有代码风格（PEP 8）
- 中文字符串统一使用 UTF-8 编码
- 新增功能补充自检用例（`utils/self_test.py`）
- 大数据量处理使用 numpy/向量化，禁止逐行 Python 循环

## 沟通 / Communication

- Issue 优先使用中文描述
- 保持友好、尊重他人
