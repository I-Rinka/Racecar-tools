from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from core.sd_analyzer import SDAnalyzer
import mplcursors
from typing import List
from matplotlib.widgets import RectangleSelector
from widgets.data_editor import DataEditor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QWidget, QVBoxLayout

from core.video_processor import regen_df_by_time_speed
import numpy as np

class VisCanvas(FigureCanvas):
    def __init__(self):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        
        self.delta_texts = []
        self.analyzers:List[SDAnalyzer] = []

        self.ax.set_xlabel("Distance(m)")
        self.ax.set_ylabel("Speed(km/h)")
        self.ax.set_title("Select region to calculate Δt = t1 - t2")

        self.selected_index = -1

        self.cursor = None

        self.mouse_distance = 0

        self.selector = RectangleSelector(
            self.ax, self.on_select,
            useblit=True, interactive=True,
            button=[1], minspanx=5, minspany=5, spancoords='pixels'
        )
        
        self.mpl_connect('pick_event', self.on_pick)
        self.mpl_connect("scroll_event", self.on_scroll)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.press_ctrl = False
        self._analyzer_update_cb = []

    # 直接读取x坐标，使拖动更平滑
    def on_mouse_move(self, event):
        if event.inaxes != self.ax:  # 确保鼠标在目标坐标轴内
            return
        self.mouse_distance = event.xdata
    
    """func(instance,i)"""
    def register_instance_on_hover(self, func, i):
        self._analyzer_update_cb[i] = func
        
    def add_instance_by_df(self, name, data_frame)-> SDAnalyzer:
        analyzer = SDAnalyzer(self.ax, name=name, data_frame=data_frame)
        return self.__add_instance(analyzer)
    
    def add_instance_by_file(self, file) -> SDAnalyzer:
        analyzer = SDAnalyzer(self.ax, speed_distance_path=file)
        return self.__add_instance(analyzer)
    
    def __add_instance(self, analyzer) -> SDAnalyzer:
        self.analyzers.append(analyzer)
        self._analyzer_update_cb.append(None)
        max_distance = max(i.df['distance'].max() for i in self.analyzers)
        self.ax.set_xlim(0, max_distance)
        
        if self.cursor is not None:
            self.cursor.remove()

        self.cursor = mplcursors.cursor([i.line for i in self.analyzers], hover=mplcursors.HoverMode.Transient)
        @self.cursor.connect("add")
        def on_hover(sel):            
            distance = self.mouse_distance
            for index,instance in enumerate(self.analyzers):
                instance.set_current_index_by_distance(distance)
                instance.draw_point(distance)
                if self._analyzer_update_cb[index] is not None:
                    self._analyzer_update_cb[index](instance, index)
            
            annotation_text = \
                f'distance: {distance:.2f}m\n' + '\n'.join(f" V{i}: {item.get_speed(distance):.2f}km/h, a: {item.get_current_accel()/ 9.8:.2f}" for i, item in enumerate(self.analyzers))

            sel.annotation.set_text(annotation_text)
            sel.annotation.get_bbox_patch().set(fc="#4f4f4f", alpha=0.6)
            # sel.annotation.get_bbox_patch().set_edgecolor(line.get_color())
            sel.annotation.set_color("white")
            sel.annotation.set_fontsize(9)
            sel.annotation.arrow_patch.set(arrowstyle="-", alpha=.5)

        self.ax.legend()
        return analyzer
    
    def on_pick(self, event):
        lines = [i.line for i in self.analyzers]
        if event.artist in lines:
            self.selected_index = lines.index(event.artist)

    def update_plot(self):
        self.fig.canvas.draw_idle()
        
    def on_scroll(self, event):
        ctrl_pressed = self.press_ctrl
        if not ctrl_pressed:
            return

        base_scale = 1.2
        xdata = event.xdata
        ydata = event.ydata
        if xdata is None or ydata is None:
            return

        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        if event.button == "up":
            scale_factor = 1 / base_scale
        elif event.button == "down":
            scale_factor = base_scale
        else:
            print("no")
            scale_factor = 1.0

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        relx = (xdata - cur_xlim[0]) / (cur_xlim[1] - cur_xlim[0])
        rely = (ydata - cur_ylim[0]) / (cur_ylim[1] - cur_ylim[0])

        self.ax.set_xlim(xdata - relx * new_width, xdata + (1 - relx) * new_width)
        self.ax.set_ylim(ydata - rely * new_height, ydata + (1 - rely) * new_height)
        self.draw_idle()
    
    def exit_editor(self, df):
        self.analyzers[0].df = regen_df_by_time_speed(df)
        self.analyzers[0].adjust_distance(0)
        self.draw_idle()
        
    def on_select(self, eclick, erelease):
        if len(self.analyzers) > 2:
            return
        
        x1 = min(eclick.xdata, erelease.xdata)
        x2 = max(eclick.xdata, erelease.xdata)
        # 删除太靠近的时间标签，防止看不清
        for t in self.delta_texts:
            x_text, _ = t.get_position()
            new_position = (x1 + x2) / 2
            if -500 < new_position - x_text < 500:
                t.remove()
                self.delta_texts.remove(t)

        if len(self.analyzers) == 1:
            df = self.analyzers[0].df
            x_shifted = df['distance'].values
            mask = (x_shifted >= x1) & (x_shifted <= x2)
            selected_idx = df.index[mask].tolist()
        
            self.editor = DataEditor(
                df,
                x_name="distance",
                y_name="speed",
                index_list=selected_idx,
                save_callback=self.exit_editor
            )
            self.editor.show()
            return
        
        def get_segment(df):
            x_shifted = df['distance'].values
            y = df['speed'].values
            mask = (x_shifted >= x1) & (x_shifted <= x2)
            return x_shifted[mask], y[mask]

        x1_seg, y1_seg = get_segment(self.analyzers[0].df)
        x2_seg, y2_seg = get_segment(self.analyzers[1].df)

        if len(x1_seg) < 2 or len(x2_seg) < 2:
            print("Not enough data in selection.")
            return
        
        def compute_time(x, v):
            v = v * 1000 / 3600  # km/h → m/s
            v[v <= 0] = np.nan
            dx = np.diff(x)
            v_avg = (v[:-1] + v[1:]) / 2
            dt = dx / v_avg
            return np.nansum(dt)
        
        t1 = compute_time(x1_seg, y1_seg)
        t2 = compute_time(x2_seg, y2_seg)
        delta_t = t1 - t2

        print(f"dt = t1 - t2 = {t1:.3f} - {t2:.3f} = {delta_t:.3f} s")
        txt = self.ax.text((x1 + x2) / 2, self.ax.get_ylim()[1]*0.9,
                    f"Δt = {delta_t:.3f} s",
                    ha='center', color='purple', fontsize=10,
                    bbox=dict(facecolor='white', alpha=0.6))
        self.delta_texts.append(txt)
        self.fig.canvas.draw_idle()