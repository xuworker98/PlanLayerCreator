"""Editable, portable signal-level schemes (JSON uses strings for infinity)."""
import json
import math
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialogButtonBox, QComboBox, QLabel, QMessageBox, QColorDialog,
    QFileDialog, QHeaderView,
)
from PySide6.QtGui import QColor
from utils.level_scheme import validate_scheme, number


class LevelEditor(QDialog):
    def __init__(self, colors, boundary='right', parent=None):
        super().__init__(parent)
        self.setWindowTitle('自定义分档与颜色')
        self.resize(620, 570)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('按电平由低到高排列；首档下限 -inf，末档上限 inf。\n双击色值单元格可选择颜色；也可直接输入 #RRGGBB。'))
        self.boundary_combo = QComboBox()
        self.boundary_combo.addItems(['左开右闭 (下限, 上限]', '左闭右开 [下限, 上限)'])
        self.boundary_combo.setCurrentIndex(0 if boundary == 'right' else 1)
        layout.addWidget(self.boundary_combo)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['下限', '上限', '颜色 #RRGGBB'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self.pick_color)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        for title, slot in [('拆分选中档', self.split_band), ('合并到相邻档', self.merge_band),
                            ('加载方案', self.load_scheme), ('保存方案', self.save_scheme)]:
            btn = QPushButton(title); btn.clicked.connect(slot); row.addWidget(btn)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.set_rows(colors)

    def set_rows(self, colors):
        self.table.setRowCount(len(colors))
        for i, (lo, hi, color) in enumerate(colors):
            for j, value in enumerate([number(lo), number(hi), color]):
                self.table.setItem(i, j, QTableWidgetItem(value))
            self.table.item(i, 2).setBackground(QColor(color))

    def values(self):
        rows = [[self.table.item(i, j).text().strip() for j in range(3)]
                for i in range(self.table.rowCount())]
        return validate_scheme(rows, 'right' if self.boundary_combo.currentIndex() == 0 else 'left')

    def pick_color(self, row, column):
        if column != 2: return
        color = QColorDialog.getColor(QColor(self.table.item(row, 2).text()), self)
        if color.isValid():
            self.table.item(row, 2).setText(color.name())
            self.table.item(row, 2).setBackground(color)

    def split_band(self):
        try:
            rows = list(self.values())
            if len(rows) >= 20: raise ValueError('最多 20 档')
            i = max(0, self.table.currentRow())
            lo, hi, color = rows[i]
            mid = hi - 5 if math.isinf(lo) else lo + 5 if math.isinf(hi) else (lo + hi) / 2
            rows[i:i+1] = [(lo, mid, color), (mid, hi, color)]
            self.set_rows(rows); self.table.setCurrentCell(i, 1)
        except (ValueError, TypeError) as error:
            QMessageBox.warning(self, '分档校验', str(error))

    def merge_band(self):
        try:
            rows = list(self.values())
            if len(rows) <= 2: raise ValueError('至少保留 2 档')
            i = max(0, self.table.currentRow())
            if i == 0:
                rows[1] = (rows[0][0], rows[1][1], rows[1][2])
            else:
                rows[i-1] = (rows[i-1][0], rows[i][1], rows[i-1][2])
            del rows[i]; self.set_rows(rows)
        except (ValueError, TypeError) as error:
            QMessageBox.warning(self, '分档校验', str(error))

    def accept(self):
        try:
            self.result_colors = self.values()
        except (ValueError, TypeError) as error:
            QMessageBox.warning(self, '分档校验', str(error)); return
        super().accept()

    def save_scheme(self):
        try:
            colors = self.values()
            path, _ = QFileDialog.getSaveFileName(self, '保存配色方案', '配色方案.json', 'JSON (*.json)')
            if not path: return
            data = {'version': 1, 'boundary': colors.boundary,
                    'bands': [[number(lo), number(hi), c] for lo, hi, c in colors]}
            with open(path, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.warning(self, '保存失败', str(error))

    def load_scheme(self):
        path, _ = QFileDialog.getOpenFileName(self, '加载配色方案', '', 'JSON (*.json)')
        if not path: return
        try:
            with open(path, encoding='utf-8') as stream: data = json.load(stream)
            if data.get('version') != 1: raise ValueError('不支持的方案版本')
            colors = validate_scheme(data['bands'], data['boundary'])
            self.set_rows(colors)
            self.boundary_combo.setCurrentIndex(0 if colors.boundary == 'right' else 1)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            QMessageBox.warning(self, '加载失败', str(error))
