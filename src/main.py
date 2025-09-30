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
from plot_page import PlotTab
from drop_video_and_process_page import VideoDropAndProcessWidget

# --------------------- 自定义可拖拽 TabBar ---------------------
class DraggableTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_pos = None
        self.pressed_index = -1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pressed_index = self.tabAt(event.pos())
            self.mouse_pressed = True
        # 阻止 QTabWidget 的默认切换
        event.accept()
        

    def mouseReleaseEvent(self, event):
        if self.mouse_pressed and event.button() == Qt.LeftButton:
            release_index = self.tabAt(event.pos())
            if release_index == self.pressed_index and release_index != -1:
                # 手动切换 Tab 页面
                if self.parent():
                    self.parent().setCurrentIndex(release_index)
        self.mouse_pressed = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        #if self._press_pos is None or self._press_index < 0:
        #    return
        # 达到拖动阈值
        # if (event.pos() - self._press_pos).manhattanLength() < QApplication.startDragDistance():
        #     return

        tab_widget = self.parent()  # QTabWidget
        index = self.pressed_index
        # if index < 0 or index >= tab_widget.count():
        #     return
        widget = tab_widget.widget(index)
        # 只允许 VideoAnalysisTab 并且已经完成
        if not isinstance(widget, VideoDropAndProcessWidget):
            return
        # if not widget.result_data:
        #     return

        # 构建 mime payload（使用 pickle 打包）
        try:
            payload = {
                'path': widget.video_path,
                'data': widget.get_result()
            }
            pickled = pickle.dumps(payload)
            mime = QMimeData()
            mime.setData('application/x-video-analysis', QByteArray(pickled))
            mime.setText(widget.video_path)
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec_(Qt.CopyAction)
        except Exception as e:
            print("Drag start failed:", e)
        finally:
            self._press_pos = None
            self._press_index = -1

# --------------------- 内层可拖拽 TabWidget ---------------------
class DraggableTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        bar = DraggableTabBar(self)
        self.setTabBar(bar)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._on_tab_close_requested)

    def _on_tab_close_requested(self, index):
        widget = self.widget(index)
        if isinstance(widget, VideoDropAndProcessWidget):
            try:
                widget.worker.stop()
                widget.worker.wait(2000)
            except Exception:
                pass
        self.removeTab(index)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("圈速工具")
        self.resize(1100, 700)

        self.main_tabs = DraggableTabWidget()
        self.setCentralWidget(self.main_tabs)

        # 默认首页：视频分析容器
        self.analysis_container = VideoDropAndProcessWidget()
        self.main_tabs.addTab(self.analysis_container, "视频解析")

        # 菜单
        self._create_menu()

    def _create_menu(self):
        menu = self.menuBar().addMenu("文件")
        new_plot_action = menu.addAction("新视频解析")
        new_plot_action.triggered.connect(self.add_analyze_tab)
    
        new_plot_action = menu.addAction("新圈速分析")
        new_plot_action.triggered.connect(self.add_plot_tab)

        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(QApplication.instance().quit)

    def add_plot_tab(self):
        plot = PlotTab()
        idx = self.main_tabs.addTab(plot, "圈速分析")
        self.main_tabs.setCurrentIndex(idx)
    
    def add_analyze_tab(self):
        plot = VideoDropAndProcessWidget()
        idx = self.main_tabs.addTab(plot, "视频解析")
        self.main_tabs.setCurrentIndex(idx)

    def _on_main_tab_close(self, index):
        # 关闭顶层 tab（如果是分析首页，不允许关闭）
        widget = self.main_tabs.widget(index)
        if widget is self.analysis_container:
            # 不允许关闭首页，可提示
            QMessageBox.information(self, "提示", "不能关闭首页（视频分析）。")
            return
        # 安全删除
        try:
            self.main_tabs.removeTab(index)
        except Exception:
            pass

# --------------------- 运行 ---------------------
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
