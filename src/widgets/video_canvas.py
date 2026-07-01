import cv2
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from core.video_wrapper import VideoWrapper


class VideoCanvas(QLabel):
    def __init__(self, video_path: str):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(160, 90)

        self.playing = False
        self.video = VideoWrapper(video_path)

        self.timer = QTimer()
        self.timer.timeout.connect(self.start_timer)
        self.timer.start(int(1000.0 / self.video.get_frame_rate()))
        self.func = None
        self.frame_index = 0
        self._current_frame = None

    def set_frame_index(self, index: int):
        self.frame_index = index
        self.video.set_frame(index)

    def set_playing(self, is_playing):
        self.playing = is_playing

    def register_frame_update_func(self, func):
        self.func = func

    def start_timer(self):
        if self.playing:
            self.update_frame()
            if self.func:
                self.func(self)

    def get_current_video_frame_index(self):
        return self.frame_index

    def update_frame(self, index: int = -1):
        if index == -1:
            frame = self.video.get_next_frame()
            if frame is not None:
                self.frame_index += 1
        else:
            frame = self.video.set_and_get_frame(index)
            self.frame_index = index
        if frame is None:
            return

        self._current_frame = frame
        self._display_frame()

    def _display_frame(self):
        if self._current_frame is None:
            return
        frame = cv2.cvtColor(self._current_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        qimg = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
        scaled = qimg.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(QPixmap.fromImage(scaled))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._display_frame()
