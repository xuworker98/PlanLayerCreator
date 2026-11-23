"""Collect conclusions for one export without writing intermediate logs."""
from contextvars import ContextVar
RESULT = ContextVar('export_result', default=None)

def note(message):
    result = RESULT.get()
    if result is not None and message not in result['notes']:
        result['notes'].append(message)

def record_cleaning(stats, input_rows, output_rows):
    result = RESULT.get()
    if result is None:
        return
    removed = sum(int(row[2]) for row in stats)
    if removed:
        note(f'已剔除 {removed} 条无效记录。')
    if output_rows < input_rows - removed:
        note(f'有效样本按栅格聚合或按最少样本数筛选后，输出 {output_rows} 个栅格。')
