"""Background export: generate privately, validate, publish, summarize once."""
from PySide6.QtCore import QThread, Signal
import os
import time
from pathlib import Path


def available_output(path):
    path = Path(path).absolute()
    def occupied(candidate):
        suffix = candidate.suffix.lower()
        parts = {'.tab': ('.tab','.dat','.map','.id','.ind','.wor'),
                 '.shp': ('.shp','.shx','.dbf','.prj','.cpg','.qml'),
                 '.mif': ('.mif','.mid')}.get(suffix, (suffix,))
        if any(candidate.with_suffix(ext).exists() for ext in parts):
            return True
        tag = '_kml_' if suffix == '.kml' else '_kmz_' if suffix == '.kmz' else None
        return bool(tag and list(candidate.parent.glob(candidate.stem + tag + '*.png')))
    candidate = path
    i = 2
    while occupied(candidate):
        candidate = path.with_name(f'{path.stem}_{i}{path.suffix}')
        i += 1
    return candidate


class GenerateWorker(QThread):
    progress = Signal(int, str)
    log = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, layer_type, df, mapping, style, output_path, do_correct=False, extra=None):
        super().__init__()
        self.layer_type, self.df, self.mapping = layer_type, df, dict(mapping)
        self.style, self.extra = dict(style), dict(extra or {})
        self.output_path, self.do_correct = output_path, do_correct
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.requestInterruption()

    def _report(self, pct, msg):
        if not self._cancelled:
            self.progress.emit(min(pct, 99), msg)

    def run(self):
        from engine.result_log import RESULT, note
        from engine.gdal_runtime import TAB_BACKEND, ACTUAL_TAB_BACKEND
        started = time.monotonic()
        token = RESULT.set({'notes': []})
        backend_token = TAB_BACKEND.set('gdal')
        actual_token = ACTUAL_TAB_BACKEND.set(None)
        count, problem, state = 0, '', '失败'
        try:
            from engine.layer_engine import (generate_site_layer, generate_sector_layer,
                generate_drive_layer, generate_grid_layer, generate_wkt_layer)
            import tempfile
            target = available_output(self.output_path)
            if str(target) != str(Path(self.output_path).absolute()):
                note('同名成果已保留，本次自动另存为新名称。')
            self.output_path = str(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            self._report(1, f'共 {len(self.df):,} 行，正在生成图层…')
            with tempfile.TemporaryDirectory(prefix='.plc_export_', dir=target.parent) as folder:
                staged = Path(folder) / target.name
                args = (self.df, self.mapping, self.style, str(staged), self.do_correct)
                generators = {'site':generate_site_layer, 'sector':generate_sector_layer,
                    'drive':generate_drive_layer,'grid':generate_grid_layer,
                    'line':generate_wkt_layer,'polygon':generate_wkt_layer}
                if self.layer_type not in generators:
                    raise ValueError('不支持的图层类型。')
                kwargs = {'progress_cb':self._report}
                if self.layer_type != 'site':
                    kwargs['extra'] = self.extra
                count = generators[self.layer_type](*args, **kwargs)
                if self._cancelled:
                    state = '已取消'
                    return
                if not count or not staged.is_file():
                    raise RuntimeError('没有生成有效图层，请检查输入及字段映射。')
                if staged.suffix.lower() in ('.tab','.shp','.mif'):
                    import pyogrio
                    actual_count=int(pyogrio.read_info(str(staged))['features'])
                    if actual_count < 0:
                        actual_count=int(pyogrio.read_info(str(staged), force_feature_count=True)['features'])
                    if actual_count < 0:
                        raise RuntimeError('无法取得输出要素数量，未发布成果。')
                    if actual_count != int(count):
                        raise RuntimeError(f'输出数量核验失败：预期 {count}，实际 {actual_count}。')
                # Windows rename is exclusive. Publish the document last.
                files = sorted((f for f in Path(folder).iterdir() if f.is_file()), key=lambda f:f == staged)
                published = []
                try:
                    for source in files:
                        destination = target.parent / source.name
                        os.rename(source, destination)
                        published.append((source, destination))
                except OSError:
                    for source, destination in reversed(published):
                        os.rename(destination, source)
                    raise
            state = '成功'
        except Exception as exc:
            problem = str(exc).strip().split('\n')[0] or type(exc).__name__
        finally:
            seconds = time.monotonic() - started
            log_path = self._write_result(state, count, seconds, problem, RESULT.get()['notes'])
            RESULT.reset(token)
            TAB_BACKEND.reset(backend_token)
            ACTUAL_TAB_BACKEND.reset(actual_token)
            if state == '成功':
                self.progress.emit(100, '生成完成')
                self.finished.emit(f'生成完成：{count:,} 个要素，{seconds:.1f} 秒 → {self.output_path}')
            elif state == '失败':
                self.error.emit(f'{problem}。结果日志：{log_path}')
            else:
                self.finished.emit('已取消，未发布图层。')

    def _write_result(self, state, count, seconds, problem, notes):
        path = Path(self.output_path).with_name(Path(self.output_path).stem + '_结果日志.txt')
        lines = [f'【{time.strftime("%Y-%m-%d %H:%M:%S")}｜PlanLayerCreator V2.0｜{state}】',
                 f'输入：{self.style.get("_input_file", "内存数据")}；{len(self.df):,} 行',
                 f'工作表：{self.style.get("_input_sheet") or "默认"}',
                 f'输出：{self.output_path}；{count if state == "成功" else 0:,} 个要素',
                 f'坐标：{"GCJ-02 → WGS84" if self.do_correct else "保持输入坐标"}；耗时：{seconds:.1f} 秒',
                 '问题：' + ('；'.join(notes + ([problem] if problem else [])) or '无')]
        if state == '失败':
            lines.append('建议：检查字段和数据、目录权限、磁盘空间及文件占用；排除后重新生成。')
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'a', encoding='utf-8') as stream:
                stream.write('\n'.join(lines) + '\n\n')
        except OSError:
            return '无法保存日志，请检查目录写入权限。'
        return str(path)
