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
from open_video_gen_data import ROIWindow

class VideoDropAndProcessWidget(QWidget):
    """首页的容器：顶部是拖放区，下面是内层 task tab 控件"""
    # def __init__(self, parent_tabs: QTabWidget, parent=None):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qvbox = QVBoxLayout(self)
        
        self.video_path = ""
        self.result_data = []

        self.drop_label = QLabel("将视频文件拖拽到此区域开始分析")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("QLabel{border: 2px dashed gray; font-size:16px; padding:20px;}")
        self.drop_label.setAcceptDrops(True)
        self.drop_label.setFixedSize(1280, 720)
        
        self.qvbox.addWidget(self.drop_label)

        # 连接 drop 事件
        self.drop_label.dragEnterEvent = self._drag_enter
        self.drop_label.dropEvent = self._drop_event
        self.controller = None
        
        self.resize(1280, 720)
        
        
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
        
        self.qvbox.removeWidget(self.drop_label)
        self.drop_label.deleteLater()
        
        # NOTE this works. TODO: connect progress bar with video frame
        # self.qvbox.addWidget(VideoAnalysisBar(video_path))
        
        controller = ROIWindow(video_path).get_widget()
        self.controller = controller
        self.qvbox.addWidget(controller)
        
        if self.parentWidget():
            self.parentWidget().adjustSize()
    
    def get_result(self):
        if self.controller is None:
            return None
        return self.controller.get_result()
        # tab = VideoAnalysisBar(video_path)
        # self.qvbox.removeWidget(self.drop_label)
        # self.drop_label.deleteLater()
        # self.qvbox.addWidget(tab)

        # # 连接完成信号，更新 tab 标题（按该 tab 对象查找 index，安全）
        # def on_finished(tab_widget):
        #     print(tab_widget.video_path)
        #     # print(self.parent_tabs) DraggableTabWidget
        #     # try:
        #     #     tab_index = self.task_tabs.indexOf(tab_widget)
        #     #     if tab_index >= 0:
        #     #         self.task_tabs.setTabText(tab_index, f"完成: {os.path.basename(tab_widget.video_path)}")
        #     #         self.result_data = tab_widget.result_data
        #     # except Exception as e:
        #     #     print("on_finished error:", e)
        # tab.finished_signal.connect(on_finished)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = QMainWindow()
    main.setWindowTitle("拖拽上传视频，视频上传后框选速度数字，按Ctrl+S生成数据")

    sub = VideoDropAndProcessWidget(main)

    main.setCentralWidget(sub)
            
    sub.setFocusPolicy(Qt.StrongFocus)

    main.show()
    sys.exit(app.exec_())
