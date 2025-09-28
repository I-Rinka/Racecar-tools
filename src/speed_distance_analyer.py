import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd
from scipy.signal import savgol_filter
from core.figure_canvas import VisCanvas
from core.video_wrapper import VideoCanvas
from typing import List

file1 = r'C:/Users/I_Rin/Desktop/Racecar-tools/distance_speed_u9x.mp4.csv'
file2 = r'C:/Users/I_Rin/Desktop/Racecar-tools/distance_speed_su7u.mp4.csv'

video_path1 = r"C:/Users/I_Rin/Desktop/Racecar-tools/u9x.mp4"
video_path2 = r"C:/Users/I_Rin/Desktop/Racecar-tools/su7u.mp4"

class PltMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.videos:List[VideoCanvas] = []

        self.setWindowTitle("Matplotlib + OpenCV in PyQt")
        self.setGeometry(100, 100, 1000, 800)

        # ---- Central widget ----
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # ---- Splitter (上下分屏，1:1) ----
        self.splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.splitter)
        
        self.canvas = VisCanvas()
        self.canvas.setMinimumHeight(200)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.splitter.addWidget(self.canvas)
        
        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.bottom_splitter)
     
        self.playing = False

    def keyPressEvent(self, event):
        step = 10
        idx = self.canvas.selected_index
        if idx >= 0:
            if event.key() == Qt.Key_Left:
                self.canvas.instances[idx].adjust_distance(-step)
            elif event.key() == Qt.Key_Right:
                self.canvas.instances[idx].adjust_distance(step)
            self.canvas.draw()
            
        if event.key() == Qt.Key.Key_Escape:
            for txt in self.canvas.delta_texts:
                txt.remove()
            self.canvas.delta_texts.clear()
            self.canvas.draw()
            
        if event.key() == Qt.Key_Space:
            self.playing = not self.playing
            for v in self.videos:
                v.set_playing(self.playing)
            
    def resizeEvent(self, event):
        for v in self.videos:
            v.update_frame()

        super().resizeEvent(event)
    
    def show(self):
        fps = [v.video.get_frame_rate() for v in self.videos]
        min_idx = int(np.argmin(fps))
        for instance in self.canvas.instances:
            vis = instance
            def func(s):
                vis.inc_current_index()
                vis.draw_point()
            instance.videoCanvas.add_update_func(func)
        
        def func_slowest(s):
            vis = self.canvas.instances[min_idx]
            vis.inc_current_index()
            vis.draw_point()
            self.canvas.draw()

        self.canvas.instances[min_idx].videoCanvas.add_update_func(func_slowest)

        super().show()

    def add_instance(self, path, video_path):
        video_canvas = VideoCanvas(video_path)
        self.videos.append(video_canvas)
        sd_instance = self.canvas.add_instance(path)
        initial_idx = sd_instance.get_initial_frame()
        sd_instance.add_video_canvas(video_canvas)
        video_canvas.set_frame_index(initial_idx)
        self.bottom_splitter.addWidget(video_canvas)
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PltMainWindow()
    window.add_instance(file1, video_path1)
    window.add_instance(file2, video_path2)
    window.show()
    sys.exit(app.exec_())
