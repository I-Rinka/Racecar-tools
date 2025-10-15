import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd
from scipy.signal import savgol_filter
from widgets.figure_canvas import VisCanvas, TimeDiferenceCanvas, AccelCanvas
from widgets.video_canvas import VideoCanvas
from core.sd_analyzer import SDAnalyzer, get_time_differences
from typing import List
import os

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
        
        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)
        top_layout.addStretch()
        top_layout.setAlignment(Qt.AlignRight)
        
        self.show_accel_button = QPushButton("show acceleration")
        self.show_accel_button.clicked.connect(self.show_accel)
        self.show_accel_button.setFixedSize(200, 30)
        self.show_accel_button.setStyleSheet("font-size: 15px;")
        top_layout.addWidget(self.show_accel_button)
        
        self.show_time_button = QPushButton("show time difference")
        self.show_time_button.clicked.connect(self.show_t_canvas)
        self.show_time_button.setFixedSize(220, 30)
        self.show_time_button.setStyleSheet("font-size: 15px;")
        top_layout.addWidget(self.show_time_button)

        self.playing = False
        
        self.canvas = VisCanvas()
        self.canvas.setMinimumHeight(200)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, stretch=1)
        
        self.accel_canvas = AccelCanvas()
        self.accel_canvas.setMinimumHeight(100)
        self.accel_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.accel_canvas, stretch=1)
        self.show_accel_canvas = False
        # self.show_accel_canvas = True
        self.accel_canvas.hide()
        
        self.time_canvas = TimeDiferenceCanvas()
        self.time_canvas.setMinimumHeight(100)
        self.time_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.time_canvas, stretch=1)
        self.show_time_canvas = False
        self.time_canvas.hide()

        # ---- 下方视频区域 (自动2x2布局) ----
        self.video_container = QWidget()
        self.video_layout = QGridLayout(self.video_container)
        layout.addWidget(self.video_container, stretch=2)
    
    def show_t_canvas(self):
        self.show_time_canvas = not self.show_time_canvas
        if self.show_time_canvas:
            self.time_canvas.show()
            self.show_time_button.setText("hide time difference")
            self.update_time_data()
        else:
            self.time_canvas.hide()
            self.show_time_button.setText("show time difference")
    
    def show_accel(self):
        self.show_accel_canvas = not self.show_accel_canvas
        if self.show_accel_canvas:
            self.accel_canvas.show()
            self.show_accel_button.setText("hide acceleration")
        else:
            self.accel_canvas.hide()
            self.show_accel_button.setText("show acceleration")
        
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.canvas.press_ctrl = False
    
        return super().keyReleaseEvent(event)
    
    def update_time_data(self):
        if self.show_time_canvas:
            if len(self.canvas.analyzers) == 2:
                sd1 = self.canvas.analyzers[0]
                sd2 = self.canvas.analyzers[1]
                data = get_time_differences(sd1, sd2)
                self.time_canvas.add_data(data)
                self.time_canvas.draw_idle()
    
    def keyPressEvent(self, event):
        if len(self.canvas.analyzers) == 1:
            if event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
                
                def is_file_in_use(path: str) -> bool:
                    """判断文件是否被其他进程占用"""
                    if not os.path.exists(path):
                        return False

                    try:
                        # Windows：O_EXCL|O_RDWR 在文件被其他进程占用时会报错
                        # Linux/macOS：虽然文件系统允许多进程读，但会检测到锁冲突
                        fd = os.open(path, os.O_RDWR | os.O_EXCL)
                        os.close(fd)
                        return False  # 能打开说明没被占用
                    except OSError:
                        return True    # 打开失败，说明文件正被占用

                name = self.canvas.analyzers[0].name
                file_path, _ = QFileDialog.getSaveFileName(self, "保存数据文件", os.path.expanduser(f"~/{name}.csv"), "CSV 文件 (*.csv)")
                if file_path:
                    if is_file_in_use(file_path):
                         QMessageBox.critical(
                            self,
                            "文件被占用",
                            f"文件：\n{file_path}\n\n当前被其他程序占用，请关闭后再试。",
                        )
                    else:
                        df = self.canvas.analyzers[0].df
                        df.to_csv(file_path, index=False, encoding="utf-8-sig")
                
        step = 10
        idx = self.canvas.selected_index
        if idx >= 0:
            if event.key() == Qt.Key.Key_Left:
                self.canvas.analyzers[idx].adjust_distance(-step)
            elif event.key() == Qt.Key.Key_Right:
                self.canvas.analyzers[idx].adjust_distance(step)
            self.update_time_data()
            self.canvas.draw()
            
        if event.key() == Qt.Key.Key_Escape:
            for txt in self.canvas.delta_texts:
                txt.remove()
            self.canvas.delta_texts.clear()
            self.canvas.draw()
            
        if event.key() == Qt.Key.Key_Control:
            self.canvas.press_ctrl = True
            
        if event.key() == Qt.Key.Key_Space:
            self.playing = not self.playing
            for v in self.videos:
                v.set_playing(self.playing)
            
    def resizeEvent(self, event):
        for v in self.videos:
            v.update_frame()

        super().resizeEvent(event)
    
    def regist_plt_point_animation(self):
        if len(self.videos) != len(self.canvas.analyzers):
            return

        fps = [v.video.get_frame_rate() for v in self.videos]
        min_idx = int(np.argmin(fps))
        for i,instance in enumerate(self.canvas.analyzers):
            vis = instance
            def point_update(s):
                vis.inc_current_index()
                vis.draw_point()
            self.videos[i].register_frame_update_func(point_update)
        
        # 只有一个函数更新，优化性能
        def slowest_update_to_draw(s):
            vis = self.canvas.analyzers[min_idx]
            vis.inc_current_index()

            vis.draw_point()
            self.canvas.update_plot()
            
        self.videos[min_idx].register_frame_update_func(slowest_update_to_draw)

    def refresh_video_layout(self):
        """根据当前视频数量自动重新布局"""
        # 清空旧布局
        for i in reversed(range(self.video_layout.count())):
            widget = self.video_layout.itemAt(i).widget()
            if widget:
                self.video_layout.removeWidget(widget)
                widget.setParent(None)

        count = len(self.videos)
        if count == 0:
            return

        if count == 1:
            self.video_layout.addWidget(self.videos[0], 0, 0)
        elif count == 2:
            self.video_layout.addWidget(self.videos[0], 0, 0)
            self.video_layout.addWidget(self.videos[1], 0, 1)
        elif count == 3:
            self.video_layout.addWidget(self.videos[0], 0, 0)
            self.video_layout.addWidget(self.videos[1], 0, 1)
            self.video_layout.addWidget(self.videos[2], 1, 0)
        else:
            # 4个或更多时，取前4个 2x2
            for idx, label in enumerate(self.videos[:4]):
                row, col = divmod(idx, 2)
                self.video_layout.addWidget(label, row, col)

        # 确保布局均分
        if count > 2:
            for row in range(2):
                self.video_layout.setRowStretch(row, 1)
            
        for col in range(2):
            self.video_layout.setColumnStretch(col, 1)

    def add_video(self, video_path, initial_idx):
        video_canvas = VideoCanvas(video_path)
        self.videos.append(video_canvas)
        def update_video(vis:SDAnalyzer, i:int):
            self.videos[i].update_frame(vis.get_current_frame_index())
            self.accel_canvas.draw_idle()
            self.canvas.draw_idle()
            
        self.canvas.register_instance_on_hover(update_video, len(self.videos) - 1)
        self.accel_canvas.register_instance_on_hover(update_video, len(self.videos) - 1)
        # self.time_canvas.register_instance_on_hover(update_video, len(self.videos) - 1)
        video_canvas.set_frame_index(initial_idx)
        
        if len(self.canvas.analyzers) == 2:
            self.update_time_data()
        
        self.refresh_video_layout()
        self.regist_plt_point_animation()
        
        for video in self.videos:
            video.update_frame(video.frame_index)
        self.canvas.update_plot()
    
    def add_instance(self, path, video_path):
        sd_instance = self.canvas.add_instance_by_file(path)
        initial_idx = sd_instance.get_initial_frame()
        self.accel_canvas.add_data_by_sda(sd_instance)
        self.time_canvas.add_sda(sd_instance)
        self.add_video(video_path, initial_idx)
        return sd_instance

    def add_instance_by_data_frame(self, video_path, df):
        sd_instance = self.canvas.add_instance_by_df(video_path, df)
        initial_idx = sd_instance.get_initial_frame()
        self.accel_canvas.add_data_by_sda(sd_instance)
        self.time_canvas.add_sda(sd_instance)
        self.add_video(video_path, initial_idx)
        return sd_instance
    
    def add_data_frame(self, path):
        res = self.canvas.add_instance_by_file(path)
        self.canvas.update_plot()
        return res
        
    def get_widget(self):
        self.setWindowFlags(self.windowFlags() & ~Qt.Window)
        self.setFocusPolicy(Qt.StrongFocus)
        return self

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PltMainWindow()
    window.show()
    window.add_instance(file1, video_path1)
    window.add_instance(file2, video_path2)
    sys.exit(app.exec_())
