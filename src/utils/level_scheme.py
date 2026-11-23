"""One interval definition shared by UI, legend and all export formats."""
import math
import re


class LevelColors(list):
    def __init__(self, rows, boundary='right'):
        super().__init__(tuple(row) for row in rows)
        if boundary not in ('right', 'left'):
            raise ValueError('未知区间边界模式')
        self.boundary = boundary


def contains(values, low, high, colors):
    if getattr(colors, 'boundary', 'right') == 'left':
        return (values >= low) & (values < high)
    return (values > low) & (values <= high)


def validate_scheme(rows, boundary='right'):
    if not 2 <= len(rows) <= 20:
        raise ValueError('分档数量必须为 2～20 档')
    result = []
    for index, (low, high, color) in enumerate(rows):
        low, high = float(low), float(high)
        if math.isnan(low) or math.isnan(high) or low >= high:
            raise ValueError(f'第 {index + 1} 档下限必须小于上限')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', str(color)):
            raise ValueError(f'第 {index + 1} 档颜色必须为 #RRGGBB')
        if result and low != result[-1][1]:
            raise ValueError(f'第 {index + 1} 档与上一档必须连续，不能重叠或留空')
        result.append((low, high, color.upper()))
    if result[0][0] != -math.inf or result[-1][1] != math.inf:
        raise ValueError('首档下限必须为 -inf，末档上限必须为 inf')
    return LevelColors(result, boundary)


def number(value):
    return f'{value:g}'


def interval_label(low, high, boundary='right', metric='RSRP'):
    left, right = ('≤', '<') if boundary == 'left' else ('<', '≤')
    if low == -math.inf:
        return f'{metric} {right} {number(high)}'
    if high == math.inf:
        return f'{metric} {"≥" if boundary == "left" else ">"} {number(low)}'
    return f'{number(low)} {left} {metric} {right} {number(high)}'
