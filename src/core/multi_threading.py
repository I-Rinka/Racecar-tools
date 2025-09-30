
class VideoAnalysisWorker(QThread):
    """后台分析线程（模拟），发送进度和完成信号。"""
    progress_update = pyqtSignal(int)        # emit int 0..100
    finished = pyqtSignal(object)           # emit dict {'path':..., 'data':...}

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self._running = True

    def stop(self):
        self._running = False

    # TODO Move analysis logic to here
    def run(self):
        # 这里用模拟的耗时任务；把实际视频分析逻辑放在这里
        try:
            data = []
            for i in range(101):
                if not self._running:
                    return
                time.sleep(0.03)                # 模拟开销
                # 模拟产生的 (distance, speed) 数据
                data.append((i, float(60 + 40 * random.random())))
                self.progress_update.emit(i)
            if self._running:
                self.finished.emit({'path': self.video_path, 'data': data})
        except Exception as e:
            # 不要让异常在线程里导致进程崩溃
            print("Worker exception:", e)

# TODO Make this become progress bar of video
class VideoAnalysisBar(QWidget):
    """每个分析任务的 tab 内容。包含标签、进度条，可拖拽（完成后）"""
    finished_signal = pyqtSignal(object)  # emit self when finished

    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.result_data = None
        self.worker = None

        layout = QVBoxLayout(self)
        self.label = QLabel(f"分析中: {os.path.basename(video_path)}")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # 一个小提示，只有完成后显示，提示可以拖拽到绘图界面
        self.hint = QLabel("分析完成后可直接拖拽此 tab 到绘图界面")
        self.hint.setVisible(False)
        layout.addWidget(self.hint)

        layout.addStretch()

        self.start_worker()
        

