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

            if self.layer_type == 'site':
                count = generate_site_layer(self.df, self.mapping, self.style,
                                            self.output_path, self.do_correct,
                                            progress_cb=self._report)
            elif self.layer_type == 'sector':
                count = generate_sector_layer(self.df, self.mapping, self.style,
                                              self.output_path, self.do_correct, self.extra)
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
                                           self.output_path, self.do_correct, self.extra)
            else:
                self.error.emit(f"未知图层类型: {self.layer_type}")
                return

            self._report(100, f"生成完成！共 {count} 个要素")
            self.finished.emit(f"生成完成！共 {count} 个要素 → {self.output_path}")
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")
            self._report(0, f"生成失败: {e}")
