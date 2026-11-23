"""Use Windows' Chinese UI font, including headless export verification."""
import os
from pathlib import Path


def configure_fonts(app):
    from PySide6.QtGui import QFont, QFontDatabase
    if not QFontDatabase.families():
        font = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts' / 'msyh.ttc'
        if font.is_file(): QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont('Microsoft YaHei UI', 9))
