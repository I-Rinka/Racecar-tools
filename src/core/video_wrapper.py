import cv2
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt

class VideoWrapper():
    def __init__(self,video_path:str):
        self.cap = cv2.VideoCapture(video_path)

    def set_frame(self, frame_index:int):
        if self.cap.get(cv2.CAP_PROP_FRAME_COUNT) > frame_index:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

    def get_frame(self, frame_index:int):
        if self.cap.get(cv2.CAP_PROP_FRAME_COUNT) > frame_index:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            _, frame = self.cap.read()
            return frame
        return None
    
    def get_next_frame(self):
        _, frame = self.cap.read()
        return frame

    def get_frame_rate(self):
        return self.cap.get(cv2.CAP_PROP_FPS)

class VideoCanvas(QLabel):
    def __init__(self, video_path:str):
        super().__init__()

        self.sizePolicy().setVerticalPolicy(QSizePolicy.Preferred)
        self.playing = False

        self.video = VideoWrapper(video_path)

        self.timer = QTimer()
        self.timer.timeout.connect(self.start_timer)
        self.timer.start(int(1000.0 / self.video.get_frame_rate()))  # ~30fps
        self.func = None
        self.frame_index = 0
    
    def set_frame_index(self, index: int):
        self.frame_index = index
        self.video.set_frame(index)

    def set_playing(self, is_palying):
        self.playing = is_palying

    def add_update_func(self, func):
        self.func = func

    def start_timer(self):
        if self.playing:
            self.update_frame()
            if self.func:
                self.func(self)

    def update_frame(self, index:int = -1):
        frame = self.video.get_next_frame() if index == -1 else self.video.get_frame(index)
        if frame is None: return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        qimg = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qimg.scaled(self.size(), Qt.KeepAspectRatio)))


