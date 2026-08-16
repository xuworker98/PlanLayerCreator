# -*- coding: utf-8 -*-
"""
MIF→TAB 子进程转换器（独立进程，不卡主线程）
用法: python mif_to_tab_subproc.py <mif_path>
"""
import sys, os, time


def run_conversion(mif_path):
    """在独立进程中执行 MapInfo COM 转换，返回进程退出码。"""
    try:
        import win32com.client
        mi = win32com.client.Dispatch("MapInfo.Application")
        time.sleep(1)
        mi.Do(f'Import "{os.path.abspath(mif_path)}" Type "MIF"')
        # 等全部文件出现（最多 300s）
        map_path = mif_path.replace('.mif', '.map').replace('.MIF', '.map')
        tab_path = mif_path.replace('.mif', '.tab').replace('.MIF', '.tab')
        for _ in range(150):
            time.sleep(2)
            if os.path.exists(map_path) and os.path.exists(tab_path):
                # 确认文件大小不再增长
                s1 = os.path.getsize(map_path)
                time.sleep(1)
                if os.path.getsize(map_path) == s1:
                    break
        mi.Do('End MapInfo')
        time.sleep(0.5)
        # 返回状态
        tab_path = mif_path.replace('.mif', '.tab')
        if os.path.exists(tab_path):
            return 0
        else:
            return 2
    except Exception:
        return 3


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(1)
    sys.exit(run_conversion(sys.argv[1]))
