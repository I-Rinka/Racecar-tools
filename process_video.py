import cv2
import numpy as np
import matplotlib.pyplot as plt
import easyocr
import csv
import pytesseract
import re
import math

# === 参数设置 ===
video_path = r"u9x.mp4"

instance_name = video_path.replace(".mp4", "")

max_display_width = 960  # 主窗口最大宽度
pytesseract.pytesseract.tesseract_cmd = r"C:/Users/I_Rin\AppData/Local/Programs/Tesseract-OCR/tesseract.exe"
cap = cv2.VideoCapture(video_path)
visualize = False

video_frame_rate = cap.get(cv2.CAP_PROP_FPS)
video_frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
video_per_frame_seconds = 1 / video_frame_rate
paused = False
roi_selected = False
roi = None
frame_idx = 0
first_index = 0
time_speed = []
frame_idxs = []

cv2.namedWindow("Video")

def resize_frame(frame, max_width):
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / w
        return cv2.resize(frame, (int(w * scale), int(h * scale))), scale
    return frame.copy(), 1.0

def show_frame(frame):
    display_frame = frame.copy()
    resized_display, _ = resize_frame(display_frame, max_display_width)
    cv2.imshow("Video", resized_display)

reader = easyocr.Reader(['ch_sim'],gpu=True)

def get_number(display_frame):
    result = reader.readtext(display_frame, allowlist = '0123456789')
    if len(result) < 1:
        return 0
    
    _, txt, _ = result[0]
   
    if not txt.isdigit():
        return 0
    
    number = int(txt, 10)
    if len(time_speed) > 0:
        last_speed =  time_speed[-1][1]
        if math.fabs(number - last_speed) > 50:
            array = [65, 115, 155, 105, 205, 150, 250, 135, 165]
            number = min(array, key=lambda v: abs(v - last_speed))
        
    return number # NOTE txt可以识别小数点，但是这里把他强制转换为整型了


def get_number_float(display_frame):
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.'
    text = pytesseract.image_to_string(display_frame, config=custom_config)
    clean_text = re.sub(r'[^0-9.]', '', text)
    value = 0.0
    
    try:
        value = float(clean_text)
    except ValueError:
        value = 0.0
        
    return value


def process_selected_frame(display_frame):
    global first_index
    first_index += 1
    if visualize:
        show_frame(display_frame)
    number = get_number(display_frame)
    print("Rec frame: {},{}, {}".format(float(first_index) / video_frame_rate, number,frame_idx))
    
    time_speed.append((float(first_index) / video_frame_rate, number))
    
    
while cap.isOpened():
    if not paused:
        frame_idx += 1
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()

        if not ret:
            print("Finished")
            break

    if roi_selected:
        x, y, w, h = roi
        display_frame = frame.copy()[y:y+h, x:x+w]
        process_selected_frame(display_frame)
        frame_idxs.append(frame_idx)
        
    else:
        show_frame(frame)
    key = cv2.waitKeyEx(30)

    if key == 27:  # ESC
        break
    elif key == 0x250000:
        frame_idx = max(0, frame_idx - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        show_frame(frame)
        
    elif key == 0x270000:
        frame_idx = min(video_frame_count, frame_idx + 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        show_frame(frame)
        
    elif key == 32:  # Space -> 暂停/播放
        paused = not paused

    elif key == ord('s'):
        roi_frame_resized, scale = resize_frame(frame, max_display_width)
        roi_scaled = cv2.selectROI("Video", roi_frame_resized, fromCenter=False, showCrosshair=True)
        if roi_scaled != (0, 0, 0, 0):
            # 反缩放得到原图上的 ROI
            x, y, w, h = roi_scaled
            x = int(x / scale)
            y = int(y / scale)
            w = int(w / scale)
            h = int(h / scale)
            roi = (x, y, w, h)
            roi_selected = True
            paused = False
            cv2.destroyWindow("Video")
        # 缩放原图用于 ROI 选择
                

cap.release()
cv2.destroyAllWindows()

if visualize:
    # 拆分成 x（时间） 和 y（速度）
    x = np.array([point[0] for point in time_speed])
    y = np.array([point[1] for point in time_speed])
    # y_smooth = spline(x_new)

    plt.figure(figsize=(10, 5))
    plt.plot(x, y, label='speed', color='blue')

    # 使用时传入 fontproperties 参数
    plt.title("speed-time")
    plt.xlabel("time")
    plt.ylabel("speed")

    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


distance = [0]  # 初始距离为0
for i in range(1, len(time_speed)):
    t0, v0 = time_speed[i - 1]
    t1, v1 = time_speed[i]
    v0_mps = v0 / 3.6
    v1_mps = v1 / 3.6
    delta_t = t1 - t0
    s = distance[-1] + ((v0_mps + v1_mps) / 2) * delta_t
    distance.append(s)

if visualize:
    plt.figure(figsize=(10, 5))
    plt.plot(distance, y, label='speed-distance', color='blue')

    plt.title("speed-distance")
    plt.xlabel("distance(m)")
    plt.ylabel("speed(km/h)")

    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

# 准备输出数据（距离 m，速度 km/h）
output_data = [(round(distance[i], 3), time_speed[i][1], frame_idxs[i]) for i in range(len(time_speed))]

time_speed_data = [(time_speed[i][0], time_speed[i][1], frame_idxs[i]) for i in range(len(time_speed))]

with open(f'time_speed_{instance_name}.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['time', 'speed', 'frame'])
    writer.writerows(time_speed)

# 输出到 CSV 文件
with open(f'distance_speed_{instance_name}.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['distance', 'speed', 'frame'])
    writer.writerows(output_data)
