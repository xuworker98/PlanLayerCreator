# -*- coding: utf-8 -*-
"""Use the GDAL runtime bundled by pyogrio without importing ``osgeo``.

The project deliberately avoids the Python GDAL bindings because their
PyInstaller hooks were the original one-file build blocker.  pyogrio ships a
matching GDAL DLL; calling GDALVectorTranslate through the stable C API keeps
the runtime small and also preserves MapInfo feature styles.
"""
from __future__ import annotations

from contextvars import ContextVar
TAB_BACKEND = ContextVar("planlayer_tab_backend", default=None)
ACTUAL_TAB_BACKEND = ContextVar("planlayer_actual_tab_backend", default=None)

import ctypes
import glob
import os
import shutil
import tempfile
from pathlib import Path


GDAL_OF_VECTOR = 0x04
_GDAL = None
_DLL_HANDLES = []


def _load_gdal():
    global _GDAL
    if _GDAL is not None:
        return _GDAL

    import pyogrio  # Import first so delvewheel loads dependent DLLs.

    package_dir = Path(pyogrio.__file__).resolve().parent
    candidates = [package_dir.parent / "pyogrio.libs"]
    bundle_root = getattr(__import__("sys"), "_MEIPASS", None)
    if bundle_root:
        candidates.extend([
            Path(bundle_root) / "pyogrio.libs",
            Path(bundle_root) / "pyogrio" / "pyogrio.libs",
        ])

    gdal_path = None
    for directory in candidates:
        if not directory.is_dir():
            continue
        if hasattr(os, "add_dll_directory"):
            _DLL_HANDLES.append(os.add_dll_directory(str(directory)))
        matches = glob.glob(str(directory / "gdal-*.dll"))
        if matches:
            gdal_path = matches[0]
            break
    if not gdal_path:
        raise RuntimeError("找不到程序内置的 GDAL 运行库")

    dll = ctypes.CDLL(gdal_path)
    dll.GDALAllRegister.argtypes = []
    dll.GDALAllRegister.restype = None
    dll.GDALOpenEx.argtypes = [
        ctypes.c_char_p, ctypes.c_uint,
        ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_char_p),
    ]
    dll.GDALOpenEx.restype = ctypes.c_void_p
    dll.GDALVectorTranslateOptionsNew.argtypes = [
        ctypes.POINTER(ctypes.c_char_p), ctypes.c_void_p,
    ]
    dll.GDALVectorTranslateOptionsNew.restype = ctypes.c_void_p
    dll.GDALVectorTranslateOptionsFree.argtypes = [ctypes.c_void_p]
    dll.GDALVectorTranslateOptionsFree.restype = None
    dll.GDALVectorTranslate.argtypes = [
        ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int,
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    dll.GDALVectorTranslate.restype = ctypes.c_void_p
    dll.GDALClose.argtypes = [ctypes.c_void_p]
    dll.GDALClose.restype = None
    if hasattr(dll, "CPLSetConfigOption"):
        dll.CPLSetConfigOption.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        dll.CPLSetConfigOption(b"GDAL_FILENAME_IS_UTF8", b"YES")
    dll.GDALAllRegister()
    _GDAL = dll
    return dll


def vector_translate(source: str, destination: str, arguments: list[str]) -> None:
    """Run GDALVectorTranslate and raise a useful error on failure."""
    dll = _load_gdal()
    source_b = os.fspath(source).encode("utf-8")
    destination_b = os.fspath(destination).encode("utf-8")
    src = dll.GDALOpenEx(source_b, GDAL_OF_VECTOR, None, None, None)
    if not src:
        raise RuntimeError(f"GDAL 无法打开源文件: {source}")

    argv = (ctypes.c_char_p * (len(arguments) + 1))(
        *[item.encode("utf-8") for item in arguments], None
    )
    options = dll.GDALVectorTranslateOptionsNew(argv, None)
    if not options:
        dll.GDALClose(src)
        raise RuntimeError("GDAL 转换参数初始化失败")

    src_array = (ctypes.c_void_p * 1)(src)
    usage_error = ctypes.c_int(0)
    dst = None
    messages = []
    Handler = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_int, ctypes.c_char_p)
    def capture(level, number, message):
        if level >= 3 and message:
            messages.append(message.decode('utf-8', errors='replace'))
    handler = Handler(capture)
    dll.CPLPushErrorHandler.argtypes = [Handler]
    dll.CPLPopErrorHandler.argtypes = []
    dll.CPLPushErrorHandler(handler)
    try:
        dst = dll.GDALVectorTranslate(
            destination_b, None, 1, src_array, options,
            ctypes.byref(usage_error),
        )
        if not dst or usage_error.value:
            raise RuntimeError(
                '无法生成 TAB：' + ('；'.join(messages) or '请检查输出目录权限、磁盘空间及文件占用。')
            )
    finally:
        dll.CPLPopErrorHandler()
        if dst:
            dll.GDALClose(dst)
        dll.GDALVectorTranslateOptionsFree(options)
        dll.GDALClose(src)


