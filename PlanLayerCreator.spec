# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_delvewheel_libs_directory,
)

project_dir = Path(SPECPATH)
datas = collect_data_files('pyogrio', include_py_files=False)
# Wheel source files are not runtime data. pyproj's standard hook already
# collects its PROJ database, so do not duplicate the package tree here.
datas = [entry for entry in datas if not entry[0].lower().endswith(
    ('.c', '.h', '.pxd', '.pyx')
)]
binaries = []
datas, binaries = collect_delvewheel_libs_directory(
    'pyogrio', datas=datas, binaries=binaries
)

hiddenimports = [
    'openpyxl', 'xlrd', 'pyogrio', 'pyogrio.raw',
    'pyogrio._io', 'pyogrio._ogr', 'pyogrio._err',
    'pyogrio._geometry', 'pyogrio._vsi',
    'pythoncom', 'pywintypes', 'win32com.client',
]

a = Analysis(
    [str(project_dir / 'main.py')],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['osgeo', 'GDAL', 'fiona', 'geopandas', 'matplotlib', 'scipy',
              'PyQt5', 'PyQt6', 'pypinyin', 'PySide6.QtNetwork',
              'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf',
              'PySide6.QtOpenGL'],
    noarchive=False,
    optimize=1,
)

# The UI uses QtCore/QtGui/QtWidgets only. These optional modules are large
# and were pulled in by the generic PySide6 hook despite not being imported.
_unused_binary_names = {
    'pyside6\\qt6quick.dll', 'pyside6\\qt6qml.dll',
    'pyside6\\qt6pdf.dll', 'pyside6\\qt6opengl.dll',
    'pyside6\\qt6network.dll', 'pyside6\\opengl32sw.dll',
    'pyside6\\qtpdf.pyd', 'pyside6\\qtqml.pyd',
    'pyside6\\qtquick.pyd', 'pyside6\\qtopengl.pyd',
    'pyside6\\qtnetwork.pyd', 'pythonwin\\mfc140u.dll',
}
a.binaries = [
    entry for entry in a.binaries
    if entry[0].replace('/', '\\').lower() not in _unused_binary_names
    and not entry[0].replace('/', '\\').lower().startswith('pythonwin\\')
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PlanLayerCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_dir / 'res' / 'icon.ico'),
    version=str(project_dir / 'build_support' / 'version_info.txt'),
)
