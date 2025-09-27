import sys
import os
import time
import pickle
import random

from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QMimeData, QByteArray, QPoint
)
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout,
    QTabWidget, QProgressBar, QHBoxLayout, QPushButton, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QTabBar
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class VideoAnalysisWorker(QThread):
    """后台分析线程（模拟），发送进度和完成信号。"""
    progress_update = pyqtSignal(int)        # emit int 0..100
    finished = pyqtSignal(object)           # emit dict {'path':..., 'data':...}

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        # 这里用模拟的耗时任务；把实际视频分析逻辑放在这里
        try:
            data = []
            for i in range(101):
                if not self._running:
                    return
                time.sleep(0.03)                # 模拟开销
                # 模拟产生的 (distance, speed) 数据
                data.append((i, float(60 + 40 * random.random())))
                self.progress_update.emit(i)
            if self._running:
                self.finished.emit({'path': self.video_path, 'data': data})
        except Exception as e:
            # 不要让异常在线程里导致进程崩溃
            print("Worker exception:", e)

# --------------------- 分析任务 Tab ---------------------
class VideoAnalysisBar(QWidget):
    """每个分析任务的 tab 内容。包含标签、进度条，可拖拽（完成后）"""
    finished_signal = pyqtSignal(object)  # emit self when finished

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.result_data = None
        self.worker = None

        layout = QVBoxLayout(self)
        self.label = QLabel(f"分析中: {os.path.basename(video_path)}")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # 一个小提示，只有完成后显示，提示可以拖拽到绘图界面
        self.hint = QLabel("分析完成后可直接拖拽此 tab 到绘图界面")
        self.hint.setVisible(False)
        layout.addWidget(self.hint)

        layout.addStretch()

        self.start_worker()
        

    def start_worker(self):
        self.worker = VideoAnalysisWorker(self.video_path)
        self.worker.progress_update.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self, payload):
        # payload: {'path':..., 'data':...}
        self.result_data = payload['data']
        self.label.setText(f"完成: {os.path.basename(self.video_path)}")
        self.hint.setVisible(True)
        # emit to container to let它更新 tab title（container 会处理 index）
        self.finished_signal.emit(self)

    def close(self):
        # 安全停止 worker（如果仍在运行）
        try:
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait(2000)
        except Exception:
            pass
        super().close()

# --------------------- 视频分析容器（首页） ---------------------
class VideoAnalysisTab(QWidget):
    """首页的容器：顶部是拖放区，下面是内层 task tab 控件"""
    def __init__(self, parent_tabs: QTabWidget, parent=None):
        super().__init__(parent)
        self.parent_tabs = parent_tabs
        self.qvbox = QVBoxLayout(self)
        self.video_path = "REMOVE ME"
        self.result_data = []

        self.drop_label = QLabel("将视频文件拖拽到此区域开始分析")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("QLabel{border: 2px dashed gray; font-size:16px; padding:20px;}")
        self.drop_label.setAcceptDrops(True)
        self.qvbox.addWidget(self.drop_label)

        # 连接 drop 事件
        self.drop_label.dragEnterEvent = self._drag_enter
        self.drop_label.dropEvent = self._drop_event

        # 当任务完成时，更新 tab 名（通过信号）
        # 由于 tabs 是动态增加的，连接在 add_task 时完成

    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.add_task(path)
                self.video_path = path

    def add_task(self, video_path):
        
        tab = VideoAnalysisBar(video_path)
        self.qvbox.removeWidget(self.drop_label)
        self.drop_label.deleteLater()
        self.qvbox.addWidget(tab)

        # 连接完成信号，更新 tab 标题（按该 tab 对象查找 index，安全）
        def on_finished(tab_widget):
            print(tab_widget.video_path)
            # print(self.parent_tabs) DraggableTabWidget
            # try:
            #     tab_index = self.task_tabs.indexOf(tab_widget)
            #     if tab_index >= 0:
            #         self.task_tabs.setTabText(tab_index, f"完成: {os.path.basename(tab_widget.video_path)}")
            #         self.result_data = tab_widget.result_data
            # except Exception as e:
            #     print("on_finished error:", e)
        tab.finished_signal.connect(on_finished)
