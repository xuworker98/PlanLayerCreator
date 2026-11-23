# -*- coding: utf-8 -*-
"""MR 栅格图层 Tab"""
from PySide6.QtWidgets import (
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QColorDialog,
    QGroupBox, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QSizePolicy, QProgressBar, QMessageBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
import os
from tabs.base_tab import BaseTab
from utils.constants import LEVEL_COLORS_6, LEVEL_COLORS_9


from widgets.level_controls import LevelControls
from widgets.map_style_controls import style_options


class GridTab(LevelControls, BaseTab):
    def __init__(self, parent=None):
        self.req_fields = [
            ('lon', '经度', True), ('lat', '纬度', True), ('level', '测量电平值', True),
        ]
        super().__init__('grid', self.req_fields, parent)
        # All primary output formats are available; TAB no longer needs MapInfo.
        self.format_combo.clear()
        self.format_combo.addItems([
            'KMZ (压缩推荐)', 'KML (未压缩)', 'TAB (MapInfo)',
            'SHP (含属性)', 'MIF (交换格式)',
        ])

    def get_default_style(self):
        return {
            'grid_size_m': 50,
            'level_colors': [list(x) for x in LEVEL_COLORS_6],
            'preset': '6档',
            'border_width': 1,
        }

    def _build_data_section(self):
        src = QGroupBox("1. 数据源")
        row = QHBoxLayout(); row.setSpacing(12)
        left = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("请选择数据文件（Excel/CSV/TXT）...")
        self.file_edit.setReadOnly(True)
        left.addWidget(self.file_edit, 1)
        for text, slot, w in [("浏览", self.browse_file, 65), ("模板", self.download_template, 55)]:
            btn = QPushButton(text); btn.setFixedWidth(w); btn.clicked.connect(slot); left.addWidget(btn)
        row.addLayout(left, 3)
        right = QHBoxLayout()
        right.addWidget(QLabel("工作表："))
        self.sheet_combo = QComboBox(); self.sheet_combo.setFixedWidth(150)
        right.addWidget(self.sheet_combo); right.addStretch()
        row.addLayout(right, 1)
        src.setLayout(row)
        return src

    def _build_map_section(self):
        map_group = QGroupBox("2. 字段映射")
        row = QHBoxLayout(); row.setSpacing(4)

        self.grid_id_combo = QComboBox(); self.grid_id_combo.addItem(""); self.grid_id_combo.setMinimumWidth(100)
        self.grid_id_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        row = self._pair(row, "栅格编号：", self.grid_id_combo, last=False)

        for key, label, req in self.req_fields:
            combo = QComboBox(); combo.addItem(""); combo.setMinimumWidth(100)
            combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.map_combos[key] = combo
            display = f'{label}：<span style="color:red;">*</span>' if req else f'{label}：'
            lbl = QLabel(display); lbl.setTextFormat(Qt.RichText)
            pair = QHBoxLayout(); pair.setSpacing(2); pair.addWidget(lbl); pair.addWidget(combo)
            row.addLayout(pair)
            sp = QLabel(" "); sp.setFixedWidth(12); row.addWidget(sp)

        self.grid_size_spin = QDoubleSpinBox()
        self.grid_size_spin.setRange(10, 1000); self.grid_size_spin.setValue(self.style['grid_size_m'])
        self.grid_size_spin.setSuffix(" m"); self.grid_size_spin.setMaximumWidth(85)
        row = self._pair(row, "网格大小：", self.grid_size_spin, last=True)
        row.addStretch()
        map_group.setLayout(row)
        return map_group

    def _pair(self, row, label_text, widget, last=False):
        lbl = QLabel(label_text); lbl.setTextFormat(Qt.RichText)
        pair = QHBoxLayout(); pair.setSpacing(2); pair.addWidget(lbl); pair.addWidget(widget)
        row.addLayout(pair)
        if not last:
            sp = QLabel(" "); sp.setFixedWidth(12); row.addWidget(sp)
        return row

    def _build_style_section(self):
        style_group = QGroupBox("3. 样式设置（KML/KMZ/TAB 配色）")
        row = QHBoxLayout(); row.setSpacing(6)

        # 左：配色方案 + 色块
        self.build_level_controls(row, default_nine=False)
        row.addWidget(QLabel('图例大小：'))
        self.legend_size_combo=QComboBox()
        for label,width in [('小',300),('标准',360),('大',420)]:self.legend_size_combo.addItem(label,width)
        self.legend_size_combo.setCurrentIndex(1);row.addWidget(self.legend_size_combo)
        row.addStretch()
        outer = QVBoxLayout()
        outer.addLayout(row)
        row = QHBoxLayout()

        row.addWidget(QLabel("原始样本聚合："))
        self.aggregation_combo = QComboBox()
        self.aggregation_combo.addItems(["平均值", "中位数"])
        self.aggregation_combo.setToolTip("未选择栅格编号时，将原始样本按米制网格聚合")
        row.addWidget(self.aggregation_combo)

        row.addWidget(QLabel("最少样本："))
        self.min_samples_spin = QSpinBox()
        self.min_samples_spin.setRange(1, 1000000); self.min_samples_spin.setValue(1)
        self.min_samples_spin.setMaximumWidth(80)
        row.addWidget(self.min_samples_spin)

        row.addStretch()

        outer.addLayout(row)
        from widgets.map_style_controls import add_style_controls
        add_style_controls(self, outer)
        style_group.setLayout(outer)
        return style_group

    def auto_match_fields(self):
        super().auto_match_fields()
        if self.df is not None:
            for alias in ['栅格编号', 'grid_id', 'GridID', 'gridid']:
                if alias in self.df.columns: self.grid_id_combo.setCurrentText(alias); break
                cl = [c.lower() for c in self.df.columns]
                if alias.lower() in cl: self.grid_id_combo.setCurrentText(self.df.columns[cl.index(alias.lower())]); break

    def update_field_combos(self):
        super().update_field_combos()
        if self.df is not None and self.grid_id_combo:
            cols = [''] + list(self.df.columns)
            self.grid_id_combo.blockSignals(True)
            cur = self.grid_id_combo.currentText(); self.grid_id_combo.clear(); self.grid_id_combo.addItems(cols)
            if cur in cols: self.grid_id_combo.setCurrentText(cur)
            self.grid_id_combo.blockSignals(False)

    def get_current_mapping(self):
        m = super().get_current_mapping()
        g = self.grid_id_combo.currentText() if self.grid_id_combo else ''
        if g: m['grid_id'] = g
        return m

    def get_extra_params(self):
        return {
            'grid_size_m': self.grid_size_spin.value(),
            'level_colors': self.get_current_colors(),
            'grid_id_col': self.grid_id_combo.currentText() if self.grid_id_combo else '',
            **style_options(self),
            'legend_width': self.legend_size_combo.currentData(),
            'aggregation': 'median' if self.aggregation_combo.currentIndex() == 1 else 'mean',
            'min_samples': self.min_samples_spin.value(),
        }

    def generate(self):
        mapping = self.get_current_mapping()
        missing = [label for key, label, req in self.req_fields if req and key not in mapping]
        if missing: QMessageBox.warning(self, "警告", "请选择必选字段: {}".format(', '.join(missing))); return
        if self.df is None: QMessageBox.warning(self, "警告", "请先导入数据"); return
        out_dir = self.out_dir_edit.text()
        if not out_dir: QMessageBox.warning(self, "警告", "请选择输出目录"); return
        ext_map = {'KMZ': '.kmz', 'KML': '.kml', 'TAB': '.tab', 'SHP': '.shp', 'MIF': '.mif'}
        ext = '.kmz'
        for k, v in ext_map.items():
            if k in self.format_combo.currentText(): ext = v; break
        output_path = os.path.join(out_dir, "{}{}".format(self.filename_edit.text().strip() or self.get_default_filename(), ext))
        do_correct = self.coord_group.checkedId() == 1
        from widgets.worker_thread import GenerateWorker
        self._on_gen_start()
        self._worker = GenerateWorker('grid', self.df, mapping, self.style, output_path, do_correct, self.get_extra_params())
        self._worker.progress.connect(self._update_status)
        self._worker.log.connect(self._status)
        self._worker.finished.connect(lambda msg: (self._on_gen_done(), self._status(msg)))
        self._worker.error.connect(lambda msg: (self._on_gen_done(), self._status("错误: {}".format(msg))))
        self._worker.start()

    def get_template_data(self):
        return {
            '栅格编号': ['G001', 'G002', 'G003'],
            '经度': [108.3752, 108.3757, 108.3762], '纬度': [22.8185, 22.8185, 22.8185],
            '平均RSRP': [-95, -108, -82], '采样点数': [50, 30, 80],
        }
