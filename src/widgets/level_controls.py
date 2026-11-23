"""Shared dynamic color controls for drive tests and MR grids."""
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QComboBox, QColorDialog, QDialog
from PySide6.QtGui import QColor
from utils.constants import LEVEL_COLORS_6, LEVEL_COLORS_9
from utils.level_scheme import LevelColors, interval_label
from widgets.level_editor import LevelEditor


class LevelControls:
    def build_level_controls(self, layout, default_nine=False):
        self._preset_sets = [LEVEL_COLORS_9, LEVEL_COLORS_6] if default_nine else [LEVEL_COLORS_6, LEVEL_COLORS_9]
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(['9档（精细）', '6档（简化）', '自定义'] if default_nine
                                   else ['6档（MR默认）', '9档（精细）', '自定义'])
        layout.addWidget(self.preset_combo)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        self._colors_layout = QHBoxLayout()
        self._colors_layout.setSpacing(3)
        layout.addLayout(self._colors_layout)
        self._color_btns = []
        self._rebuild_colors()
        self.edit_scheme_btn = QPushButton('编辑分档')
        self.edit_scheme_btn.clicked.connect(self.edit_scheme)
        layout.addWidget(self.edit_scheme_btn)
        self.boundary_combo = QComboBox()
        self.boundary_combo.addItems(['(下限, 上限]', '[下限, 上限)'])
        self.boundary_combo.setToolTip('统一控制所有档位的边界归属；首末档向无穷延伸')
        self.boundary_combo.currentIndexChanged.connect(self._boundary_changed)
        layout.addWidget(self.boundary_combo)

    def _boundary_changed(self, index):
        self.style['boundary'] = 'right' if index == 0 else 'left'
        self._rebuild_colors()

    def _mark_custom(self):
        self.style['preset'] = '自定义'
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(2)
        self.preset_combo.blockSignals(False)

    def _pick_color(self, index):
        colors = self.style['level_colors']
        color = QColorDialog.getColor(QColor(colors[index][2]), self, f'配色档位 {index + 1}')
        if color.isValid():
            colors[index][2] = color.name()
            self._mark_custom(); self._rebuild_colors()

    def _rebuild_colors(self):
        while self._colors_layout.count():
            item = self._colors_layout.takeAt(0)
            item.widget().deleteLater()
        self._color_btns = []
        for index, (lo, hi, color) in enumerate(self.style['level_colors']):
            button = QPushButton()
            button.setFixedSize(22, 22)
            button.setStyleSheet(f'background:{color};border:1px solid #89939d;padding:0;')
            button.setToolTip(interval_label(lo, hi, self.style.get('boundary', 'right')))
            button.clicked.connect(lambda checked=False, i=index: self._pick_color(i))
            self._colors_layout.addWidget(button)
            self._color_btns.append(button)

    def on_preset_changed(self, index):
        if index < 2:
            self.style['level_colors'] = [list(row) for row in self._preset_sets[index]]
            self.style['preset'] = f'{len(self.style["level_colors"])}档'
            self._rebuild_colors()
        else:
            self.edit_scheme()

    def edit_scheme(self):
        dialog = LevelEditor(self.style['level_colors'], self.style.get('boundary', 'right'), self)
        if dialog.exec() == QDialog.Accepted:
            colors = dialog.result_colors
            self.style['level_colors'] = [list(row) for row in colors]
            self.style['boundary'] = colors.boundary
            self.boundary_combo.setCurrentIndex(0 if colors.boundary == 'right' else 1)
            self._mark_custom(); self._rebuild_colors()
        else:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex({'9档': 0 if len(self._preset_sets[0]) == 9 else 1,
                '6档': 0 if len(self._preset_sets[0]) == 6 else 1}.get(self.style.get('preset'), 2))
            self.preset_combo.blockSignals(False)

    def get_current_colors(self):
        return LevelColors(self.style['level_colors'], self.style.get('boundary', 'right'))
