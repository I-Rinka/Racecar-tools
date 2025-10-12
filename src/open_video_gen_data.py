import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from core.video_processor import TimeSpeedProcessor
import os
import copy
from widgets.ocr_canvas import OCRCanvas, RoiVideo, VideoSlider

class VideoAnalysisThread(QThread):
    finished = pyqtSignal(object)
    processed = pyqtSignal(object)

    def __init__(self, roi:RoiVideo, processr:TimeSpeedProcessor):
        super().__init__()
        self.roi = roi
        self.running = True
        self.processor = processr

    def run(self):
        # 模拟耗时分析
        while self.running:
            frame = self.roi.get_next_processed_frame()
            
            if frame is None:
                self.finished.emit({"result":self.processor.get_df_data()})
                return

            number = self.processor.process_frame(frame, self.roi.get_cur_index() - 1)
            self.processed.emit({"frame": frame, "number": number, "index": self.roi.get_cur_index() - 1})
    
    def set_new_value(self, idx, roi):
        self.roi.set_new_value(idx, roi)
        
    def stop(self):
        self.running = False
        
    def get_result(self):
        self.stop()
        self.wait()
        return self.processor.get_df_data()
        
    def start(self, priority=QThread.InheritPriority):
        if not self.isRunning():  # 避免重复 start 崩溃
            self.running = True
            super().start(priority)

class ROIWindow(QMainWindow):
    def __init__(self, video_path):
        super().__init__()
        self.setWindowTitle("空格暂停，框选速度区域，Ctrl+S保存并退出")
        self.ocr_canvas = OCRCanvas(video_path)
        # self.setCentralWidget(self.ocr_canvas)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.slider = VideoSlider(0, self.ocr_canvas.video_frame_count())
        self.slider.frameChanged.connect(self.ocr_canvas.paly_video_at_index)
        self.slider.setFocusPolicy(Qt.NoFocus)
        
        layout.addWidget(self.ocr_canvas)
        layout.addWidget(self.slider)
        
        h,w = self.ocr_canvas.get_size_h_w()
        self.resize(w, h)
        
        self.is_paused = False
        
        video_base = os.path.basename(video_path)
        name,_ = os.path.splitext(video_base)
        self.name = name
        self.save_path = os.path.join(os.path.dirname(video_path), self.name+"_database.csv")
        print(self.save_path)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_video)
        self.timer.start(int(1000.0 / self.ocr_canvas.video_frame_rate()))  # ~30fps

        # self.processor = TimeSpeedProcessor(self.ocr_canvas.video_frame_rate())
        
        self.q_thread = VideoAnalysisThread(self.ocr_canvas.get_roi_video_copy(), TimeSpeedProcessor(self.ocr_canvas.video_frame_rate()))
        self.q_thread.processed.connect(self.play_processed_frame)
        self.q_thread.finished.connect(self.finish)
        
    def play_processed_frame(self, result):
        idx = result["index"]
        self.slider.set_frame(idx)
        self.ocr_canvas.paly_video_at_index(idx)
    
    def finish(self):
        self.q_thread.processor.write_csv(self.save_path)
    
    def play_video(self):
        self.ocr_canvas.play_video()
        self.slider.set_frame(self.ocr_canvas.video_current_frame_index())
        
        # roi selected:
        if self.ocr_canvas.roi_selected == True:
            self.timer.stop()
            self.q_thread.set_new_value(self.ocr_canvas.frame_index, self.ocr_canvas.roi)
            self.q_thread.start()
        
    def timer_play_or_pause(self, to_pause = None):
        if to_pause is None: # switch
            if self.is_paused:
                self.ocr_canvas.disable_select()
                self.timer.start(int(1000.0 / self.ocr_canvas.video_frame_rate()))  # ~30fps
            else:
                self.ocr_canvas.enable_select()
                # 切换后是已停止状态：通知处理线程暂停
                if self.ocr_canvas.roi_selected:
                    self.q_thread.stop()
                else:
                    self.timer.stop()
            self.is_paused = not self.is_paused
            return
        
        else:
            if self.is_paused and not to_pause:
                self.ocr_canvas.disable_select()
                self.timer.start(int(1000.0 / self.ocr_canvas.video_frame_rate()))  # ~30fps
            elif not self.is_paused and to_pause:
                self.ocr_canvas.enable_select()
                # 切换后是已停止状态：通知处理线程暂停
                if self.ocr_canvas.roi_selected:
                    self.q_thread.stop()
                else:
                    self.timer.stop()
            self.is_paused = to_pause
            # else not to do
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.q_thread.get_result()
            self.q_thread.processor.write_csv(self.save_path)
            self.timer_play_or_pause(True)
            QMessageBox.information(self, "保存成功", f"文件已保存到:{self.save_path}")
            
        if event.key() == Qt.Key.Key_Left and not self.ocr_canvas.roi_selected:
            self.ocr_canvas.video_paly_back()
            self.slider.set_frame(self.ocr_canvas.video_current_frame_index())
            self.timer_play_or_pause(True)
            
        elif event.key() == Qt.Key.Key_Right and not self.ocr_canvas.roi_selected:
            self.ocr_canvas.play_video()
            self.ocr_canvas.play_video()
            self.slider.set_frame(self.ocr_canvas.video_current_frame_index())
            self.timer_play_or_pause(True)
        
        elif event.key() == Qt.Key.Key_Space:
            self.timer_play_or_pause()
            
        elif event.key() == Qt.Key.Key_Escape:
            self.ocr_canvas.roi_selected = False
            self.q_thread.stop()
            self.q_thread.processor.restart()
            self.ocr_canvas.update()
    
    def get_widget(self):
        self.setWindowFlags(self.windowFlags() & ~Qt.Window)
        self.setFocusPolicy(Qt.StrongFocus)
        return self
    
    def get_size_h_w(self):
        return self.ocr_canvas.get_size_h_w()
    
    def get_result(self):
        return self.q_thread.get_result()
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    file_path = None
    if len(sys.argv) > 1:
        # 拖入文件时，从命令行参数获得路径
        file_path = sys.argv[1]
        
    if file_path is None:
        file_path, _ = QFileDialog.getOpenFileName(None, "选择文件", "", "Video Files (*.mp4)")

    win = ROIWindow(file_path)
    win.show()
    win.setFixedSize(win.size())

    
    sys.exit(app.exec_())