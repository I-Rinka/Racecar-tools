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

    def set_and_get_frame(self, frame_index:int):
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
    
    def get_frame_count(self):
        return self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
    
    def is_opened(self):
        return self.cap.isOpened()
