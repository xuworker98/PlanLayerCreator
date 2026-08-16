# -*- coding: utf-8 -*-
"""Tab 基类：上下逐项布局，子类可覆盖各区块"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QProgressBar,
    QFileDialog, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
import os
import pandas as pd
from utils.constants import FIELD_ALIASES, OUTPUT_FORMATS


class BaseTab(QWidget):
    MAP_COLS = 2
    STYLE_COLS = 2

    def __init__(self, layer_type, required_fields, parent=None):
        super().__init__(parent)
        self.layer_type = layer_type
        self.required_fields = required_fields
        self.df = None
        self.current_file = ""
        self.current_sheet = ""
        self.sheet_names = []
        self.mapping = {}
        self.map_combos = {}
        self.style = self.get_default_style()
        self._worker = None
        self._map_row = 0
        self._map_col = 0
        self._sty_row = 0
        self._sty_col = 0
        self.init_ui()
        self.setup_connections()

    def get_default_style(self):
        return {}

    def get_layer_display_name(self):
        names = {
            'site': '站点图层', 'sector': '扇区图层', 'drive': '路测图层',
            'grid': '栅格图层', 'line': '线路图层', 'polygon': '面域图层'
        }
        return names.get(self.layer_type, '图层')

    def get_default_filename(self):
        return f'{self.get_layer_display_name()}-未命名'

    # ========== UI 入口 ==========

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 6, 10, 6)
        main_layout.setAlignment(Qt.AlignTop)

        main_layout.addWidget(self._build_data_section())
        main_layout.addWidget(self._build_map_section())
        main_layout.addWidget(self._build_style_section())
        main_layout.addWidget(self._build_output_section())
        main_layout.addWidget(self._build_coord_section())
        main_layout.addLayout(self._build_button_row())

    # ========== 1. 数据源 ==========

    def _build_data_section(self):
        src = QGroupBox("1. 数据源")
        src_layout = QVBoxLayout()
        src_layout.setSpacing(4)
        file_row = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("请选择数据文件（Excel/CSV/TXT）...")
        self.file_edit.setReadOnly(True)
        file_row.addWidget(self.file_edit, 1)
        for text, slot, w in [("浏览", self.browse_file, 65), ("模板", self.download_template, 55)]:
            btn = QPushButton(text)
            btn.setFixedWidth(w)
            btn.clicked.connect(slot)
            file_row.addWidget(btn)
        src_layout.addLayout(file_row)
        sheet_row = QHBoxLayout()
        sheet_row.addWidget(QLabel("工作表："))
        self.sheet_combo = QComboBox()
        self.sheet_combo.setFixedWidth(150)
        sheet_row.addWidget(self.sheet_combo)
        sheet_row.addStretch()
        src_layout.addLayout(sheet_row)
        src.setLayout(src_layout)
        return src

    # ========== 2. 字段映射 ==========

    def _build_map_section(self):
        map_group = QGroupBox("2. 字段映射")
        cols = max(2, getattr(self, 'MAP_COLS', 2)) * 2
        self.map_grid = QGridLayout()
        self.map_grid.setHorizontalSpacing(12)
        self.map_grid.setVerticalSpacing(6)
        for c in range(cols):
            self.map_grid.setColumnStretch(c, 1 if c % 2 == 1 else 0)
        self._map_row = 0
        self._map_col = 0
        self.init_field_mapping_ui()
        map_group.setLayout(self.map_grid)
        return map_group

    # ========== 3. 样式设置 ==========

    def _build_style_section(self):
        style_group = QGroupBox("3. 样式设置（KML/KMZ/TAB 配色）")
        sc = max(2, getattr(self, 'STYLE_COLS', 2)) * 2
        self.style_grid = QGridLayout()
        self.style_grid.setHorizontalSpacing(12)
        self.style_grid.setVerticalSpacing(6)
        for c in range(sc):
            self.style_grid.setColumnStretch(c, 1 if c % 2 == 1 else 0)
        self._sty_row = 0
        self._sty_col = 0
        self.init_style_ui()
        style_group.setLayout(self.style_grid)
        return style_group

    # ========== 4. 输出设置 ==========

    def _build_output_section(self):
        out_group = QGroupBox("4. 输出设置")
        out_grid = QGridLayout()
        out_grid.setHorizontalSpacing(12)
        out_grid.setVerticalSpacing(6)
        out_grid.setColumnStretch(0, 0)
        out_grid.setColumnStretch(1, 1)
        out_grid.setColumnStretch(2, 0)
        out_grid.setColumnStretch(3, 1)
        out_grid.setColumnStretch(4, 0)

        out_grid.addWidget(QLabel("目录："), 0, 0)
        dir_row = QHBoxLayout()
        self.out_dir_edit = QLineEdit()
        # 默认桌面路径（不创建，生成时按需创建）
        layer_names = {'site':'站点图层','sector':'扇区图层','drive':'路测图层',
                       'grid':'栅格图层','line':'线路图层','polygon':'面域图层'}
        folder_name = layer_names.get(self.layer_type, '输出图层')
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        default_out = os.path.join(desktop, folder_name)
        self.out_dir_edit.setText(default_out)
        dir_row.addWidget(self.out_dir_edit, 1)
        btn_out = QPushButton("浏览")
        btn_out.setFixedWidth(55)
        btn_out.clicked.connect(self.select_output_dir)
        dir_row.addWidget(btn_out)
        out_grid.addLayout(dir_row, 0, 1, 1, 3)

        out_grid.addWidget(QLabel("文件名："), 1, 0)
        self.filename_edit = QLineEdit()
        self.filename_edit.setText(self.get_default_filename())
        out_grid.addWidget(self.filename_edit, 1, 1)

        out_grid.addWidget(QLabel("格式："), 1, 2)
        self.format_combo = QComboBox()
        self.format_combo.addItems(OUTPUT_FORMATS)
        self.format_combo.setCurrentIndex(0)
        out_grid.addWidget(self.format_combo, 1, 3)

        out_group.setLayout(out_grid)
        return out_group

    # ========== 5. 坐标系 ==========

    def _build_coord_section(self):
        coord_group = QGroupBox("5. 坐标系")
        row = QHBoxLayout()
        row.setSpacing(16)

        self.coord_original_radio = self._radio("原坐标输出（WGS84）", True)
        self.coord_correct_radio = self._radio("纠偏输出（GCJ-02 → WGS84）", False)
        from PySide6.QtWidgets import QButtonGroup
        self.coord_group = QButtonGroup(self)
        self.coord_group.addButton(self.coord_original_radio, 0)
        self.coord_group.addButton(self.coord_correct_radio, 1)

        row.addWidget(self.coord_original_radio)
        row.addWidget(self.coord_correct_radio)
        from PySide6.QtWidgets import QCheckBox
        self.smart_detect_cb = QCheckBox("启用智能检测")
        self.smart_detect_cb.setChecked(True)
        row.addWidget(self.smart_detect_cb)

        self.smart_result_label = QLabel("")
        self.smart_result_label.setStyleSheet("color: #00b894; font-size: 11px;")
        row.addWidget(self.smart_result_label)
        row.addStretch()
        coord_group.setLayout(row)
        return coord_group

    # ========== 底部按钮 ==========

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
        self.btn_cancel.setVisible(False)

        self.btn_open_folder = QPushButton("打开文件夹")
        self.btn_open_folder.setFixedWidth(100)
        self.btn_open_folder.clicked.connect(self.open_output_folder)

        btn_row.addWidget(self.progress_bar)
        btn_row.addWidget(self.btn_generate)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_open_folder)
        btn_row.addStretch()
        return btn_row

    # ========== 子类重写 ==========

    def init_field_mapping_ui(self):
        pass

    def init_style_ui(self):
        pass

    # ========== 网格辅助 ==========

    def _radio(self, text, checked):
        from PySide6.QtWidgets import QRadioButton
        rb = QRadioButton(text)
        rb.setChecked(checked)
        return rb

    def add_map_row(self, label, widget, required=False):
        cols = max(2, getattr(self, 'MAP_COLS', 2))
        display = f'{label}：<span style="color:red;">*</span>' if required else f'{label}：'
        lbl = QLabel(display)
        lbl.setTextFormat(Qt.RichText)
        widget.setMinimumWidth(60)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        c = self._map_col * 2
        self.map_grid.addWidget(lbl, self._map_row, c)
        self.map_grid.addWidget(widget, self._map_row, c + 1)
        self._map_col += 1
        if self._map_col >= cols:
            self._map_col = 0
            self._map_row += 1

    def add_style_row(self, label, widget):
        cols = max(2, getattr(self, 'STYLE_COLS', 2))
        c = self._sty_col * 2
        if label:
            lbl = QLabel(f'{label}：')
            self.style_grid.addWidget(lbl, self._sty_row, c)
            self.style_grid.addWidget(widget, self._sty_row, c + 1)
        else:
            self.style_grid.addWidget(widget, self._sty_row, c, 1, 2)
        self._sty_col += 1
        if self._sty_col >= cols:
            self._sty_col = 0
            self._sty_row += 1

    def add_style_span(self, widget, colspan=4):
        cols = max(2, getattr(self, 'STYLE_COLS', 2)) * 2
        span = min(colspan, cols)
        self.style_grid.addWidget(widget, self._sty_row, 0, 1, span)
        self._sty_row += 1
        self._sty_col = 0

    def add_map_span(self, widget, colspan=4):
        cols = max(2, getattr(self, 'MAP_COLS', 2)) * 2
        span = min(colspan, cols)
        self.map_grid.addWidget(widget, self._map_row, 0, 1, span)
        self._map_row += 1
        self._map_col = 0

    # ========== 通用方法 ==========

    def setup_connections(self):
        self.sheet_combo.currentTextChanged.connect(self.on_sheet_changed)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "",
            "表格文件 (*.xlsx *.xls *.xlsm *.csv *.txt);;Excel (*.xlsx *.xls);;CSV (*.csv);;TXT (*.txt)")
        if path:
            self.import_file(path)

    def import_file(self, path):
        try:
            ext = path.lower()
            if ext.endswith('.csv'):
                for enc in ['utf-8', 'gbk', 'utf-8-sig']:
                    try:
                        self.df = pd.read_csv(path, encoding=enc); self.sheet_names = ['默认']; break
                    except: continue
                else:
                    self.df = pd.read_csv(path, encoding='utf-8', errors='replace'); self.sheet_names = ['默认']
            elif ext.endswith('.txt'):
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    first = f.readline()
                sep = '\t' if first.count('\t') > first.count(',') else ','
                for enc in ['utf-8', 'gbk', 'utf-8-sig']:
                    try:
                        self.df = pd.read_csv(path, encoding=enc, sep=sep); self.sheet_names = ['默认']; break
                    except: continue
                else:
                    self.df = pd.read_csv(path, encoding='utf-8', errors='replace', sep=sep); self.sheet_names = ['默认']
            else:
                engine = 'openpyxl' if path.endswith('.xlsx') else 'xlrd'
                xl = pd.ExcelFile(path, engine=engine)
                self.sheet_names = xl.sheet_names
                self.df = pd.read_excel(path, sheet_name=0, engine=engine)
            if self.df is None or self.df.empty:
                QMessageBox.warning(self, "警告", "未读取到有效数据"); return
            self.current_file = path
            self.current_sheet = self.sheet_names[0] if self.sheet_names else ''
            self.file_edit.setText(path)
            self.sheet_combo.blockSignals(True); self.sheet_combo.clear(); self.sheet_combo.addItems(self.sheet_names)
            if self.sheet_names: self.sheet_combo.setCurrentIndex(0)
            self.sheet_combo.blockSignals(False)
            self.update_field_combos()
            self._status(f"已导入 {os.path.basename(path)}, {len(self.df)} 行")
            self.auto_match_fields()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def update_field_combos(self):
        if self.df is None: return
        columns = [''] + list(self.df.columns)
        for combo in self.map_combos.values():
            combo.blockSignals(True)
            cur = combo.currentText(); combo.clear(); combo.addItems(columns)
            if cur in columns: combo.setCurrentText(cur)
            combo.blockSignals(False)

    def auto_match_fields(self):
        if self.df is None: return
        cols_lower = [c.lower() for c in self.df.columns]
        for key, combo in self.map_combos.items():
            if key in FIELD_ALIASES:
                for alias in FIELD_ALIASES[key]:
                    if alias in self.df.columns: combo.setCurrentText(alias); break
                    if alias.lower() in cols_lower:
                        combo.setCurrentText(self.df.columns[cols_lower.index(alias.lower())]); break

    def on_sheet_changed(self, sheet_name):
        if not sheet_name or self.df is None or not self.current_file: return
        if self.current_file.lower().endswith(('.csv', '.txt')): return
        try:
            self.df = pd.read_excel(self.current_file, sheet_name=sheet_name)
            self.current_sheet = sheet_name
            self.update_field_combos(); self.auto_match_fields()
            self._status(f"切换: {sheet_name}, {len(self.df)} 行")
        except Exception as e:
            self._status(f"切换失败: {e}")

    def select_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path: self.out_dir_edit.setText(path)

    def get_current_mapping(self):
        return {k: c.currentText() for k, c in self.map_combos.items() if c.currentText()}

    def get_extra_params(self):
        return {}

    def download_template(self):
        data = self.get_template_data()
        if not data: QMessageBox.information(self, "提示", "暂无模板"); return
        path, _ = QFileDialog.getSaveFileName(self, "保存模板", f'{self.layer_type}_template.xlsx', "Excel (*.xlsx)")
        if path: pd.DataFrame(data).to_excel(path, index=False); QMessageBox.information(self, "成功", f"已保存:\n{path}")

    def get_template_data(self):
        return {}

    def generate(self):
        QMessageBox.information(self, "提示", "功能开发中，敬请期待...")

    def cancel_generate(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._status("已取消")

    def open_output_folder(self):
        path = self.out_dir_edit.text()
        if path and os.path.isdir(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, "提示", "目录不存在")

    def set_smart_result(self, text, color='#00b894'):
        self.smart_result_label.setText(text)
        self.smart_result_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _status(self, msg):
        win = self.window()
        if win and hasattr(win, 'status_label'):
            win.status_label.setText(msg[:80])

    def set_progress(self, value):
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(value)
            if value >= 100:
                self.progress_bar.setVisible(False)

    def _update_status(self, pct, msg):
        self.set_progress(pct)
        self._status(msg)

    def _on_gen_start(self):
        self.btn_generate.setVisible(False)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

    def _on_gen_done(self):
        self.btn_generate.setVisible(True)
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
