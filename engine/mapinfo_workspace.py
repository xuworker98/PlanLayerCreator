# -*- coding: utf-8 -*-
"""Generate a small MapInfo workspace for automatic labels.

Object symbols, pens and brushes live in the TAB table.  Automatic labels are
Map-window state, so a companion WOR is the portable way to retain the chosen
label field and font settings.
"""
from __future__ import annotations

import os

from engine.mapinfo_writer import color_int


def write_label_workspace(tab_path, label_field, color="#000000", size=9,
                          enabled=True, font="Microsoft YaHei"):
    if not label_field:
        return None
    wor_path = os.path.splitext(tab_path)[0] + ".wor"
    alias = "PLC_Layer"
    tab_name = os.path.basename(tab_path).replace('"', '""')
    field = str(label_field).replace('"', '""')
    font = str(font).replace('"', '""')
    rgb = color_int(color, 0)
    auto = "On Visibility On" if enabled else "Off Visibility Off"
    content = (
        "!Workspace\r\n"
        "!Version 1200\r\n"
        "!Charset WindowsSimpChinese\r\n\r\n"
        f'Open Table "{tab_name}" As {alias} Interactive\r\n'
        f"Map From {alias}\r\n"
        f"Set Map Layer 1 Label With {field} Auto {auto} "
        f'Font ("{font}",0,{int(size)},{rgb},16777215)\r\n'
    )
    with open(wor_path, "w", encoding="gbk", newline="") as stream:
        stream.write(content)
    return wor_path
