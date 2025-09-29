from widgets.ocr_canvas import OCRCanvas
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from PyQt5.QtCore import Qt, QRect, QTimer
from core.video_wrapper import VideoWrapper
from core.video_processor import TimeSpeedProcessor

class ROIWindow(QMainWindow):
    def __init__(self, video_path):
        super().__init__()
        self.setWindowTitle("ROI Selector")
        self.ocr_canvas = OCRCanvas(video_path)
        self.setCentralWidget(self.ocr_canvas)
        h,w = self.ocr_canvas.get_size_h_w()
        self.resize(w, h)
        self.is_paused = False
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_video)
        self.timer.start(int(1000.0 / self.ocr_canvas.video_frame_rate()))  # ~30fps

        self.processor = TimeSpeedProcessor(self.ocr_canvas.video_frame_rate())
        
    def process_video(self):
        if self.is_paused:
            self.ocr_canvas.enable_select()
            return
        
        self.ocr_canvas.disable_select()
        
        if self.ocr_canvas.roi_selected:
            self.timer.setInterval(0)
        else:
            self.timer.setInterval(int(1000.0 / self.ocr_canvas.video_frame_rate()))
            
        if not self.ocr_canvas.video_is_end():
            frame = self.ocr_canvas.play_video()
            if self.ocr_canvas.roi_selected:
                number = self.processor.process_frame(frame)
                # print(number)
            
        else:
            self.timer.stop()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.ocr_canvas.video_paly_back()
            self.is_paused = True
            
        elif event.key() == Qt.Key.Key_Right:
            self.ocr_canvas.play_video()
            self.ocr_canvas.play_video()
            self.is_paused = True
        
        elif event.key() == Qt.Key.Key_Space:
            self.is_paused = not self.is_paused
            
        elif event.key() == Qt.Key.Key_Escape:
            self.ocr_canvas.roi_selected = False
            self.processor.restart()
            
            self.ocr_canvas.update()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)

    win = ROIWindow(r"C:/Users/I_Rin/Desktop/Racecar-tools/rimac.mp4")
    win.show()
    
    sys.exit(app.exec_())