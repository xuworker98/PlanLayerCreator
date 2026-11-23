"""Shared visible styling options for grid fills and route markers."""
from PySide6.QtWidgets import QHBoxLayout,QLabel,QCheckBox,QDoubleSpinBox,QSpinBox,QPushButton,QColorDialog
from PySide6.QtGui import QColor

def add_style_controls(tab, layout, point=False):
    row=QHBoxLayout();row.setSpacing(10);row.setContentsMargins(0,0,0,0)
    tab.no_fill_check=QCheckBox('无填充');tab.no_outline_check=QCheckBox('无边框')
    row.addWidget(tab.no_fill_check);row.addWidget(tab.no_outline_check)
    row.addWidget(QLabel('边框宽度：'))
    tab.outline_width_spin=QDoubleSpinBox();tab.outline_width_spin.setRange(0.1,10);tab.outline_width_spin.setValue(1);tab.outline_width_spin.setSuffix(' px');row.addWidget(tab.outline_width_spin)
    row.addWidget(QLabel('边框颜色：'))
    tab.outline_color='#000000';tab.outline_color_btn=QPushButton();tab.outline_color_btn.setFixedSize(34,22)
    def show_color():tab.outline_color_btn.setStyleSheet(f'background:{tab.outline_color};border:1px solid #bcc8d2;border-radius:4px;')
    def pick():
        color=QColorDialog.getColor(QColor(tab.outline_color),tab,'边框颜色')
        if color.isValid():tab.outline_color=color.name();show_color()
    show_color();tab.outline_color_btn.clicked.connect(pick);row.addWidget(tab.outline_color_btn)
    row.addWidget(QLabel('填充透明度：'))
    tab.transparency_spin=QSpinBox();tab.transparency_spin.setRange(0,100);tab.transparency_spin.setValue(20);tab.transparency_spin.setSuffix(' %');row.addWidget(tab.transparency_spin)
    row.addStretch();layout.addLayout(row)
    def refresh(*args):
        fmt=tab.format_combo.currentText();alpha=fmt.startswith(('KML','KMZ','SHP'))
        tab.transparency_spin.setEnabled(alpha and not tab.no_fill_check.isChecked())
        tab.transparency_spin.setToolTip('0% 不透明，100% 完全透明。' if alpha else '此格式原生对象不保存百分比透明度。')
        outline_capable=not point or alpha
        for control in (tab.no_fill_check,tab.no_outline_check):
            control.setEnabled(outline_capable)
            control.setToolTip('' if outline_capable else '此格式点符号保留原生配色和大小；独立轮廓及空心样式可用 KML/KMZ/SHP。')
        for control in (tab.outline_width_spin,tab.outline_color_btn):control.setEnabled(outline_capable and not tab.no_outline_check.isChecked())
    tab._refresh_style_options=refresh
    tab.no_fill_check.toggled.connect(refresh);tab.no_outline_check.toggled.connect(refresh)

def style_options(tab):
    return {'fill_enabled':not tab.no_fill_check.isChecked(),'outline_enabled':not tab.no_outline_check.isChecked(),
            'border_width':tab.outline_width_spin.value(),'border_color':tab.outline_color,
            'transparency':tab.transparency_spin.value()}
