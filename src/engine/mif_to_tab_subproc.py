# -*- coding: utf-8 -*-
"""
MIF→TAB 子进程转换器（独立进程，不卡主线程）
用法: python mif_to_tab_subproc.py <mif_path>
"""
import sys, os, time


def run_conversion(mif_path):
    """在独立进程中执行 MapInfo COM 转换，返回进程退出码。"""
    mi = None
    try:
        import win32com.client
        mi = win32com.client.DispatchEx("MapInfo.Application")
        mi.Do(f'Import "{os.path.abspath(mif_path)}" Type "MIF"')
        mi.Do('Close All')
        base = os.path.splitext(mif_path)[0]
        return 0 if all(os.path.isfile(base + ext) for ext in ('.tab', '.dat', '.map', '.id')) else 2
    except Exception:
        return 3
    finally:
        if mi is not None:
            try:
                mi.Do('End MapInfo')
            except Exception:
                pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(1)
    sys.exit(run_conversion(sys.argv[1]))
