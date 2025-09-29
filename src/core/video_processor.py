import cv2
import numpy as np
import matplotlib.pyplot as plt
import easyocr
import csv
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:/Users/I_Rin\AppData/Local/Programs/Tesseract-OCR/tesseract.exe"
import re
import math

video_path = r"u9x.mp4"
instance_name = video_path.replace(".mp4", "")
reader = easyocr.Reader(['ch_sim'], gpu=True)

easy_err_number = [65, 105, 115, 125, 135, 150, 155, 165, 205, 250, 255]

def get_number(display_frame, on_err_cb = None):
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
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.'
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

class TimeSpeedProcessor():
    """docstring for TimeSpeed."""
    def __init__(self, frame_rate):
        self.index = 0
        self.time_interval = 1.0 / frame_rate
        self.time_speed = []
        self.ez_ocr_able_to_process = True
        self.last_speed = -1
    
    def process_frame(self, frame: cv2.Mat):
        def func_err_cb1():
            print("Int data not work data")
            
            self.ez_ocr_able_to_process = False
        
        def func_err_cb2():
            print("Can't recognize the data")
        
        if self.ez_ocr_able_to_process == True:
            number = get_number(frame, func_err_cb1)
            
        if self.ez_ocr_able_to_process == False:
            number = get_number_float(frame, func_err_cb2)
        
        if self.last_speed > 0 and math.fabs(number - self.last_speed) > 50:
            print(f"origin number: {number}")
            array = [65, 115, 155, 105, 205, 150, 250, 135, 165]
            number = min(array, key=lambda v: abs(v - self.last_speed))
    
        self.last_speed = number
        self.time_speed.append((self.index * self.time_interval, number))
        self.index += 1
        return number

    def restart(self):
        self.index = 0
        self.time_speed.clear()
        
    def get_result(self):
        return self.time_speed
    
