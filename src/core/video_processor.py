import cv2
import numpy as np
import pytesseract
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.digit_recognizer import (
    DigitTemplateCache, learn_from_ocr_result, recognize_by_template
)

_digit_cache = DigitTemplateCache()

SPEED_MIN = 0.0
SPEED_MAX = 500.0
MAX_DELTA = 50.0


def get_number_float(display_frame, on_err_cb=None):
    custom_config = r'--oem 3 --psm 6 outputbase digits'
    text = pytesseract.image_to_string(display_frame, config=custom_config)
    clean_text = re.sub(r'[^0-9.]', '', text)
    try:
        value = float(clean_text)
    except ValueError:
        if on_err_cb is not None:
            on_err_cb()
        value = 0.0
    return value


def _sanity_check(value: float, last_speed: float) -> bool:
    if value < SPEED_MIN or value > SPEED_MAX:
        return False
    if last_speed >= 0 and abs(value - last_speed) > MAX_DELTA:
        return False
    return True


def smart_ocr(frame: np.ndarray, last_speed: float = -1.0) -> float:
    global _digit_cache

    value = get_number_float(frame)
    if value > 0 and _sanity_check(value, last_speed):
        learn_from_ocr_result(_digit_cache, frame, int(round(value)))
        return value

    tmpl_value, score = recognize_by_template(_digit_cache, frame)
    if score > 0.5 and _sanity_check(tmpl_value, last_speed):
        return tmpl_value

    if value > 0:
        return value
    return tmpl_value


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


def get_accel(speeds: list, distance: list, window=5):
    res = []
    for i in range(len(speeds)):
        dv_dx = local_slope(distance, speeds, i, window=window)
        v0 = speeds[i]
        a = v0 * dv_dx * 25 / 324
        res.append(a)
    return res


def regen_df_by_time_speed(df: pd.DataFrame):
    if "time" not in df:
        return df
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


def _process_single(frame, frame_index, time_val, last_speed):
    speed = smart_ocr(frame, last_speed)
    return frame_index, time_val, speed


class TimeSpeedProcessor:
    def __init__(self, frame_rate, max_workers=4):
        self.time_interval = 1.0 / frame_rate
        self.time_speed = []
        self.last_speed = -1.0
        self.df = None
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    def process_frame(self, frame: cv2.Mat, frame_index=-1):
        idx = len(self.time_speed)
        number = smart_ocr(frame, self.last_speed)
        print(number)
        self.time_speed.append((idx * self.time_interval, number, frame_index))
        if number > 0:
            self.last_speed = number
        return number

    def process_batch(self, frames: list[tuple[np.ndarray, int]]):
        base_idx = len(self.time_speed)
        futures = {}
        for offset, (frame, frame_index) in enumerate(frames):
            t = (base_idx + offset) * self.time_interval
            fut = self.pool.submit(_process_single, frame, frame_index, t, self.last_speed)
            futures[fut] = offset

        results = [None] * len(frames)
        for fut in as_completed(futures):
            offset = futures[fut]
            results[offset] = fut.result()

        for frame_index, time_val, speed in results:
            self.time_speed.append((time_val, speed, frame_index))
            if speed > 0:
                self.last_speed = speed

        return results

    def get_df_data(self):
        distance = [0]
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
            "accel": get_accel(
                [self.time_speed[i][1] for i in range(len(self.time_speed))],
                distance
            )
        }
        self.df = pd.DataFrame(data)
        return self.df

    def write_csv(self, name="speed_distance.csv"):
        if self.df is None:
            self.get_df_data()
        self.df.to_csv(name, index=False, encoding="utf-8-sig")

    def restart(self):
        self.last_speed = -1.0
        self.time_speed.clear()

    def get_result(self):
        return self.time_speed

    def shutdown(self):
        self.pool.shutdown(wait=False)
