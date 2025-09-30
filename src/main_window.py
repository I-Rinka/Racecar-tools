from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer, Qt
from speed_distance_analyer import PltMainWindow
from drop_video_and_process_page import VideoDropAndProcessWidget
import sys

app = QApplication(sys.argv)

main = QMainWindow()
main.setWindowTitle("主窗口")

sub = VideoDropAndProcessWidget(main)

main.setCentralWidget(sub)
        
sub.setFocusPolicy(Qt.StrongFocus)

main.show()
sys.exit(app.exec_())
