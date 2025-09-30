from widgets.ocr_canvas import OCRCanvas
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt, QTimer, QCoreApplication
from core.video_processor import TimeSpeedProcessor
import os

class ROIWindow(QMainWindow):
    def __init__(self, video_path):
        super().__init__()
        self.setWindowTitle("空格暂停，框选速度区域，Ctrl+S保存并退出")
        self.ocr_canvas = OCRCanvas(video_path)
        self.setCentralWidget(self.ocr_canvas)
        h,w = self.ocr_canvas.get_size_h_w()
        self.resize(w, h)
        
        self.is_paused = False
        
        base = os.path.basename(video_path)
        name,_ = os.path.splitext(base)
        self.name = name
        
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
                number = self.processor.process_frame(frame, self.ocr_canvas.frame_index - 1)
                print(number) # get number
            
        else:
            self.timer.stop()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.processor.write_csv(self.name+"_database.csv")
            self.timer.stop()
            QMessageBox.information(self, "保存成功", f"文件已保存到:{os.path.join(os.getcwd(), self.name+"_database.csv")}")
            QCoreApplication.instance().quit()
            
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
    
    def get_widget(self):
        self.setWindowFlags(self.windowFlags() & ~Qt.Window)
        self.setFocusPolicy(Qt.StrongFocus)
        return self
    
    def get_size_h_w(self):
        return self.ocr_canvas.get_size_h_w()
    
    def get_result(self):
        return self.processor.get_df_data()
            
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
    
    sys.exit(app.exec_())