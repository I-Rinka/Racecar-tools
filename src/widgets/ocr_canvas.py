import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QSlider
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from core.video_wrapper import VideoWrapper
import copy

class VideoSlider(QSlider):
    frameChanged = pyqtSignal(int)  # 拖动时发出的信号（用于跳帧）

    def __init__(self, start = 0, total_frames=0):
        super().__init__(Qt.Horizontal)
        self.setRange(start, max(start, total_frames - 1))
        self._dragging = False
        self._last_value = 0

        self.sliderPressed.connect(self._on_press)
        self.sliderReleased.connect(self._on_release)
        self.valueChanged.connect(self._on_value_change)

    def _on_press(self):
        self._dragging = True

    def _on_release(self):
        self._dragging = False
        self.frameChanged.emit(self.value())

    def _on_value_change(self, value):
        self._last_value = value
        self.frameChanged.emit(value)

    def set_frame(self, frame_index):
        """由VideoPlayer调用以更新滑块位置"""
        if not self._dragging:
            self.blockSignals(True)
            self.setValue(frame_index)
            self.blockSignals(False)


def cvimg_to_qt(img):
    """把OpenCV的BGR图像转成Qt的QImage"""
    h, w, ch = img.shape
    bytes_per_line = ch * w
    return QImage(img.data, w, h, bytes_per_line, QImage.Format_BGR888)

class RoiVideo():
    def __init__(self,video:VideoWrapper, frame_idx: int, roi:tuple):
        self.video = video.copy()
        self.roi = roi
        self.frame_index = frame_idx
        self.video.set_frame(self.frame_index)

    def get_next_processed_frame(self):
        self.frame_index = self.frame_index + 1
        self.frame = self.video.get_next_frame()
        if self.frame is None:
            return None

        x, y, w, h = self.roi
        return self.frame[y:y+h, x:x+w].copy()
    
    def set_new_value(self, idx, roi):
        self.frame_index = idx
        self.video.set_frame(self.frame_index)
        self.roi=roi

    def get_cur_index(self):
        return self.frame_index

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
    
    def video_frame_count(self):
        return int(self.video.get_frame_count())
    
    def video_current_frame_index(self):
        return self.frame_index
    
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
    
    def paly_video_at_index(self, idx):
        self.frame_index = idx
        self.frame = self.video.set_and_get_frame(idx)
        self.qimage:QImage = cvimg_to_qt(self.frame)
        self.setPixmap(QPixmap.fromImage(self.qimage))
        self.update()
    
    def get_roi_video_copy(self):
        return RoiVideo(self.video, self.frame_index, self.roi)

    def play_video(self) -> cv2.Mat:
        self.frame_index = self.frame_index + 1
        self.frame = self.video.get_next_frame()
        if self.frame is None:
            return None
        
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