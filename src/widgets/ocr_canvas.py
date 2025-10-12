import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QSlider
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QPoint
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
        if self._dragging:
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
    def __init__(self, video_path: str):
        super().__init__()
        self.video = VideoWrapper(video_path)
        self.frame_index = 0
        self.frame = self.video.set_and_get_frame(0)  # numpy BGR image
        self.qimage: QImage = cvimg_to_qt(self.frame) if self.frame is not None else None

        self.start = None      # image-coords QPoint or None
        self.end = None        # image-coords QPoint or None
        self.roi = None        # (x, y, w, h) in image coords
        self.roi_selected = False
        self.can_select = False

        # Optional: 避免 QLabel 自动缩放改变行为（按需）
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(False)
        
        self.setFixedSize(self.qimage.size())

    def enable_select(self):
        self.can_select = True

    def disable_select(self):
        self.can_select = False

    # ---------------------- 辅助：计算图像在 QLabel 的显示矩形 ----------------------
    def _image_size(self):
        """返回原始图像的 (w, h)"""
        if self.frame is None:
            return 0, 0
        h, w = self.frame.shape[:2]
        return w, h

    def _image_display_rect(self) -> QRect:
        """计算原始图像在 QLabel 中按 KeepAspectRatio 后的显示矩形（QRect，widget 坐标系）"""
        label_w, label_h = self.width(), self.height()
        img_w, img_h = self._image_size()
        if img_w == 0 or img_h == 0:
            return QRect(0, 0, 0, 0)

        # scale 保持长宽比
        scale = min(label_w / img_w, label_h / img_h)
        disp_w = int(img_w * scale)
        disp_h = int(img_h * scale)
        offset_x = (label_w - disp_w) // 2
        offset_y = (label_h - disp_h) // 2
        return QRect(offset_x, offset_y, disp_w, disp_h)

    # ---------------------- 坐标映射 ----------------------
    def map_to_image(self, pos: QPoint) -> QPoint:
        """
        将 widget 坐标 (pos) 映射到 image 坐标 (QPoint)。
        如果超出 image 显示区域，会 clamp 到 image 边界。
        """
        img_w, img_h = self._image_size()
        if img_w == 0 or img_h == 0:
            return QPoint(0, 0)

        disp_rect = self._image_display_rect()
        # clamp 到显示区域
        x = min(max(pos.x(), disp_rect.left()), disp_rect.right())
        y = min(max(pos.y(), disp_rect.top()), disp_rect.bottom())

        # 转为相对于显示区域左上的坐标，然后映射到原图尺寸
        rel_x = x - disp_rect.left()
        rel_y = y - disp_rect.top()
        img_x = int(rel_x * (img_w / disp_rect.width()))
        img_y = int(rel_y * (img_h / disp_rect.height()))

        # clamp image coords
        img_x = max(0, min(img_x, img_w - 1))
        img_y = max(0, min(img_y, img_h - 1))
        
        return QPoint(img_x, img_y)

    def map_from_image(self, img_pt: QPoint) -> QPoint:
        """
        将 image 坐标映射回 widget (绘制) 坐标。
        """
        img_w, img_h = self._image_size()
        if img_w == 0 or img_h == 0:
            return QPoint(0, 0)

        disp_rect = self._image_display_rect()
        x = int(img_pt.x() * (disp_rect.width() / img_w) + disp_rect.left())
        y = int(img_pt.y() * (disp_rect.height() / img_h) + disp_rect.top())
        return QPoint(x, y)

    # ---------------------- 鼠标事件（使用 image 坐标） ----------------------
    def mousePressEvent(self, event):
        if self.can_select and (not self.roi_selected) and event.button() == Qt.LeftButton:
            self.start = self.map_to_image(event.pos())
            self.end = self.start
            self.update()

    def mouseMoveEvent(self, event):
        if self.can_select and (not self.roi_selected) and (self.start is not None):
            self.end = self.map_to_image(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.can_select and (not self.roi_selected) and event.button() == Qt.LeftButton and (self.start is not None):
            self.end = self.map_to_image(event.pos())
            x1, y1 = min(self.start.x(), self.end.x()), min(self.start.y(), self.end.y())
            x2, y2 = max(self.start.x(), self.end.x()), max(self.start.y(), self.end.y())
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            self.roi = (x1, y1, w, h)
            self.roi_selected = True
            self.start = None
            self.end = None
            self.update()

    # ---------------------- 视频相关（保持你原有逻辑） ----------------------
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
            self.frame_index = max(0, self.frame_index - 2)
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
        self.qimage = cvimg_to_qt(self.frame)
        self.setPixmap(QPixmap.fromImage(self.qimage))
        self.update()

    def get_roi_video_copy(self):
        return RoiVideo(self.video, self.frame_index, self.roi)

    def play_video(self) -> cv2.Mat:
        self.frame_index += 1
        self.frame = self.video.get_next_frame()
        if self.frame is None:
            return None

        self.qimage = cvimg_to_qt(self.frame)
        self.setPixmap(QPixmap.fromImage(self.qimage))

        if not self.roi_selected:
            return self.frame

        self.update()
        x, y, w, h = self.roi
        return self.frame[y:y + h, x:x + w].copy()

    # ---------------------- 绘制：只遮罩图像区域、正确绘制 ROI ----------------------
    def paintEvent(self, event):
        # 先让 QLabel 正常绘制（包括 pixmap/qimage）
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(Qt.red, 2, Qt.SolidLine)
        painter.setRenderHint(QPainter.Antialiasing)

        img_w, img_h = self._image_size()
        if img_w == 0 or img_h == 0:
            return

        # 2) 正在拖动时：在 image 显示区域上绘制临时矩形（反映 image-coords）
        if self.start and self.end:
            p1 = self.map_from_image(self.start)
            p2 = self.map_from_image(self.end)
            draw_rect = QRect(p1, p2).normalized()
            # 在临时框内，绘制原始图像的对应片段（缩放到 draw_rect）以"清空遮罩"
            x_img = min(self.start.x(), self.end.x())
            y_img = min(self.start.y(), self.end.y())
            w_img = abs(self.start.x() - self.end.x())
            h_img = abs(self.start.y() - self.end.y())
            if w_img > 0 and h_img > 0:
                sub = self.frame[y_img:y_img + h_img, x_img:x_img + w_img].copy()
                qi = cvimg_to_qt(sub)
                painter.drawImage(draw_rect, qi)
            painter.setPen(pen)
            painter.drawRect(draw_rect)

        # 3) 已选中 ROI：把 ROI 区域恢复显示并画边框（只在 image display rect 内操作）
        if self.roi_selected and self.roi is not None:
            disp_rect = self._image_display_rect()

            mask_color = QColor(0, 0, 0, 160)
            painter.fillRect(disp_rect, mask_color)
            
            x, y, w, h = self.roi
            # 防越界
            x = max(0, min(x, img_w - 1))
            y = max(0, min(y, img_h - 1))
            w = max(1, min(w, img_w - x))
            h = max(1, min(h, img_h - y))

            top_left = self.map_from_image(QPoint(x, y))
            bottom_right = self.map_from_image(QPoint(x + w, y + h))
            rect = QRect(top_left, bottom_right).normalized()

            sub = self.frame[y:y + h, x:x + w].copy()
            qi = cvimg_to_qt(sub)
            painter.drawImage(rect, qi)

            painter.setPen(pen)
            painter.drawRect(rect)

            # 可选：在左上角显示 roi 数值，便于调试
            txt = f"ROI: x={x} y={y} w={w} h={h}"
            painter.setPen(Qt.white)
            painter.drawText(disp_rect.left() + 6, disp_rect.top() + 16, txt)

    def get_size_h_w(self):
        return self.frame.shape[:2]