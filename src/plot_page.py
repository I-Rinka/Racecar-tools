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
    QListWidget, QListWidgetItem, QMessageBox, QFileDialog
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from speed_distance_analyer import PltMainWindow

def get_video_path(csv_path):
    dir_path = os.path.dirname(csv_path)
    csv_name = os.path.basename(csv_path)

    filename_no_ext = csv_name[:-len("_database.csv")]  # 去掉前缀和 .csv

    # 构造对应的 mp4 路径
    mp4_path = os.path.join(dir_path, f"{filename_no_ext}.mp4")

    # 检查文件是否存在
    if os.path.isfile(mp4_path):
        return mp4_path
    else:
        raise FileNotFoundError(f"没有找到对应的 MP4 文件: {mp4_path}")

class PlotTab(QWidget):
    """用于接收分析结果并绘图的页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.qvbox = layout
        self.plt = PltMainWindow().get_widget()
        layout.addWidget(self.plt)

        self._lines = {}  # name -> matplotlib Line2D
        self.setAcceptDrops(True)

        # 状态变量
        self.pending_csv = None      # 待配对的 CSV 路径
        self.csv_locked = False      # 连续 CSV 拖入锁定标志
        self.initial_idx = 0

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-video-analysis') or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # ===== 模式 1：原有 application/x-video-analysis 拖放 =====
        if event.mimeData().hasFormat('application/x-video-analysis'):
            try:
                ba = event.mimeData().data('application/x-video-analysis')
                pickled = bytes(ba)  # QByteArray -> bytes
                payload = pickle.loads(pickled)
                video_path = payload.get('path')
                data = payload.get('data')
                self.plt.add_instance_by_data_frame(video_path, data)
                return
            except Exception as e:
                QMessageBox.critical(self, "错误", f"拖放解析失败：{e}")
                return

        # ===== 模式 2：.csv / .mp4 配对拖放 =====
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if not urls:
                return

            for url in urls:
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1].lower()

                # 🚫 非 csv / mp4 文件直接拒绝
                if ext not in ['.csv', '.mp4']:
                    QMessageBox.warning(self, "错误", f"不支持的文件类型：{ext}")
                    return

                # 📄 拖入 CSV
                if ext == '.csv':
                    if self.pending_csv:
                        self.pending_csv = None
                        self.csv_locked = True
                        return
                    
                    try:
                        video_path = get_video_path(path)
                        instance = self.plt.add_instance(path, video_path)
                    except Exception as e:
                            instance = self.plt.add_data_frame(path)
                            self.initial_idx = instance.get_initial_frame()
                            
                            self.pending_csv = path
                            QMessageBox.information(self, "提示", f"CSV 文件已添加：{path}，请拖入对应 MP4 文件配对，或者拖入其他csv文件")
                            return

                # 🎥 拖入 MP4
                if ext == '.mp4':
                    if self.csv_locked:
                        QMessageBox.warning(self, "错误", "数据分析模式，只能拖入csv")
                        return
                    
                    if not self.pending_csv:
                        QMessageBox.warning(self, "错误", "不允许先拖入 MP4，请先拖入对应 CSV")
                        return
                    
                    # print(path)
                    self.plt.add_video(path, self.initial_idx)
                    self.pending_csv = None
                    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("圈速工具")
        plot = PlotTab()
        self.main_tabs = QTabWidget()
        self.setCentralWidget(self.main_tabs)
        self.main_tabs.addTab(plot, "圈速分析")
    
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
