# -*- coding: utf-8 -*-
"""制作扇区 Tab"""
from PySide6.QtWidgets import (
    QPushButton, QColorDialog, QSpinBox, QDoubleSpinBox, QComboBox,
    QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
    QSizePolicy, QProgressBar, QCheckBox, QMessageBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
import os
from tabs.base_tab import BaseTab
from utils.constants import (
    SECTOR_COLORS, SECTOR_OTHER_COLOR, SECTOR_DEFAULT_ALPHA,
    SECTOR_DEFAULT_LINE_COLOR, SECTOR_DEFAULT_LINE_WIDTH,
    SECTOR_DEFAULT_BW, SECTOR_DEFAULT_RADIUS
)


class SectorTab(BaseTab):
    def __init__(self, parent=None):
        self.req_fields = [
            ('lon', '经度', True),
            ('lat', '纬度', True),
            ('name', '小区名称', True),
            ('azimuth', '方位角', True),
        ]
        self.site_id_combo = None
        self.bw_combo = None
        self.radius_combo = None
        super().__init__('sector', self.req_fields, parent)

    def get_default_style(self):
        return {
            'colors': dict(SECTOR_COLORS),
            'other_color': SECTOR_OTHER_COLOR,
            'alpha': SECTOR_DEFAULT_ALPHA,
            'line_color': SECTOR_DEFAULT_LINE_COLOR,
            'line_width': SECTOR_DEFAULT_LINE_WIDTH,
            'rule': 2,
        }

    # ====== 1. 数据源（同站点标准） ======

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

    # ====== 2. 字段映射：第一行4组 + 第二行5组 ======

    def _build_map_section(self):
        map_group = QGroupBox("2. 字段映射")
        layout = QVBoxLayout(); layout.setSpacing(6)

        # 第一行：4 组必选
        row1 = QHBoxLayout(); row1.setSpacing(4)
        for key, label, req in self.req_fields:
            combo = QComboBox(); combo.addItem(""); combo.setMinimumWidth(100)
            combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.map_combos[key] = combo
            display = f'{label}：<span style="color:red;">*</span>' if req else f'{label}：'
            lbl = QLabel(display); lbl.setTextFormat(Qt.RichText)
            pair = QHBoxLayout(); pair.setSpacing(2); pair.addWidget(lbl); pair.addWidget(combo)
            row1.addLayout(pair)
            if key != self.req_fields[-1][0]:
                sp = QLabel(" "); sp.setFixedWidth(16); row1.addWidget(sp)
        row1.addStretch()
        layout.addLayout(row1)

        # 第二行：5 组可选
        row2 = QHBoxLayout(); row2.setSpacing(4)
        self.site_id_combo = QComboBox(); self.site_id_combo.addItem(""); self.site_id_combo.setMinimumWidth(100)
        self.site_id_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        row2 = self._add_map_item(row2, "基站标识：", self.site_id_combo, last=False)

        self.bw_combo = QComboBox(); self.bw_combo.addItem(""); self.bw_combo.setMinimumWidth(100)
        self.bw_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        row2 = self._add_map_item(row2, "波瓣角列：", self.bw_combo, last=False)

        self.radius_combo = QComboBox(); self.radius_combo.addItem(""); self.radius_combo.setMinimumWidth(100)
        self.radius_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        row2 = self._add_map_item(row2, "覆盖半径列：", self.radius_combo, last=False)

        self.bw_default_spin = QDoubleSpinBox()
        self.bw_default_spin.setRange(10, 180); self.bw_default_spin.setValue(SECTOR_DEFAULT_BW)
        self.bw_default_spin.setMinimumWidth(50)
        row2 = self._add_map_item(row2, "默认波瓣角：", self.bw_default_spin, last=False)

        self.radius_default_spin = QDoubleSpinBox()
        self.radius_default_spin.setRange(10, 10000); self.radius_default_spin.setValue(SECTOR_DEFAULT_RADIUS)
        self.radius_default_spin.setMinimumWidth(50)
        row2 = self._add_map_item(row2, "默认覆盖半径：", self.radius_default_spin, last=True)

        row2.addStretch()
        layout.addLayout(row2)
        map_group.setLayout(layout)
        return map_group

    def _add_map_item(self, row, label_text, widget, last=False):
        lbl = QLabel(label_text); lbl.setTextFormat(Qt.RichText)
        pair = QHBoxLayout(); pair.setSpacing(2); pair.addWidget(lbl); pair.addWidget(widget)
        row.addLayout(pair)
        if not last:
            sp = QLabel(" "); sp.setFixedWidth(16); row.addWidget(sp)
        return row

    # ====== 3. 样式设置 ======

    def _build_style_section(self):
        style_group = QGroupBox("3. 样式设置（KML/KMZ/TAB 配色）")
        layout = QVBoxLayout(); layout.setSpacing(6)

        # 第一行：编号规则
        row1 = QHBoxLayout(); row1.setSpacing(2)
        self.rule_combo = QComboBox()
        self.rule_combo.addItems(["规则一（正北±60°首扇区）", "规则二（简单顺时针，默认）"])
        self.rule_combo.setCurrentIndex(1)
        self.rule_combo.setMaximumWidth(300)
        row1.addWidget(QLabel("编号规则："))
        row1.addWidget(self.rule_combo)
        row1.addStretch()
        layout.addLayout(row1)

        # 第二行：4 组颜色
        row2 = QHBoxLayout(); row2.setSpacing(4)
        self.sector_color_btns = {}
        labels_c = ["扇区1颜色：", "扇区2颜色：", "扇区3颜色：", "其他扇区颜色："]
        keys_c = [1, 2, 3, 'other']
        for i, (lbl_text, key) in enumerate(zip(labels_c, keys_c)):
            btn = QPushButton(); btn.setFixedSize(36, 18)
            clr = self.style['colors'][key] if key != 'other' else self.style['other_color']
            btn.setStyleSheet(f"background:{clr};border:1px solid #dcdde1;border-radius:2px;")
            if key == 'other':
                btn.clicked.connect(self.pick_other_color)
            else:
                btn.clicked.connect(lambda checked, idx=key: self.pick_sector_color(idx))
            self.sector_color_btns[key] = btn
            pair = QHBoxLayout(); pair.setSpacing(2)
            pair.addWidget(QLabel(lbl_text)); pair.addWidget(btn)
            row2.addLayout(pair)
            if i < 3:
                sp = QLabel(" "); sp.setFixedWidth(16); row2.addWidget(sp)
        row2.addStretch()
        layout.addLayout(row2)

        # 第三行：3 组
        row3 = QHBoxLayout(); row3.setSpacing(4)
        self.alpha_spin = QSpinBox(); self.alpha_spin.setRange(0, 255); self.alpha_spin.setValue(self.style['alpha'])
        self.alpha_spin.setMaximumWidth(80)
        row3 = self._add_style_item(row3, "填充透明度：", self.alpha_spin, last=False)

        self.line_color_btn = QPushButton(); self.line_color_btn.setFixedSize(36, 18)
        self.line_color_btn.setStyleSheet(f"background:{self.style['line_color']};border:1px solid #dcdde1;border-radius:2px;")
        self.line_color_btn.clicked.connect(self.pick_line_color)
        row3 = self._add_style_item(row3, "边框颜色：", self.line_color_btn, last=False)

        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.5, 5.0); self.line_width_spin.setValue(self.style['line_width'])
        self.line_width_spin.setMaximumWidth(80)
        row3 = self._add_style_item(row3, "边框宽度：", self.line_width_spin, last=True)
        row3.addStretch()
        layout.addLayout(row3)
        style_group.setLayout(layout)
        return style_group

    def _add_style_item(self, row, label_text, widget, last=False):
        pair = QHBoxLayout(); pair.setSpacing(2)
        pair.addWidget(QLabel(label_text)); pair.addWidget(widget)
        row.addLayout(pair)
        if not last:
            sp = QLabel(" "); sp.setFixedWidth(16); row.addWidget(sp)
        return row

    # ====== 4. 输出 + 5. 坐标系 + 按钮：同基类 ======

    # ====== 颜色选择 ======

    def pick_sector_color(self, idx):
        c = QColorDialog.getColor(QColor(self.style['colors'][idx]), self, f"扇区{idx}")
        if c.isValid():
            self.style['colors'][idx] = c.name()
            self.sector_color_btns[idx].setStyleSheet(f"background:{c.name()};border:1px solid #dcdde1;border-radius:2px;")

    def pick_other_color(self):
        c = QColorDialog.getColor(QColor(self.style['other_color']), self, "其他扇区")
        if c.isValid():
            self.style['other_color'] = c.name()
            self.sector_color_btns['other'].setStyleSheet(f"background:{c.name()};border:1px solid #dcdde1;border-radius:2px;")

    def pick_line_color(self):
        c = QColorDialog.getColor(QColor(self.style['line_color']), self, "边框颜色")
        if c.isValid():
            self.style['line_color'] = c.name()
            self.line_color_btn.setStyleSheet(f"background:{c.name()};border:1px solid #dcdde1;border-radius:2px;")

    # ====== 通用 ======

    def update_field_combos(self):
        super().update_field_combos()
        if self.df is not None:
            columns = [''] + list(self.df.columns)
            for combo in [self.site_id_combo, self.bw_combo, self.radius_combo]:
                if combo:
                    combo.blockSignals(True)
                    cur = combo.currentText(); combo.clear(); combo.addItems(columns)
                    if cur in columns: combo.setCurrentText(cur)
                    combo.blockSignals(False)

    def auto_match_fields(self):
        super().auto_match_fields()
        if self.df is not None:
            aliases = {'site_id': ['siteid', 'site_id', '基站标识', '基站ID'],
                       'beamwidth': ['beamwidth', 'bw', '波束宽度', '波瓣角'],
                       'radius': ['radius', '覆盖半径', '半径']}
            cols_lower = [c.lower() for c in self.df.columns]
            for key, combo in [('site_id', self.site_id_combo), ('beamwidth', self.bw_combo), ('radius', self.radius_combo)]:
                if not combo: continue
                for alias in aliases.get(key, []):
                    if alias in self.df.columns: combo.setCurrentText(alias); break
                    if alias.lower() in cols_lower: combo.setCurrentText(self.df.columns[cols_lower.index(alias.lower())]); break

    def get_extra_params(self):
        return {
            'rule': self.rule_combo.currentIndex() + 1,
            'bw_default': self.bw_default_spin.value(), 'r_default': self.radius_default_spin.value(),
            'bw_col': self.bw_combo.currentText() if self.bw_combo else '',
            'r_col': self.radius_combo.currentText() if self.radius_combo else '',
            'other_color': self.style['other_color'],
            'site_col': self.site_id_combo.currentText() if self.site_id_combo else '',
        }

    def generate(self):
        mapping = self.get_current_mapping()
        missing = [label for key, label, req in self.req_fields if req and key not in mapping]
        if missing:
            QMessageBox.warning(self, "警告", f"请选择必选字段: {', '.join(missing)}")
            return
        if self.df is None:
            QMessageBox.warning(self, "警告", "请先导入数据")
            return
        out_dir = self.out_dir_edit.text()
        if not out_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return
        filename = self.filename_edit.text().strip() or self.get_default_filename()
        ext_map = {'KMZ': '.kmz', 'KML': '.kml', 'TAB': '.tab', 'SHP': '.shp'}
        ext = '.kmz'
        fmt = self.format_combo.currentText()
        for k, v in ext_map.items():
            if k in fmt: ext = v; break
        output_path = os.path.join(out_dir, f"{filename}{ext}")
        do_correct = self.coord_group.checkedId() == 1
        extra = self.get_extra_params()

        from widgets.worker_thread import GenerateWorker
        self._on_gen_start()
        self._worker = GenerateWorker('sector', self.df, mapping, self.style, output_path, do_correct, extra)
        self._worker.progress.connect(self.set_progress)
        self._worker.log.connect(self._status)
        self._worker.finished.connect(lambda msg: (self._on_gen_done(), self._status(msg)))
        self._worker.error.connect(lambda msg: (self._on_gen_done(), self._status(f"错误: {msg}")))
        self._worker.start()

    def get_template_data(self):
        return {
            '基站标识': ['S001', 'S001', 'S001'], '小区名称': ['A', 'B', 'C'],
            '经度': [108.3718, 108.3718, 108.3718], '纬度': [22.8715, 22.8715, 22.8715],
            '方位角': [0, 120, 240], '波束宽度': [65, 65, 65], '覆盖半径': [100, 100, 100],
        }
