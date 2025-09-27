import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QSplitter
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import mplcursors
import pandas as pd
import math

file1 = r'C:/Users/I_Rin/Desktop/Racecar-tools/distance_speed_u9x.mp4.csv'
file2 = r'C:/Users/I_Rin/Desktop/Racecar-tools/distance_speed_su7u.mp4.csv'

video_path1 = r"C:/Users/I_Rin/Desktop/Racecar-tools/u9x.mp4"
video_path2 = r"C:/Users/I_Rin/Desktop/Racecar-tools/su7u.mp4"

cap1 = cv2.VideoCapture(video_path1)
cap2 = cv2.VideoCapture(video_path2)
    
df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

original_data = [df1.copy(), df2.copy()]
offsets = [0.0, 0.0]
selected_index = [0]
delta_texts = []

def compute_time(x, v):
    v = v * 1000 / 3600  # km/h → m/s
    v[v <= 0] = np.nan
    dx = np.diff(x)
    v_avg = (v[:-1] + v[1:]) / 2
    dt = dx / v_avg
    return np.nansum(dt)

class PltMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Matplotlib + OpenCV in PyQt")
        self.setGeometry(100, 100, 1000, 800)

        # ---- Central widget ----
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # ---- Splitter (上下分屏，1:1) ----
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # ---- Matplotlib figure ----
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        splitter.addWidget(self.canvas)
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)
        
        bottom_splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(bottom_splitter)
        
        # ---- RectangleSelector ----
        self.selector = RectangleSelector(
            self.ax, self.on_select,
            useblit=True, interactive=True,
            button=[1], minspanx=5, minspany=5, spancoords='pixels'
        )
        self.video_label1 = QLabel()
        bottom_splitter.addWidget(self.video_label1)
        
        self.video_label2 = QLabel()
        bottom_splitter.addWidget(self.video_label2)

        # ---- Splitter 比例 ----
        splitter.setSizes([400, 400])  # 上下各一半
        bottom_splitter.setSizes([500,500])
        
        line1, = self.ax.plot(df1['distance'], df1['speed'], label=file1, picker=True)
        line2, = self.ax.plot(df2['distance'], df2['speed'], label=file2, picker=True)

        line1.frame = df1['frame']
        line2.frame = df2['frame']

        self.lines = [line1, line2]

        self.ax.set_xlim(min(df1['distance'].min(), df2['distance'].min()),
                    max(df1['distance'].max(), df2['distance'].max()))
        self.ax.set_xlabel("Distance (m)")
        self.ax.set_ylabel("Speed (km/h)")
        self.ax.set_title("Select region to calculate Δt = t1 - t2")
        self.ax.legend()
        self.canvas.draw()
        
        # ---- Hover tooltips ----
        self.cursor = mplcursors.cursor(self.lines, hover=mplcursors.HoverMode.Transient)
        @self.cursor.connect("add")
        def on_hover(sel):
            x, y = sel.target
            
            idx = int(sel.index)
            other_line = line2 if math.fabs(line1.get_xdata()[idx] - x) < math.fabs(line2.get_xdata()[idx] - x)  else line1
            
            sel.annotation.set_text(f"x:{x}, {line1.get_xdata()[idx]}, {line2.get_xdata()[idx]}")
            
            other_distances = other_line.get_xdata()
            other_idx = int(np.argmin(np.abs(other_distances - x)))
            
            other_speed = other_line.get_ydata()[other_idx]
                
            sel.annotation.set_text(f"distance = {x:.2f} m\nv1 = {y:.2f} km/h\n v2 = {other_speed:.2f} km/h")

            sel.annotation.get_bbox_patch().set(fc="#4f4f4f", alpha=0.6)
            # sel.annotation.get_bbox_patch().set_edgecolor(line.get_color())
            sel.annotation.set_color("white")
            sel.annotation.set_fontsize(9)
            sel.annotation.arrow_patch.set(arrowstyle="-", alpha=.5)
            
            if math.fabs(line1.get_xdata()[idx] - x) < math.fabs(line2.get_xdata()[idx] - x):
                self.show_frame(idx, other_idx)
            else:
                self.show_frame(other_idx, idx)

        # ---- Video QLabel ----


        # # ---- OpenCV video capture ----
        # self.cap = cv2.VideoCapture(video_path)
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.next_frame)
        # self.playing = True
        # self.timer.start(30)  # ~30fps

    def keyPressEvent(self, event):
        # 空格键暂停/继续
        step = 1
        idx = selected_index[0]
        if event.key == 'left':
            offsets[idx] -= step
            self.update_plot()
        elif event.key == 'right':
            offsets[idx] += step
            self.update_plot()
        elif event.key == 'escape':
            for txt in delta_texts:
                txt.remove()
            delta_texts.clear()
            self.fig.canvas.draw_idle()
            print("Cleared all time annotations")
    
    def update_plot(self):
        for i in [0, 1]:
            x = original_data[i]['distance'].values + offsets[i]
            y = original_data[i]['speed'].values
            self.lines[i].set_data(x, y)
        self.fig.canvas.draw_idle()

    def show_frame(self,frame_idx1, frame_idx2):
            if frame_idx1 > cap1.get(cv2.CAP_PROP_FRAME_COUNT):
                frame_idx1 = cap1.get(cv2.CAP_PROP_FRAME_COUNT) - 1
                
            if frame_idx1 < 0:
                frame_idx1 = 0
            
            cap1.set(cv2.CAP_PROP_POS_FRAMES, frame_idx1)
            
            _, frame1 = cap1.read()
            # cv2.imshow(video_path1, frame1)
            
            if frame_idx2 > cap2.get(cv2.CAP_PROP_FRAME_COUNT):
                frame_idx2 = cap2.get(cv2.CAP_PROP_FRAME_COUNT) - 1
                
            if frame_idx2 < 0:
                frame_idx2 = 0
            
            cap2.set(cv2.CAP_PROP_POS_FRAMES, frame_idx2)
            
            _, frame2 = cap2.read()
            # cv2.imshow(video_path2, frame2)
            
            frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
            h, w, ch = frame1.shape
            qimg = QImage(frame1.data, w, h, ch * w, QImage.Format_RGB888)
            self.video_label1.setPixmap(QPixmap.fromImage(qimg))
            
            frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
            h, w, ch = frame2.shape
            qimg = QImage(frame2.data, w, h, ch * w, QImage.Format_RGB888)
            self.video_label2.setPixmap(QPixmap.fromImage(qimg))
        

    def on_select(self, eclick, erelease):
        x1 = min(eclick.xdata, erelease.xdata)
        x2 = max(eclick.xdata, erelease.xdata)
        # 删除太靠近的时间标签，防止看不清
        for t in delta_texts:
            x_text, _ = t.get_position()
            new_position = (x1 + x2) / 2
            if -500 < new_position - x_text < 500:
                t.remove()
                delta_texts.remove(t)

        def get_segment(df, offset):
            x_shifted = df['distance'].values + offset
            y = df['speed'].values
            mask = (x_shifted >= x1) & (x_shifted <= x2)
            return x_shifted[mask], y[mask]

        x1_seg, y1_seg = get_segment(original_data[0], offsets[0])
        x2_seg, y2_seg = get_segment(original_data[1], offsets[1])

        if len(x1_seg) < 2 or len(x2_seg) < 2:
            print("Not enough data in selection.")
            return

        t1 = compute_time(x1_seg, y1_seg)
        t2 = compute_time(x2_seg, y2_seg)
        delta_t = t1 - t2

        print(f"dt = t1 - t2 = {t1:.3f} - {t2:.3f} = {delta_t:.3f} s")
        txt = self.ax.text((x1 + x2) / 2, self.ax.get_ylim()[1]*0.9,
                    f"Δt = {delta_t:.3f} s",
                    ha='center', color='purple', fontsize=10,
                    bbox=dict(facecolor='white', alpha=0.6))
        delta_texts.append(txt)
        self.fig.canvas.draw_idle()

        
    def on_pick(self, event):
        print("on pick")
        if event.artist in self.lines:
            selected_index[0] = self.lines.index(event.artist)
            print(f"Selected curve {selected_index[0]+1}")


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec_())
