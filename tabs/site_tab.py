# -*- coding: utf-8 -*-
"""制作站点 Tab — 定制布局"""
from PySide6.QtWidgets import (
    QPushButton, QColorDialog, QDoubleSpinBox, QCheckBox, QComboBox,
    QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
    QSizePolicy, QProgressBar, QMessageBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
import os
from tabs.base_tab import BaseTab
from utils.constants import SITE_DEFAULT_ICON_COLOR, SITE_DEFAULT_LABEL_COLOR, SITE_DEFAULT_SCALE


class SiteTab(BaseTab):
    MAP_COLS = 4
    STYLE_COLS = 4

    def __init__(self, parent=None):
        self.req_fields = [
            ('lon', '经度', True),
            ('lat', '纬度', True),
            ('name', '站点名称', True),
            ('label', '标签列', False),
        ]
        super().__init__('site', self.req_fields, parent)

    def get_default_style(self):
        return {
            'icon_color': SITE_DEFAULT_ICON_COLOR,
            'label_color': SITE_DEFAULT_LABEL_COLOR,
            'scale': SITE_DEFAULT_SCALE,
            'show_label': True,
        }

    # ====== 1. 数据源：一行两栏 ======

    def _build_data_section(self):
        src = QGroupBox("1. 数据源")
        row = QHBoxLayout()
        row.setSpacing(12)

        # 左栏：路径+浏览+模板
        left = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("请选择数据文件（Excel/CSV/TXT）...")
        self.file_edit.setReadOnly(True)
        left.addWidget(self.file_edit, 1)
        for text, slot, w in [("浏览", self.browse_file, 65), ("模板", self.download_template, 55)]:
            btn = QPushButton(text); btn.setFixedWidth(w); btn.clicked.connect(slot); left.addWidget(btn)
        row.addLayout(left, 3)

        # 右栏：工作表+下拉
        right = QHBoxLayout()
        right.addWidget(QLabel("工作表："))
        self.sheet_combo = QComboBox()
        self.sheet_combo.setFixedWidth(150)
        right.addWidget(self.sheet_combo)
        right.addStretch()
        row.addLayout(right, 1)

        src.setLayout(row)
        return src

    # ====== 2. 字段映射：一行四栏 ======

    def _build_map_section(self):
        map_group = QGroupBox("2. 字段映射")
        self._map_pairs = QHBoxLayout()
        self._map_pairs.setSpacing(4)
        self._map_row = QHBoxLayout()  # placeholder, not used for HBox
        self.init_field_mapping_ui()
        self._map_pairs.addStretch()
        map_group.setLayout(self._map_pairs)
        return map_group

    def init_field_mapping_ui(self):
        for key, label, req in self.req_fields:
            combo = QComboBox()
            combo.addItem("")
            combo.setMinimumWidth(120)
            combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.map_combos[key] = combo
            display = f'{label}：<span style="color:red;">*</span>' if req else f'{label}：'
            lbl = QLabel(display)
            lbl.setTextFormat(Qt.RichText)
            pair = QHBoxLayout()
            pair.setSpacing(2)
            pair.addWidget(lbl)
            pair.addWidget(combo)
            self._map_pairs.addLayout(pair)
            if key != self.req_fields[-1][0]:
                spacer = QLabel(" ")
                spacer.setFixedWidth(16)
                self._map_pairs.addWidget(spacer)

    # ====== 3. 样式设置：一行四栏，紧凑 ======

    def _build_style_section(self):
        style_group = QGroupBox("3. 样式设置（KML/KMZ/TAB 配色）")
        self.style_grid = QGridLayout()
        self.style_grid.setHorizontalSpacing(6)
        self.style_grid.setVerticalSpacing(0)
        for c in range(8):
            self.style_grid.setColumnStretch(c, 0 if c % 2 == 0 else 1)
        self._sty_row = 0
        self._sty_col = 0
        self.init_style_ui()
        style_group.setLayout(self.style_grid)
        return style_group

    def init_style_ui(self):
        # 图标颜色
        self.icon_color_btn = QPushButton()
        self.icon_color_btn.setFixedSize(36, 18)
        self.icon_color_btn.setStyleSheet(f"background:{self.style['icon_color']};border:1px solid #dcdde1;border-radius:2px;")
        self.icon_color_btn.clicked.connect(lambda: self.pick_color('icon_color'))
        self.add_style_row("图标颜色", self.icon_color_btn)

        # 标签颜色
        self.label_color_btn = QPushButton()
        self.label_color_btn.setFixedSize(36, 18)
        self.label_color_btn.setStyleSheet(f"background:{self.style['label_color']};border:1px solid #dcdde1;border-radius:2px;")
        self.label_color_btn.clicked.connect(lambda: self.pick_color('label_color'))
        self.add_style_row("标签颜色", self.label_color_btn)

        # 图标大小
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 5.0)
        self.scale_spin.setValue(self.style['scale'])
        self.scale_spin.setMaximumWidth(80)
        self.add_style_row("图标大小", self.scale_spin)

        # 显示标签
        self.show_label_cb = QCheckBox("显示标签")
        self.show_label_cb.setChecked(self.style['show_label'])
        self.add_style_row("", self.show_label_cb)

    # ====== 生成 ======

    def generate(self):
        mapping = self.get_current_mapping()
        missing = [label for key, label, req in self.req_fields if req and key not in mapping]
        if missing:
            QMessageBox.warning(self, "警告", f"请选择必选字段: {', '.join(missing)}")
            return
        out_dir = self.out_dir_edit.text()
        if not out_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return
        filename = self.filename_edit.text().strip() or self.get_default_filename()
        fmt_text = self.format_combo.currentText()
        ext_map = {'KMZ': '.kmz', 'KML': '.kml', 'TAB': '.tab', 'SHP': '.shp'}
        ext = '.kmz'
        for k, v in ext_map.items():
            if k in fmt_text: ext = v; break
        output_path = os.path.join(out_dir, f"{filename}{ext}")
        do_correct = self.coord_group.checkedId() == 1

        from widgets.worker_thread import GenerateWorker
        self._on_gen_start()
        self._worker = GenerateWorker('site', self.df, mapping, self.style, output_path, do_correct)
        self._worker.progress.connect(self.set_progress)
        self._worker.log.connect(self._status)
        self._worker.finished.connect(lambda msg: (self._on_gen_done(), self._status(msg)))
        self._worker.error.connect(lambda msg: (self._on_gen_done(), self._status(f"错误: {msg}")))
        self._worker.start()

    # ====== 样式方法 ======

    def _build_button_row(self):
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(24)
        self.progress_bar.setMaximumWidth(300)

        self.btn_generate = QPushButton("生成图层")
        self.btn_generate.setFixedWidth(120)
        self.btn_generate.clicked.connect(self.generate)

        self.btn_cancel = QPushButton("取消生成")
        self.btn_cancel.setFixedWidth(100)
        self.btn_cancel.clicked.connect(self.cancel_generate)

        self.btn_open_folder = QPushButton("打开文件夹")
        self.btn_open_folder.setFixedWidth(100)
        self.btn_open_folder.clicked.connect(self.open_output_folder)

        btn_row.addWidget(self.progress_bar)
        btn_row.addWidget(self.btn_generate)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_open_folder)
        btn_row.addStretch()
        return btn_row

    # ====== 样式方法 ======

    def pick_color(self, key):
        color = QColorDialog.getColor(QColor(self.style[key]), self, "选择颜色")
        if color.isValid():
            self.style[key] = color.name()
            btn = self.icon_color_btn if key == 'icon_color' else self.label_color_btn
            btn.setStyleSheet(f"background:{color.name()};border:1px solid #dcdde1;border-radius:2px;")

    def _radio(self, text, checked):
        from PySide6.QtWidgets import QRadioButton
        rb = QRadioButton(text)
        rb.setChecked(checked)
        return rb

    def get_template_data(self):
        return {
            '站点名称': ['基站A', '基站B', '基站C'],
            '经度': [108.3718, 108.3738, 108.3726],
            '纬度': [22.8715, 22.8693, 22.8749],
            '标签': ['A小区', 'B小区', 'C小区'],
        }
