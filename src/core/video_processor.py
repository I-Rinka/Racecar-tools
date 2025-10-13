import cv2
import numpy as np
import matplotlib.pyplot as plt
import easyocr
import csv
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:/Users/I_Rin\AppData/Local/Programs/Tesseract-OCR/tesseract.exe"
import re
import math
import pandas as pd

reader = None

easy_err_number = [140.0, 151.0, 165.0, 244.0, 247.0]
# 24 -> 244, 247 -> 2417
# easy_err_number = [65, 75, 85, 95, 105, 115, 125, 135, 145, 150, 155, 165, 168, 175, 180, 185, 189, 205, 250, 255, 270, 280, 290]

def get_number(display_frame, on_err_cb = None):
    global reader
    if reader is None:
        reader = easyocr.Reader(['ch_sim'], gpu=True)
    
    result = reader.readtext(display_frame, allowlist = '0123456789')
    if len(result) < 1:
        if on_err_cb is not None:
            on_err_cb()
        return 0
    
    _, txt, _ = result[0]
   
    if not txt.isdigit():
        if on_err_cb is not None:
            on_err_cb()
        return 0
    
    number = int(txt, 10)

    return number

def get_number_float(display_frame, on_err_cb = None):
    custom_config = r'--oem 3 --psm 6 outputbase digits'
    text = pytesseract.image_to_string(display_frame, config=custom_config)
    clean_text = re.sub(r'[^0-9.]', '', text)
    value = 0.0
    
    try:
        value = float(clean_text)
    except ValueError:
        if on_err_cb is not None:
            on_err_cb()
        value = 0.0
        
    return value

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

def get_accel(speeds:list, distance:list, window = 5):
    res = []
    for i in range(len(speeds)):
        dv_dx = local_slope(distance, speeds, i, window=window)
        v0 = speeds[i]
        a = v0 * dv_dx * 25 / 324
        res.append(a)
    return res

def regen_df_by_time_speed(df: pd.DataFrame):
    df = df.dropna(how='any')
    distance = [0]
    for i in range(1, len(df)):
        t0, v0 = df["time"].iloc[i - 1], df["speed"].iloc[i - 1]
        t1, v1 = df["time"].iloc[i], df["speed"].iloc[i]
        v0_mps = v0 / 3.6
        v1_mps = v1 / 3.6
        delta_t = t1 - t0
        s = distance[-1] + ((v0_mps + v1_mps) / 2) * delta_t
        distance.append(s)
    df["distance"] = distance
    df["accel"] = get_accel(df["speed"].values, df["distance"].values)
    return df

class TimeSpeedProcessor():
    """docstring for TimeSpeed."""
    def __init__(self, frame_rate):
        self.index = 0
        self.time_interval = 1.0 / frame_rate
        self.time_speed = []
        self.ez_ocr_able_to_process = True
        self.last_speed = -1
        self.df = None
        
    def process_frame(self, frame: cv2.Mat, frame_index = -1):
        number = get_number_float(frame, None)
        print(number)
        self.time_speed.append((self.index * self.time_interval, number, frame_index))
        self.index += 1
        return number
            
    def get_df_data(self):
        distance = [0]  # 初始距离为0
        for i in range(1, len(self.time_speed)):
            t0, v0, _ = self.time_speed[i - 1]
            t1, v1, _ = self.time_speed[i]
            v0_mps = v0 / 3.6
            v1_mps = v1 / 3.6
            delta_t = t1 - t0
            s = distance[-1] + ((v0_mps + v1_mps) / 2) * delta_t
            distance.append(s)

        data = {
            "frame": [self.time_speed[i][2] for i in range(len(self.time_speed))],
            "speed": [self.time_speed[i][1] for i in range(len(self.time_speed))],
            "distance": distance,
            "time": [self.time_speed[i][0] for i in range(len(self.time_speed))],
            "accel": get_accel([self.time_speed[i][1] for i in range(len(self.time_speed))], distance)
        }
        
        self.df = pd.DataFrame(data)
        return self.df
    
    def write_csv(self, name="speed_distance.csv"):
        if self.df is None:
            self.get_df_data()
        
        self.df.to_csv(name, index=False, encoding="utf-8-sig")
            
    def restart(self):
        self.index = 0
        self.ez_ocr_able_to_process = True
        self.time_speed.clear()
        
    def get_result(self):
        return self.time_speed
    
