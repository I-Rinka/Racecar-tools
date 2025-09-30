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

from speed_distance_analyer import PltMainWindow

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

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-video-analysis'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        global it

        try:
            ba = event.mimeData().data('application/x-video-analysis')
            pickled = bytes(ba)             # QByteArray -> bytes
            payload = pickle.loads(pickled)
            # name = payload.get('name') or os.path.basename(payload.get('path', 'data'))
            video_path = payload.get('path')
            data = payload.get('data')
            self.plt.add_instance_by_data_frame(video_path, data)
            
        except Exception as e:
            print("Drop parse failed:", e)
            return