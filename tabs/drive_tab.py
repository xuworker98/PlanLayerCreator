# -*- coding: utf-8 -*-
"""路测图层 Tab"""
from PySide6.QtWidgets import (
    QPushButton, QCheckBox, QDoubleSpinBox, QComboBox,
    QGroupBox, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QSizePolicy, QProgressBar, QColorDialog, QMessageBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
import os
from tabs.base_tab import BaseTab
from utils.constants import LEVEL_COLORS_9, LEVEL_COLORS_6


class DriveTab(BaseTab):
    def __init__(self, parent=None):
        self.req_fields = [
            ('lon', '经度', True), ('lat', '纬度', True), ('level', '测量电平值', True),
        ]
        super().__init__('drive', self.req_fields, parent)
        self.format_combo.clear()
        self.format_combo.addItems([
            'KMZ (压缩推荐)', 'KML (未压缩)', 'TAB (原生着色)',
            'SHP (含属性)', 'MIF (交换格式)',
        ])

    def get_default_style(self):
        return {
            'show_label': False, 'scale': 0.8,
            'level_colors': [list(x) for x in LEVEL_COLORS_9], 'preset': '9档',
        }

    # ====== 1. 数据源 ======

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

    # ====== 2. 字段映射 ======

    def _build_map_section(self):
        map_group = QGroupBox("2. 字段映射")
        row = QHBoxLayout(); row.setSpacing(4)
        for key, label, req in self.req_fields:
            combo = QComboBox(); combo.addItem(""); combo.setMinimumWidth(100)
            combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.map_combos[key] = combo
            display = f'{label}：<span style="color:red;">*</span>' if req else f'{label}：'
            lbl = QLabel(display); lbl.setTextFormat(Qt.RichText)
            pair = QHBoxLayout(); pair.setSpacing(2); pair.addWidget(lbl); pair.addWidget(combo)
            row.addLayout(pair)
            if key != self.req_fields[-1][0]:
                sp = QLabel(" "); sp.setFixedWidth(16); row.addWidget(sp)
        row.addStretch()
        map_group.setLayout(row)
        return map_group

    # ====== 3. 样式设置：色块按钮组 ======

    def _build_style_section(self):
        style_group = QGroupBox("3. 样式设置（KML/KMZ/TAB 配色）")
        layout = QVBoxLayout(); layout.setSpacing(6)

        row = QHBoxLayout(); row.setSpacing(6)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["9档（精细）", "6档（简化）", "自定义"])
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        pair = QHBoxLayout(); pair.setSpacing(2)
        pair.addWidget(QLabel("配色方案：")); pair.addWidget(self.preset_combo)
        row.addLayout(pair)

        sp = QLabel(" "); sp.setFixedWidth(12); row.addWidget(sp)

        # 色块按钮组
        self._color_btns = []
        for i, (low, high, ch) in enumerate(self.style['level_colors']):
            btn = QPushButton()
            btn.setFixedSize(28, 20)
            btn.setStyleSheet(f"background:{ch};border:1px solid #b2bec3;border-radius:2px;")
            tip = f'{int(low) if low > -999 else "-∞"} ~ {int(high) if high < 999 else "+∞"}'
            btn.setToolTip(tip)
            idx = i
            btn.clicked.connect(lambda checked, ii=idx: self._pick_color(ii))
            self._color_btns.append(btn)
            row.addWidget(btn)

        sp2 = QLabel(" "); sp2.setFixedWidth(16); row.addWidget(sp2)

        self.show_label_cb = QCheckBox("显示标签")
        self.show_label_cb.setChecked(self.style['show_label'])
        row.addWidget(self.show_label_cb)

        sp3 = QLabel(" "); sp3.setFixedWidth(16); row.addWidget(sp3)

        p4 = QHBoxLayout(); p4.setSpacing(2)
        p4.addWidget(QLabel("图标大小："))
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 5.0); self.scale_spin.setValue(self.style['scale'])
        self.scale_spin.setMaximumWidth(70)
        p4.addWidget(self.scale_spin)
        row.addLayout(p4)
        row.addStretch()
        layout.addLayout(row)
        style_group.setLayout(layout)
        return style_group

    def _pick_color(self, idx):
        old = self.style['level_colors'][idx][2]
        c = QColorDialog.getColor(QColor(old), self, f"配色档位 {idx+1}")
        if c.isValid():
            self.style['level_colors'][idx][2] = c.name()
            self._color_btns[idx].setStyleSheet(f"background:{c.name()};border:1px solid #b2bec3;border-radius:2px;")

    def _rebuild_colors(self):
        for i, (_, _, ch) in enumerate(self.style['level_colors']):
            if i < len(self._color_btns):
                self._color_btns[i].setStyleSheet(f"background:{ch};border:1px solid #b2bec3;border-radius:2px;")

    def on_preset_changed(self, idx):
        if idx == 0: self.style['level_colors'] = [list(x) for x in LEVEL_COLORS_9]; self.style['preset'] = '9档'
        elif idx == 1: self.style['level_colors'] = [list(x) for x in LEVEL_COLORS_6]; self.style['preset'] = '6档'
        self._rebuild_colors()

    def get_current_colors(self):
        return [(lo, hi, ch) for lo, hi, ch in self.style['level_colors']]

    def get_extra_params(self):
        return {
            'level_colors': self.get_current_colors(),
            'show_label': self.show_label_cb.isChecked(),
            'scale': self.scale_spin.value(),
        }

    def generate(self):
        mapping = self.get_current_mapping()
        missing = [label for key, label, req in self.req_fields if req and key not in mapping]
        if missing: QMessageBox.warning(self, "警告", f"请选择必选字段: {', '.join(missing)}"); return
        if self.df is None: QMessageBox.warning(self, "警告", "请先导入数据"); return
        out_dir = self.out_dir_edit.text()
        if not out_dir: QMessageBox.warning(self, "警告", "请选择输出目录"); return
        ext_map = {'KMZ': '.kmz', 'KML': '.kml', 'TAB': '.tab', 'SHP': '.shp', 'MIF': '.mif'}
        ext = '.kmz'
        for k, v in ext_map.items():
            if k in self.format_combo.currentText(): ext = v; break
        output_path = os.path.join(out_dir, f"{self.filename_edit.text().strip() or self.get_default_filename()}{ext}")
        do_correct = self.coord_group.checkedId() == 1
        from widgets.worker_thread import GenerateWorker
        self._on_gen_start()
        self._worker = GenerateWorker('drive', self.df, mapping, self.style, output_path, do_correct, self.get_extra_params())
        self._worker.progress.connect(self.set_progress)
        self._worker.log.connect(self._status)
        self._worker.finished.connect(lambda msg: (self._on_gen_done(), self._status(msg)))
        self._worker.error.connect(lambda msg: (self._on_gen_done(), self._status(f"错误: {msg}")))
        self._worker.start()

    def get_template_data(self):
        return {
            '时间戳': ['2026-01-01', '2026-01-01'], '经度': [108.3752, 108.3755],
            '纬度': [22.8185, 22.8188], 'SS-RSRP': [-95, -100],
        }
