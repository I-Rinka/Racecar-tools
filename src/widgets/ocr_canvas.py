import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect
from core.video_wrapper import VideoWrapper

def cvimg_to_qt(img):
    """把OpenCV的BGR图像转成Qt的QImage"""
    h, w, ch = img.shape
    bytes_per_line = ch * w
    return QImage(img.data, w, h, bytes_per_line, QImage.Format_BGR888)

class OCRCanvas(QLabel):
    def __init__(self, video_path:str):
        super().__init__()
        self.video = VideoWrapper(video_path)
        self.frame_index = 0
        self.frame = self.video.set_and_get_frame(0)
        self.start = None
        self.end = None
        self.roi = None
        self.roi_selected = False  # 标记是否已选择
        self.can_select = False
    
    def enable_select(self):
        self.can_select = True
    
    def disable_select(self):
        self.can_select = False

    def mousePressEvent(self, event):
        if self.can_select and self.roi_selected == False and event.button() == Qt.LeftButton:
            self.start = event.pos()
            self.end = self.start
            self.update()


    def mouseMoveEvent(self, event):
        if self.can_select and self.roi_selected == False and self.start:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.can_select and self.roi_selected == False and event.button() == Qt.LeftButton and self.start:
            self.end = event.pos()
            x1, y1 = min(self.start.x(), self.end.x()), min(self.start.y(), self.end.y())
            x2, y2 = max(self.start.x(), self.end.x()), max(self.start.y(), self.end.y())
            self.roi = (x1, y1, x2 - x1, y2 - y1)
            self.roi_selected = True
            self.start = None
            self.end = None
            self.update()
            
    def video_is_end(self):
        return not self.video.is_opened()
    
    def video_frame_rate(self):
        return self.video.get_frame_rate()
    
    def video_paly_back(self):
        if self.frame_index > 0:
            self.frame_index = self.frame_index - 2
            self.video.set_frame(self.frame_index)
            self.play_video()
            self.update()
    
    def get_roi_frame(self) -> cv2.Mat:
        if not self.roi_selected:
            return None
        return self.frame

    def play_video(self) -> cv2.Mat:
        self.frame_index = self.frame_index + 1
        self.frame = self.video.get_next_frame()
        self.qimage:QImage = cvimg_to_qt(self.frame)
        self.setPixmap(QPixmap.fromImage(self.qimage))
        
        if not self.roi_selected:
            return self.frame
        
        self.update()
        x, y, w, h = self.roi
        
        return self.frame[y:y+h, x:x+w].copy()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)

        # 画拖动中的 ROI（红框）
        pen = QPen(Qt.red, 2, Qt.SolidLine)
        if self.start and self.end:
            painter.setPen(pen)
            rect = QRect(self.start, self.end)
            painter.drawRect(rect)
            
        if self.roi_selected:
            x, y, w, h = self.roi

            rect = QRect(x, y, w, h)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 180))
            
            frame = self.frame[y:y+h, x:x+w].copy()
            painter.drawImage(rect, cvimg_to_qt(frame))
            
            painter.setPen(pen)
            painter.drawRect(rect)
            
    def get_size_h_w(self):
        return self.frame.shape[:2] 