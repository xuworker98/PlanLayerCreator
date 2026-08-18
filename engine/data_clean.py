# -*- coding: utf-8 -*-
"""统一数据清洗：度分秒转换、类型强制、空值剔除、统计日志"""
import re

import numpy as np
import pandas as pd


def dms_to_decimal(val):
    """度分秒 → 十进制度

    支持格式：
      108.3718        -> 108.3718（十进制，直接返回）
      108°22'18"      -> 108.3717（度分秒）
      108 22 18       -> 108.3717（空格分隔 度 分 秒）
      108°            -> 108.0（单个数字带度符号）
    """
    if val is None:
        return np.nan
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in ('nan', 'none', 'null', 'na', 'n/a'):
        return np.nan
    # 直接十进制
    try:
        return float(s)
    except ValueError:
        pass
    # 提取所有数字（含负号）
    nums = re.findall(r'-?\d+(?:\.\d+)?', s)
    if not nums:
        return np.nan
    if len(nums) == 1:
        # 单个数字：如 "108.3718" 或 "108°"
        return float(nums[0])
    # 多个数字 = 度 分 秒（可能带 N/S/E/W 方向）
    d = float(nums[0])
    m = float(nums[1]) if len(nums) > 1 else 0.0
    sec = float(nums[2]) if len(nums) > 2 else 0.0
    upper = s.upper()
    sign = -1.0 if (d < 0 or 'W' in upper or 'S' in upper) else 1.0
    return sign * (abs(d) + m / 60.0 + sec / 3600.0)


def clean_numeric(df, col_specs):
    """清洗 DataFrame 的数值列，返回 (清洗后df, 统计信息)

    Args:
        df: 输入 DataFrame
        col_specs: 列规则 dict，如
            {
              '经度': {'kind': 'float', 'lo': -180, 'hi': 180, 'dms': True},
              '方位角': {'kind': 'int', 'lo': 0, 'hi': 360},
            }
        kind: 'float' 或 'int'
        dms: 是否尝试度分秒转换（经纬度 True，其他 False）

    Returns:
        (df_clean, stats)
        stats: list of (列名, 原始行数, 剔除行数, 原因)
    """
    df = df.copy()
    stats = []
    total = len(df)

    # 清洗所有字符串列的控制字符（防 XML 非法字符，如 \x0b、\x1f）
    _CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].map(lambda v: _CTRL.sub('', str(v)) if pd.notna(v) else v)

    for col, spec in col_specs.items():
        if col not in df.columns:
            continue
        kind = spec.get('kind', 'float')
        lo = spec.get('lo')
        hi = spec.get('hi')
        dms = spec.get('dms', False)
        before = len(df)

        # 度分秒转换（仅经纬度）
        if dms:
            df[col] = df[col].apply(dms_to_decimal)
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 类型强制
        if kind == 'int':
            # 先转浮点再四舍五入转 int，非有限值保持 NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].where(df[col].notna(), np.nan)
            df[col] = df[col].round().astype('Int64')  # 可空整数
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 空值剔除
        na_count = int(df[col].isna().sum())
        df = df.dropna(subset=[col])
        if na_count:
            stats.append((col, before, na_count, '空值/非法数值'))

        # 范围检查
        if lo is not None or hi is not None:
            mask = pd.Series(True, index=df.index)
            if lo is not None:
                mask &= (df[col] >= lo)
            if hi is not None:
                mask &= (df[col] <= hi)
            range_count = int((~mask).sum())
            df = df[mask]
            if range_count:
                stats.append((col, before, range_count,
                              f'越界(超出{lo}~{hi})'))

    return df, stats


def format_clean_log(stats, total_rows, final_rows):
    """格式化清洗日志文本"""
    lines = ['[数据清洗日志]',
             f'读取行数: {total_rows}',
             f'最终生成: {final_rows} 行']
    if not stats:
        lines.append('无剔除记录')
    else:
        for col, before, count, reason in stats:
            lines.append(f'- 剔除[{col}] {count} 行（{reason}）')
    return '\n'.join(lines)
