# -*- coding: utf-8 -*-
"""
MapInfo COM 自动转换器：检测 → MIF→TAB 静默转换
"""
import os
import sys
import time


def detect_mapinfo():
    """检测 MapInfo 是否安装，返回可执行路径"""
    paths = [
        os.path.expandvars(r'%ProgramFiles(x86)%\MapInfo2012\Professional\MapInfow.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\MapInfo\Professional\MapInfow.exe'),
        os.path.expandvars(r'%ProgramFiles%\MapInfo\Professional\MapInfow.exe'),
        os.path.expandvars(r'%ProgramFiles%\MapInfo2017\MapInfow.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\MapInfo2017\MapInfow.exe'),
        os.path.expandvars(r'%ProgramFiles%\MapInfo2023\MapInfow.exe'),
        r'C:\Program Files (x86)\MapInfo\Professional\MapInfow.exe',
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE,):
            try:
                key = winreg.OpenKey(root, r'SOFTWARE\Wow6432Node\MapInfo\MapInfo\Professional')
                val, _ = winreg.QueryValueEx(key, 'ProgramDirectory')
                winreg.CloseKey(key)
                exe = os.path.join(val, 'MapInfow.exe')
                if os.path.exists(exe):
                    return exe
            except Exception:
                pass
    except Exception:
        pass
    return None


def build_subprocess_command(mif_path):
    """源码环境调用脚本；onefile 环境让当前 EXE 进入隐藏转换模式。"""
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--mif-to-tab', mif_path]
    script = os.path.join(os.path.dirname(__file__), 'mif_to_tab_subproc.py')
    return [sys.executable, script, mif_path]


def mif_to_tab_com(mif_path, progress_cb=None):
    """使用子进程 MapInfo COM 将 MIF 转为 TAB"""
    tab_path = mif_path.replace('.mif', '.tab').replace('.MIF', '.tab')

    # 删旧 TAB 文件
    for ext in ['.tab', '.map', '.dat', '.id', '.ind']:
        p = mif_path.replace('.mif', ext).replace('.MIF', ext)
        if p != mif_path and os.path.exists(p):
            try: os.remove(p)
            except: pass

    import subprocess
    try:
        proc = subprocess.Popen(
            build_subprocess_command(mif_path),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        proc.communicate(timeout=300)
        if proc.returncode == 0:
            return os.path.exists(tab_path)
        else:
            return False
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        print('[COM subprocess] Timeout')
        return False
    except Exception as e:
        print(f'[COM subprocess] {e}')
        return False
