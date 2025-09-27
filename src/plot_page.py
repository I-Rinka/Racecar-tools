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

from windowed_speed_distance_analyzer import PltMainWindow
import pandas as pd


file1 = r'C:/Users/I_Rin/Desktop/Racecar-tools/distance_speed_u9x.mp4.csv'
file2 = r'C:/Users/I_Rin/Desktop/Racecar-tools/distance_speed_su7u.mp4.csv'

df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

dfs = [df1, df2]
it = 0

class PlotTab(QWidget):
    """用于接收分析结果并绘图的页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # 左侧列表（显示导入的数据项）
        self.list_widget = QListWidget()
        splitter.addWidget(self.list_widget)
        self.list_widget.setMaximumHeight(50)

        # 右侧 matplotlib 画布
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        splitter.addWidget(self.canvas)

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
            name = payload.get('name') or os.path.basename(payload.get('path', 'data'))
            data = payload.get('data')
        except Exception as e:
            print("Drop parse failed:", e)
            return

        # 防止重复导入同名数据
        base_name = name
        count = 1
        while base_name in self._lines:
            base_name = f"{name}_{count}"
            count += 1
        name = base_name

        # 在列表中添加一项和删除按钮
        item = QListWidgetItem()
        widget_row = QWidget()
        row_layout = QHBoxLayout(widget_row)
        label = QLabel(name)
        btn = QPushButton("删除")
        btn.setFixedWidth(60)
        row_layout.addWidget(label)
        row_layout.addWidget(btn)
        row_layout.setContentsMargins(2, 2, 2, 2)
        item.setSizeHint(widget_row.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget_row)

        # 绘图
        # try:
        #     xs, ys = zip(*data)
        # except Exception:
        #     # 可能 data 是一维数组（模拟）时处理
        #     xs = list(range(len(data)))
        #     ys = data

        # line, = self.ax.plot(xs, ys, label=name)
        # self._lines[name] = line
        # self.ax.legend()
        # self.canvas.draw_idle()
        df = dfs[it]
        line, = self.ax.plot(df["distance"], df["speed"], label=name)
        self._lines[name] = line
        self.ax.legend()
        self.canvas.draw_idle()
        
        it += 1
        if it == 2:
            window = PltMainWindow()
            window.show()

        def remove_item():
            # 从画布删除
            try:
                ln = self._lines.pop(name, None)
                if ln:
                    ln.remove()
                # 从列表删除
                row_index = self.list_widget.row(item)
                self.list_widget.takeItem(row_index)
                self.ax.legend()
                self.canvas.draw_idle()
            except Exception as e:
                print("Remove item error:", e)

        btn.clicked.connect(remove_item)
