import cv2
import numpy as np
import matplotlib.pyplot as plt
import easyocr
import csv
import pytesseract
import re
import math

video_path = r"u9x.mp4"
instance_name = video_path.replace(".mp4", "")
pytesseract.pytesseract.tesseract_cmd = r"C:/Users/I_Rin\AppData/Local/Programs/Tesseract-OCR/tesseract.exe"
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

class ProcessVideo(object):
    """docstring for ProcessVideo."""
    def __init__(self, arg):
        super(ProcessVideo, self).__init__()
        
    

def handle_outstanding_number(cu):
    if len(time_speed) > 0:
        last_speed =  time_speed[-1][1]
        if math.fabs(number - last_speed) > 50:
            array = [65, 115, 155, 105, 205, 150, 250, 135, 165]
            number = min(array, key=lambda v: abs(v - last_speed))