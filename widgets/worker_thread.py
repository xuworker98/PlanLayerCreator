# -*- coding: utf-8 -*-
"""后台工作线程 — 带进度报告"""
from PySide6.QtCore import QThread, Signal


class GenerateWorker(QThread):
    progress = Signal(int, str)
    log = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, layer_type, df, mapping, style, output_path, do_correct=False, extra=None):
        super().__init__()
        self.layer_type = layer_type
        self.df = df
        self.mapping = mapping
        self.style = style
        self.output_path = output_path
        self.do_correct = do_correct
        self.extra = extra
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        self.requestInterruption()

    def _report(self, pct, msg):
        """报告进度（线程安全）"""
        if not self._cancelled:
            self.progress.emit(pct, msg)

    def run(self):
        try:
            from engine.layer_engine import (
                generate_site_layer, generate_sector_layer,
                generate_drive_layer, generate_grid_layer,
                generate_wkt_layer,
            )
            if self._cancelled:
                return

            self._report(0, "开始生成图层...")
            # 确保输出目录存在
            import os
            out_dir = os.path.dirname(self.output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)

            # 预估时间（粗估，提醒用户耐心等待）
            n_rows = len(self.df) if self.df is not None else 0
            if n_rows > 0:
                if self.layer_type in ('drive', 'grid'):
                    est_sec = max(2, n_rows // 20000)
                else:
                    est_sec = max(2, n_rows // 500)
                if est_sec >= 60:
                    est_txt = f"约 {est_sec // 60} 分钟"
                else:
                    est_txt = f"约 {est_sec} 秒"
                self._report(1, f"共 {n_rows} 行，预计 {est_txt}，请耐心等待，不要关闭程序")

            if self.layer_type == 'site':
                count = generate_site_layer(self.df, self.mapping, self.style,
                                            self.output_path, self.do_correct,
                                            progress_cb=self._report)
            elif self.layer_type == 'sector':
                count = generate_sector_layer(self.df, self.mapping, self.style,
                                              self.output_path, self.do_correct, self.extra,
                                              progress_cb=self._report)
            elif self.layer_type == 'drive':
                count = generate_drive_layer(self.df, self.mapping, self.style,
                                             self.output_path, self.do_correct,
                                             self.extra, progress_cb=self._report)
            elif self.layer_type == 'grid':
                count = generate_grid_layer(self.df, self.mapping, self.style,
                                            self.output_path, self.do_correct,
                                            self.extra, progress_cb=self._report)
            elif self.layer_type in ('line', 'polygon'):
                count = generate_wkt_layer(self.df, self.mapping, self.style,
                                           self.output_path, self.do_correct, self.extra,
                                           progress_cb=self._report)
            else:
                self.error.emit(f"未知图层类型: {self.layer_type}")
                return

            self._report(100, f"生成完成！共 {count} 个要素")
            self.finished.emit(f"生成完成！共 {count} 个要素 → {self.output_path}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.error.emit(f"{e}\n{tb}")
            self._report(0, f"生成失败: {e}")
            self._write_error_log(e, tb)

    def _write_error_log(self, e, tb):
        """生成异常时，写详细错误日志到输出目录（错误日志.txt）"""
        try:
            import os
            import time
            out_dir = os.path.dirname(os.path.abspath(self.output_path))
            if not out_dir:
                out_dir = os.getcwd()
            log_path = os.path.join(out_dir, '错误日志.txt')
            lines = [
                "",
                "=" * 60,
                "生成错误日志",
                "=" * 60,
                f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"图层类型: {self.layer_type}",
                f"输出文件: {self.output_path}",
                f"输入行数: {len(self.df) if self.df is not None else 0}",
                "",
                f"错误信息: {e}",
                "",
                "详细堆栈:",
                tb,
            ]
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        except Exception:
            pass