def mif_to_tab(mif_path: str, tab_path: str, encoding: str = "CP936") -> None:
    """Convert a UTF-8 MIF/MID pair to a styled native MapInfo TAB set."""
    vector_translate(
        mif_path,
        tab_path,
        [
            "-f", "MapInfo File",
            "-dsco", "FORMAT=TAB",
            "-dsco", "STRICT_FIELDS_NAME_LAUNDERING=NO",
            "-lco", f"ENCODING={encoding}",
            "-lco", "STRICT_FIELDS_NAME_LAUNDERING=NO",
            "-overwrite",
        ],
    )


def _legacy_cp936_pair(gbk_mif: str, target_mif: str) -> None:
    """Prepare the GBK MIF/MID pair for legacy MapInfo import (Version 300)."""
    with open(gbk_mif, "r", encoding="gbk") as source:
        header_and_geometry = source.read()
    header_and_geometry = header_and_geometry.replace("Version 1520", "Version 300", 1)
    with open(target_mif, "w", encoding="gbk", newline="") as target:
        target.write(header_and_geometry)

    source_mid = os.path.splitext(gbk_mif)[0] + ".mid"
    target_mid = os.path.splitext(target_mif)[0] + ".mid"
    with open(source_mid, "r", encoding="gbk", newline="") as source:
        mid_text = source.read()
    with open(target_mid, "w", encoding="gbk", newline="") as target:
        target.write(mid_text)


def mif_to_tab_compatible(mif_path: str, tab_path: str, encoding: str = "CP936",
                          progress_cb=None) -> str:
    """Prefer installed MapInfo for legacy compatibility, else bundled GDAL.

    Returns ``"mapinfo"`` or ``"gdal"`` so diagnostics can report which
    backend created the table.
    """
    target = Path(tab_path).absolute()
    extensions = ('.tab', '.dat', '.map', '.id', '.ind')
    if any(target.with_suffix(ext).exists() for ext in extensions):
        raise FileExistsError('同名 TAB 文件已存在，请另存新名称。')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='plc_tab_', dir=target.parent) as folder:
        staged = Path(folder) / target.name
        if progress_cb:
            progress_cb(89, '正在生成 TAB 图层…')
        mif_to_tab(mif_path, str(staged), encoding=encoding)
        import pyogrio
        info = pyogrio.read_info(str(staged))
        if int(info['features']) <= 0:
            raise RuntimeError('TAB 输出为空，请检查输入数据。')
        if not all(staged.with_suffix(ext).is_file() for ext in extensions[:4]):
            raise RuntimeError('TAB 文件组不完整，未发布成果。')
        # Publish only validated new files. Existing outputs are never modified.
        for ext in extensions:
            source = staged.with_suffix(ext)
            if source.exists():
                with open(source, 'rb') as src, open(target.with_suffix(ext), 'xb') as dst:
                    shutil.copyfileobj(src, dst)
    ACTUAL_TAB_BACKEND.set('gdal')
    return 'gdal'


def first_feature_style(dataset_path: str) -> str:
    """Return the first feature's OGR style string (used by regression tests)."""
    dll = _load_gdal()
    dll.GDALDatasetGetLayer.argtypes = [ctypes.c_void_p, ctypes.c_int]
    dll.GDALDatasetGetLayer.restype = ctypes.c_void_p
    dll.OGR_L_GetNextFeature.argtypes = [ctypes.c_void_p]
    dll.OGR_L_GetNextFeature.restype = ctypes.c_void_p
    dll.OGR_F_GetStyleString.argtypes = [ctypes.c_void_p]
    dll.OGR_F_GetStyleString.restype = ctypes.c_char_p
    dll.OGR_F_Destroy.argtypes = [ctypes.c_void_p]
    dll.OGR_F_Destroy.restype = None
    dataset = dll.GDALOpenEx(os.fspath(dataset_path).encode("utf-8"), GDAL_OF_VECTOR, None, None, None)
    if not dataset:
        return ""
    feature = None
    try:
        layer = dll.GDALDatasetGetLayer(dataset, 0)
        feature = dll.OGR_L_GetNextFeature(layer) if layer else None
        value = dll.OGR_F_GetStyleString(feature) if feature else None
        return value.decode("utf-8", errors="replace") if value else ""
    finally:
        if feature:
            dll.OGR_F_Destroy(feature)
        dll.GDALClose(dataset)
