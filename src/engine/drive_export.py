"""Stage route outputs and package a faithful offline screen legend."""
import os
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from utils.constants import LEVEL_COLORS_9
from utils.level_scheme import validate_scheme, interval_label


def render_legend(colors, metric, path, title='路测信号电平'):
    from PySide6.QtGui import QImage, QPainter, QColor, QFont, QFontMetrics
    from PySide6.QtCore import QRect, Qt
    metric = str(metric)
    height = 178 + len(colors) * 52
    image = QImage(600, height, QImage.Format_ARGB32)
    image.fill(QColor('white'))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    def text(rect, value, size, bold=False, color='#172b3a'):
        font = QFont('Microsoft YaHei'); font.setPixelSize(size); font.setBold(bold)
        painter.setFont(font); painter.setPen(QColor(color))
        value = painter.fontMetrics().elidedText(value, Qt.ElideRight, rect.width())
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, value)
    painter.fillRect(QRect(1, 1, 598, 108), QColor('#eef2f5'))
    text(QRect(26, 10, 548, 48), title, 34, True)
    text(QRect(26, 60, 548, 35), metric + ' · dBm', 24)
    # Common signal names fit directly in each interval; long names use x.
    label_metric = metric if len(metric) <= 12 else 'x'
    row_font = QFont('Microsoft YaHei'); row_font.setPixelSize(28)
    metrics = QFontMetrics(row_font)
    if any(metrics.horizontalAdvance(interval_label(lo, hi, colors.boundary, label_metric)) > 456
           for lo, hi, _ in colors):
        label_metric = 'x'
    for i, (lo, hi, color) in enumerate(reversed(colors)):
        y = 126 + 52 * i
        painter.fillRect(QRect(26, y + 6, 72, 30), QColor(color))
        painter.setPen(QColor('#8b949e')); painter.drawRect(26, y + 6, 72, 30)
        text(QRect(118, y, 456, 44), interval_label(lo, hi, colors.boundary, label_metric), 28)
    text(QRect(26, height - 58, 548, 27), 'x = ' + metric if label_metric == 'x' else '单位：dBm', 22, color='#465662')
    mode = '左闭右开 [下限, 上限)' if colors.boundary == 'left' else '左开右闭 (下限, 上限]'
    text(QRect(26, height - 30, 548, 25), f'{len(colors)} 档 · {mode}', 22, color='#465662')
    painter.setPen(QColor('#8b949e')); painter.drawRect(0, 0, 599, height - 1)
    painter.end()
    if not image.save(str(path), 'PNG'):
        raise OSError(f'图例图片保存失败：{path}')


def render_point(path, color='#FFFFFF', options=None):
    from PySide6.QtGui import QImage,QPainter,QColor,QPen
    from PySide6.QtCore import Qt,QRectF
    options=options or {}
    image=QImage(32,32,QImage.Format_ARGB32);image.fill(Qt.transparent)
    painter=QPainter(image);painter.setRenderHint(QPainter.Antialiasing)
    fill=QColor(color);fill.setAlpha(round(255*(1-float(options.get('transparency',20))/100)))
    painter.setBrush(fill if options.get('fill_enabled',True) else Qt.NoBrush)
    if options.get('outline_enabled',True):
        pen=QPen(QColor(options.get('border_color','#000000')))
        pen.setWidthF(float(options.get('border_width',1)));painter.setPen(pen)
    else:painter.setPen(Qt.NoPen)
    painter.drawEllipse(QRectF(5,5,22,22));painter.end()
    if not image.save(str(path),'PNG'):raise OSError('点符号图片保存失败。')


def overlay_xml(href, count, width=360):
    # Coordinates in pixels from the bottom-left of the screen.
    if width not in (300, 360, 420):
        raise ValueError('图例宽度必须为 300、360 或 420 像素')
    height = round((178 + count * 52) * width / 600)
    return (
        '<ScreenOverlay><name>路测图例</name><visibility>1</visibility>'
        f'<Icon><href>{escape(href)}</href></Icon>'
        '<overlayXY x="0" y="0" xunits="fraction" yunits="fraction"/>'
        '<screenXY x="16" y="16" xunits="pixels" yunits="pixels"/>'
        f'<size x="{width}" y="{height}" xunits="pixels" yunits="pixels"/>'
        '</ScreenOverlay>'
    )


def export_drive(implementation, df, mapping, style, output_path, do_correct, extra, progress_cb):
    from engine.legend_export import export_with_legend
    return export_with_legend(implementation,df,mapping,style,output_path,do_correct,extra,progress_cb,point=True)
