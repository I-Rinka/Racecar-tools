import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import RectangleSelector
import csv
import mplcursors

file = 'time_speed_u9x.mp4.csv'
df = pd.read_csv(file)

times = df['time']
speed = df['speed']
distance = [0]  # 初始距离为0
for i in range(1, len(times)):
    t0, v0 = times[i - 1], speed[i-1]
    t1, v1 = times[i], speed[i]
    v0_mps = v0 / 3.6
    v1_mps = v1 / 3.6
    delta_t = t1 - t0
    s = distance[-1] + ((v0_mps + v1_mps) / 2) * delta_t
    distance.append(s)

output_data = [(round(distance[i], 3), df['speed'][i], df['frame'][i]) for i in range(len(times))]

new_file = file.replace("time", "distance")

plt.figure(figsize=(10, 5))
line, = plt.plot(distance, speed, label='speed-distance', color='blue')

plt.title("speed-distance")
plt.xlabel("distance(m)")
plt.ylabel("speed(km/h)")

cursor = mplcursors.cursor(line, hover=mplcursors.HoverMode.Transient)

@cursor.connect("add")
def on_add(sel):
    x, y = sel.target
    sel.annotation.set_text(f"distance = {x:.2f} m\nv1 = {y:.2f} km/h\n")

plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

with open(new_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['distance', 'speed', 'frame'])
    writer.writerows(output_data)
