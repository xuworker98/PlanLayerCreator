# -*- coding: utf-8 -*-
"""面域图层 Tab（WKT）"""
from PySide6.QtWidgets import (
    QPushButton, QColorDialog, QDoubleSpinBox, QComboBox,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QProgressBar, QMessageBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
import os
from tabs.base_tab import BaseTab


class PolygonTab(BaseTab):
    def __init__(self, parent=None):
        self.req_fields = [
            ('type_col', '唯一标识', True),
            ('wkt_col', 'WKT几何列', True),
        ]
        super().__init__('polygon', self.req_fields, parent)

    def get_default_style(self):
        return {'fill_color': '#74b9ff', 'line_color': '#0984e3', 'line_width': 1.0}

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

    # ====== 2. 字段映射：一行 4 组 ======

    def _build_map_section(self):
        map_group = QGroupBox("2. 字段映射")
        row = QHBoxLayout(); row.setSpacing(4)

        self.id_combo = QComboBox(); self.id_combo.addItem(""); self.id_combo.setMinimumWidth(80)
        self.id_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        pair0 = QHBoxLayout(); pair0.setSpacing(2)
        pair0.addWidget(QLabel("序号列："))
        pair0.addWidget(self.id_combo)
        row.addLayout(pair0)
        sp = QLabel(" "); sp.setFixedWidth(16); row.addWidget(sp)

        for key, label, req in self.req_fields:
            combo = QComboBox(); combo.addItem(""); combo.setMinimumWidth(120)
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

    # ====== 3. 样式设置：一行 4 组 ======

    def _build_style_section(self):
        style_group = QGroupBox("3. 样式设置（KML/KMZ/TAB 配色）")
        row = QHBoxLayout(); row.setSpacing(4)

        self.fill_color_btn = QPushButton(); self.fill_color_btn.setFixedSize(36, 18)
        self.fill_color_btn.setStyleSheet(f"background:{self.style['fill_color']};border:1px solid #dcdde1;border-radius:2px;")
        self.fill_color_btn.clicked.connect(lambda: self._pick('fill_color'))
        p1 = QHBoxLayout(); p1.setSpacing(2); p1.addWidget(QLabel("填充颜色：")); p1.addWidget(self.fill_color_btn)
        row.addLayout(p1)
        sp = QLabel(" "); sp.setFixedWidth(16); row.addWidget(sp)

        self.line_color_btn = QPushButton(); self.line_color_btn.setFixedSize(36, 18)
        self.line_color_btn.setStyleSheet(f"background:{self.style['line_color']};border:1px solid #dcdde1;border-radius:2px;")
        self.line_color_btn.clicked.connect(lambda: self._pick('line_color'))
        p2 = QHBoxLayout(); p2.setSpacing(2); p2.addWidget(QLabel("边框颜色：")); p2.addWidget(self.line_color_btn)
        row.addLayout(p2)
        sp2 = QLabel(" "); sp2.setFixedWidth(16); row.addWidget(sp2)

        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.5, 5.0); self.line_width_spin.setValue(self.style['line_width'])
        self.line_width_spin.setMaximumWidth(80)
        p3 = QHBoxLayout(); p3.setSpacing(2); p3.addWidget(QLabel("边框宽度：")); p3.addWidget(self.line_width_spin)
        row.addLayout(p3)
        row.addStretch()
        style_group.setLayout(row)
        return style_group

    def _pick(self, key):
        c = QColorDialog.getColor(QColor(self.style[key]), self, "选择颜色")
        if c.isValid():
            self.style[key] = c.name()
            btn = self.fill_color_btn if key == 'fill_color' else self.line_color_btn
            btn.setStyleSheet(f"background:{c.name()};border:1px solid #dcdde1;border-radius:2px;")

    def update_field_combos(self):
        super().update_field_combos()
        if self.df is not None and self.id_combo:
            cols = [''] + list(self.df.columns)
            self.id_combo.blockSignals(True)
            cur = self.id_combo.currentText(); self.id_combo.clear(); self.id_combo.addItems(cols)
            if cur in cols: self.id_combo.setCurrentText(cur)
            self.id_combo.blockSignals(False)

    def auto_match_fields(self):
        super().auto_match_fields()
        if self.df is not None:
            am = {'type_col': ['类型', 'type', 'Type'], 'wkt_col': ['WKT', 'wkt', 'geometry', 'geom']}
            cols = list(self.df.columns); cl = [c.lower() for c in cols]
            for key, aliases in am.items():
                if key not in self.map_combos: continue
                for a in aliases:
                    if a in cols: self.map_combos[key].setCurrentText(a); break
                    if a.lower() in cl: self.map_combos[key].setCurrentText(cols[cl.index(a.lower())]); break

    def get_current_mapping(self):
        m = super().get_current_mapping()
        if self.id_combo and self.id_combo.currentText(): m['id_col'] = self.id_combo.currentText()
        return m

    def get_extra_params(self):
        return {
            'fill_color': self.style['fill_color'], 'line_color': self.style['line_color'],
            'line_width': self.line_width_spin.value(),
        }

    def generate(self):
        mapping = self.get_current_mapping()
        missing = [label for key, label, req in self.req_fields if req and key not in mapping]
        if missing: QMessageBox.warning(self, "警告", f"请选择必选字段: {', '.join(missing)}"); return
        if self.df is None: QMessageBox.warning(self, "警告", "请先导入数据"); return
        out_dir = self.out_dir_edit.text()
        if not out_dir: QMessageBox.warning(self, "警告", "请选择输出目录"); return
        ext_map = {'KMZ': '.kmz', 'KML': '.kml', 'TAB': '.tab', 'SHP': '.shp'}
        ext = '.kmz'
        for k, v in ext_map.items():
            if k in self.format_combo.currentText(): ext = v; break
        output_path = os.path.join(out_dir, f"{self.filename_edit.text().strip() or self.get_default_filename()}{ext}")
        do_correct = self.coord_group.checkedId() == 1
        from widgets.worker_thread import GenerateWorker
        self._on_gen_start()
        self._worker = GenerateWorker('polygon', self.df, mapping, self.style, output_path, do_correct, self.get_extra_params())
        self._worker.progress.connect(self.set_progress)
        self._worker.log.connect(self._status)
        self._worker.finished.connect(lambda msg: (self._on_gen_done(), self._status(msg)))
        self._worker.error.connect(lambda msg: (self._on_gen_done(), self._status(f"错误: {msg}")))
        self._worker.start()

    def get_template_data(self):
        return {
            '序号': [1], '类型': ['POLYGON'],
            'WKT': ['POLYGON ((108.3718 22.8715, 108.3748 22.8715, 108.3748 22.8745, 108.3718 22.8745, 108.3718 22.8715))'],
        }
