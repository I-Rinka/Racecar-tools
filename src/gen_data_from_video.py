from widgets.ocr_canvas import OCRCanvas
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from PyQt5.QtCore import Qt, QRect, QTimer
from core.video_wrapper import VideoWrapper

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROI Selector")
        self.ocr_canvas = OCRCanvas(r"C:/Users/I_Rin/Desktop/Racecar-tools/rimac.mp4")
        self.setCentralWidget(self.ocr_canvas)
        h,w = self.ocr_canvas.get_size_h_w()
        self.resize(w, h)
        self.is_paused = False
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_video)
        self.timer.start(int(1000.0 / self.ocr_canvas.video_frame_rate()))  # ~30fps
    
    def process_video(self):
        if self.is_paused:
            return
        
        if self.ocr_canvas.roi_selected:
            self.timer.setInterval(0)
        else:
            self.timer.setInterval(int(1000.0 / self.ocr_canvas.video_frame_rate()))
            
        if not win.ocr_canvas.video_is_end():
            win.ocr_canvas.play_video()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            win.ocr_canvas.video_paly_back()
            self.is_paused = True
            
        elif event.key() == Qt.Key.Key_Right:
            win.ocr_canvas.play_video()
            self.is_paused = True
        
        elif event.key() == Qt.Key.Key_Space:
            self.is_paused = not self.is_paused
            
        elif event.key() == Qt.Key.Key_Escape:
            self.ocr_canvas.roi_selected = False
            win.ocr_canvas.update()
        

if __name__ == "__main__":
    app = QApplication(sys.argv)

    win = MainWindow()
    win.show()
    


    sys.exit(app.exec_())