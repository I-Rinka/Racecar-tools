from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer, Qt
from speed_distance_analyer import PltMainWindow

import sys

file1 = r'C:/Users/I_Rin/Desktop/Racecar-tools/distance_speed_u9x.mp4.csv'
file2 = r'C:/Users/I_Rin/Desktop/Racecar-tools/distance_speed_su7u.mp4.csv'

video_path1 = r"C:/Users/I_Rin/Desktop/Racecar-tools/u9x.mp4"
video_path2 = r"C:/Users/I_Rin/Desktop/Racecar-tools/su7u.mp4"


app = QApplication(sys.argv)

main = QMainWindow()
main.setWindowTitle("主窗口")

tab = QTabWidget()
main.setCentralWidget(tab)


sub = PltMainWindow()

sub.setWindowFlags(sub.windowFlags() & ~Qt.Window)   # 去掉顶层窗口标志
sub.setParent(tab)                                   # 设置父控件
tab.addTab(sub, "子窗口")
sub.setFocusPolicy(Qt.StrongFocus)
sub.add_instance(file1, video_path1)
sub.add_instance(file2, video_path2)


main.show()
sys.exit(app.exec_())
