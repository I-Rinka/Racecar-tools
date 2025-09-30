import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from sortedcontainers import SortedDict
import numpy as np

import os

def extract_name_without_extension(path):
    base = os.path.basename(path)
    name,_ = os.path.splitext(base)
    return name

def local_slope(x_arr, y_arr, idx, window=5):
    n = len(x_arr)
    i0 = max(0, idx - window)
    i1 = min(n - 1, idx + window)
    xs = x_arr[i0:i1+1]
    ys = y_arr[i0:i1+1]
    if len(xs) < 2:
        return 0.0
    A = np.vstack([xs, np.ones_like(xs)]).T
    slope, _ = np.linalg.lstsq(A, ys, rcond=None)[0]
    return slope

class SDAnalyzer():
    def __init__(self, axes:Axes, speed_distance_path=None, name: str=None, data_frame: pd.DataFrame = None):
        if data_frame is not None:
            self.df = data_frame
        else:
            self.df = pd.read_csv(speed_distance_path)
        
        if name is None:
            name = extract_name_without_extension(speed_distance_path)

        self.name = name
        self.ax = axes

        self.initial_frame = self.df['frame'][0]

        self.line, = self.ax.plot(self.df['distance'], self.df['speed'], label=name, picker=True)
        self.point = None
        self.vert_line = None

        self.build_sd()
        self.current_index = 0

    """rebuild sd after adjust distance"""
    def build_sd(self):
        self._sd = SortedDict()
        for i,distance in enumerate(self.df['distance']):
            if self._sd.get(distance) is None:
                self._sd[distance] = i 

    def adjust_distance(self, step):
        self.df['distance'] = self.df['distance'] + step
        self.line.set_data(self.df['distance'], self.df['speed'])
        self.build_sd()
        
    def draw_point(self, distance=-1):
        if self.point is None:
            self.point, = self.ax.plot([], [], 'o', markersize=6, alpha=0.6,
                                    markerfacecolor=self.line.get_color(),
                                    markeredgecolor='white',
                                    markeredgewidth=1)
        if distance == -1:
            self.point.set_data([self.df["distance"][self.current_index]], [self.df['speed'][self.current_index]])
            if self.vert_line is None:
                self.vert_line = self.ax.axvline(x=[self.df["distance"][self.current_index]], color="black", linewidth=0.5, alpha=0.8, linestyle='-')
            self.vert_line.set_xdata([self.df["distance"][self.current_index]])
        else:
            if self.vert_line is not None:
                self.vert_line.remove()
                self.vert_line = None

        index = self.get_index(distance)
        if index:
            self.point.set_data([distance], [self.df['speed'][index]])
    
    def get_speed(self, distance:float):
        index = self.get_index(distance)
        if index and self.df.get('speed') is not None:
            return self.df['speed'][index]
        return 0

    def get_frame_index(self, distance:float):
        index = self.get_index(distance)
        if index and self.df.get('frame') is not None:
            return self.df['frame'][index]
        return 0
    
    def get_current_frame_index(self):
        return self.df["frame"][self.current_index]

    def set_current_index_by_distance(self, distance:float):
        idx = self.get_index(distance)
        self.current_index = idx if idx is not None else 0
        return self.df['distance'][idx]
    
    def inc_current_index(self):
        self.current_index = self.current_index + 1

    def get_current_accel(self, window = 5):
        speeds = self.df["speed"].values
        dv_dx = local_slope(self.df["distance"].values, speeds, self.current_index, window=window)
        v0 = speeds[self.current_index]
        return v0 * dv_dx * 25 / 324
        
    def get_initial_frame(self) -> int:
        return self.initial_frame

    def get_accel(self, distance:float):
        index = self.get_index(distance)
        if index and self.df.get('acceleration') is not None:
            return self.df['acceleration'][index]
        return 0

    def get_index(self, distance:float):
        keys = self._sd.keys()
        index = self._sd.bisect_left(distance)
        candidates = []

        if index < len(keys):
            candidates.append(keys[index])
        if index < len(keys) - 1:
            candidates.append(keys[index + 1])
        if index > 0:
            candidates.append(keys[index - 1])

        if not candidates:
            return None

        closest_key = min(candidates, key=lambda k: abs(k - distance))
        return self._sd[closest_key]