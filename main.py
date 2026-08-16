# -*- coding: utf-8 -*-
"""
通信规划图层生成器（PlanLayerCreator）V1.1
作者：通信民工 | 关注【通信民工】公众号 | QQ: 853665220
"""
import sys
import os

# 确保 src/ 在 path 中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QStatusBar, QLabel, QWidget, QHBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

# 注册编译进程序的图标和二维码资源。
import resources_rc  # noqa: F401

from utils.constants import (
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, WINDOW_TITLE, STATUS_RIGHT
)

VERSION = "1.1"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.init_ui()

    def init_ui(self):
        # 中心 TabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 延迟导入 Tab（避免启动时加载全部）
        from tabs.site_tab import SiteTab
        from tabs.sector_tab import SectorTab
        from tabs.drive_tab import DriveTab
        from tabs.grid_tab import GridTab
        from tabs.line_tab import LineTab
        from tabs.polygon_tab import PolygonTab
        from tabs.help_tab import HelpTab

        self.site_tab = SiteTab()
        self.sector_tab = SectorTab()
        self.drive_tab = DriveTab()
        self.grid_tab = GridTab()
        self.line_tab = LineTab()
        self.polygon_tab = PolygonTab()
        self.help_tab = HelpTab()

        self.tabs.addTab(self.site_tab, "制作站点")
        self.tabs.addTab(self.sector_tab, "制作扇区")
        self.tabs.addTab(self.drive_tab, "路测图层")
        self.tabs.addTab(self.grid_tab, "栅格图层")
        self.tabs.addTab(self.line_tab, "线路图层")
        self.tabs.addTab(self.polygon_tab, "面域图层")
        self.tabs.addTab(self.help_tab, "使用帮助")

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("✅ 就绪")
        self.status_label.setStyleSheet("font-size: 12px;")
        self.status_bar.addWidget(self.status_label, 1)

        right_label = QLabel(STATUS_RIGHT)
        right_label.setStyleSheet("color: #0984e3; font-size: 12px; padding-right: 8px;")
        self.status_bar.addPermanentWidget(right_label)

        # 应用图标
        self.setWindowIcon(QIcon(':/res/icon.ico'))


def main():
    # onefile 子进程模式：同一个 EXE 承担 MapInfo COM 转换，避免把
    # sys.executable 当作 Python 解释器再次启动 GUI。
    if len(sys.argv) >= 3 and sys.argv[1] == '--mif-to-tab':
        from engine.mif_to_tab_subproc import run_conversion
        return run_conversion(sys.argv[2])
    if len(sys.argv) >= 2 and sys.argv[1] == '--self-test':
        from utils.self_test import run_self_test
        output_dir = sys.argv[2] if len(sys.argv) >= 3 else None
        return run_self_test(output_dir)

    gui_smoke = '--gui-smoke' in sys.argv
    if gui_smoke:
        sys.argv.remove('--gui-smoke')

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 全局 QSS 样式
    app.setStyleSheet("""
    QMainWindow { background: #f5f6fa; }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #dcdde1;
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 16px;
        background-color: #ffffff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #2d3436;
    }
    QPushButton {
        background: #0984e3;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 16px;
    }
    QPushButton:hover { background: #0773c5; }
    QPushButton:pressed { background: #065ea8; }
    QPushButton:disabled { background: #b2bec3; }
    QComboBox, QLineEdit {
        border: 1px solid #dcdde1;
        border-radius: 4px;
        padding: 4px 8px;
        background: #ffffff;
        color: #2d3436;
    }
    QComboBox::drop-down { width: 0px; }
    QComboBox:hover { border-color: #0984e3; }
    QComboBox QAbstractItemView {
        background: white;
        color: #2d3436;
        selection-background-color: #0984e3;
        selection-color: white;
        outline: none;
    }
    QTabWidget::pane {
        border: 1px solid #dcdde1;
        background: #ffffff;
    }
    QTabBar::tab {
        background: #dfe6e9;
        padding: 8px 20px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #ffffff;
        font-weight: bold;
    }
    QScrollArea { border: none; background: transparent; }
    QProgressBar {
        border: 1px solid #dcdde1;
        border-radius: 4px;
        text-align: center;
        height: 18px;
    }
    QProgressBar::chunk { background: #0984e3; border-radius: 3px; }
    QStatusBar { background: #dfe6e9; color: #2d3436; font-size: 12px; }
    """)

    app.setWindowIcon(QIcon(':/res/icon.ico'))

    window = MainWindow()
    window.show()
    if gui_smoke:
        from PySide6.QtCore import QTimer
        def finish_smoke_test():
            ok = (
                window.isVisible()
                and window.tabs.count() == 7
                and not window.windowIcon().isNull()
            )
            app.exit(0 if ok else 2)
        QTimer.singleShot(1500, finish_smoke_test)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
