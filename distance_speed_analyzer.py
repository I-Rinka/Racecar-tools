import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import RectangleSelector
import mplcursors

df1 = pd.read_csv('distance_speed_u9.csv')
df2 = pd.read_csv('distance_speed_su7.csv')

original_data = [df1.copy(), df2.copy()]
offsets = [0.0, 0.0]
selected_index = [0]
delta_texts = []

# 初始化图形
fig, ax = plt.subplots()
line1, = ax.plot(df1['distance'], df1['speed'], label='Curve 1', picker=True)
line2, = ax.plot(df2['distance'], df2['speed'], label='Curve 2', picker=True)
lines = [line1, line2]

ax.set_xlim(min(df1['distance'].min(), df2['distance'].min()),
            max(df1['distance'].max(), df2['distance'].max()))
ax.set_xlabel("Distance (m)")
ax.set_ylabel("Speed (km/h)")
ax.set_title("Select region to calculate Δt = t1 - t2")
ax.legend()

def update_plot():
    for i in [0, 1]:
        x = original_data[i]['distance'].values + offsets[i]
        y = original_data[i]['speed'].values
        lines[i].set_data(x, y)
    fig.canvas.draw_idle()

def on_pick(event):
    print("on pick")
    if event.artist in lines:
        selected_index[0] = lines.index(event.artist)
        print(f"Selected curve {selected_index[0]+1}")

def compute_time(x, v):
    v = v * 1000 / 3600  # km/h → m/s
    v[v <= 0] = np.nan
    dx = np.diff(x)
    v_avg = (v[:-1] + v[1:]) / 2
    dt = dx / v_avg
    return np.nansum(dt)

def on_select(eclick, erelease):
    x1 = min(eclick.xdata, erelease.xdata)
    x2 = max(eclick.xdata, erelease.xdata)
    # 删除太靠近的时间标签，防止看不清
    for t in delta_texts:
        x_text, _ = t.get_position()
        new_position = (x1 + x2) / 2
        if -500 < new_position - x_text < 500:
            t.remove()
            delta_texts.remove(t)

    def get_segment(df, offset):
        x_shifted = df['distance'].values + offset
        y = df['speed'].values
        mask = (x_shifted >= x1) & (x_shifted <= x2)
        return x_shifted[mask], y[mask]

    x1_seg, y1_seg = get_segment(original_data[0], offsets[0])
    x2_seg, y2_seg = get_segment(original_data[1], offsets[1])

    if len(x1_seg) < 2 or len(x2_seg) < 2:
        print("Not enough data in selection.")
        return

    t1 = compute_time(x1_seg, y1_seg)
    t2 = compute_time(x2_seg, y2_seg)
    delta_t = t1 - t2

    print(f"dt = t1 - t2 = {t1:.3f} - {t2:.3f} = {delta_t:.3f} s")
    txt = ax.text((x1 + x2) / 2, ax.get_ylim()[1]*0.9,
                  f"Δt = {delta_t:.3f} s",
                  ha='center', color='purple', fontsize=10,
                  bbox=dict(facecolor='white', alpha=0.6))
    delta_texts.append(txt)
    fig.canvas.draw_idle()



def on_key(event):
    step = 1
    idx = selected_index[0]
    if event.key == 'left':
        offsets[idx] -= step
        update_plot()
    elif event.key == 'right':
        offsets[idx] += step
        update_plot()
    elif event.key == 'escape':
        for txt in delta_texts:
            txt.remove()
        delta_texts.clear()
        fig.canvas.draw_idle()
        print("Cleared all time annotations")

for line in lines:
    cursor = mplcursors.cursor(line, hover=mplcursors.HoverMode.Transient)
    @cursor.connect("add")
    def on_add(sel, line=line):  # 绑定当前 line
        x, y = sel.target
        sel.annotation.set_text(f"x = {x:.2f} m\nv = {y:.2f} km/h")

        # 设置科技风格 + 曲线颜色匹配
        sel.annotation.get_bbox_patch().set(fc=line.get_color(), alpha=0.8)
        sel.annotation.get_bbox_patch().set_edgecolor(line.get_color())
        sel.annotation.set_color("white")
        sel.annotation.set_fontsize(9)
        sel.annotation.arrow_patch.set(arrowstyle="-", alpha=.5)
        
selector = RectangleSelector(ax, on_select,
                             useblit=False,
                             button=[1],
                             minspanx=5, minspany=5,
                             spancoords='pixels',
                             interactive=True)

# 事件绑定
fig.canvas.mpl_connect('pick_event', on_pick)
fig.canvas.mpl_connect('key_press_event', on_key)

plt.show()