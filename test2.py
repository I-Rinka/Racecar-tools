import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


df1 = pd.read_csv('distance_speed_u9x.csv')
df2 = pd.read_csv('distance_speed_su7u.csv')

original_data = [df1.copy(), df2.copy()]
offsets = [0.0, 0.0]
selected_index = [0]
delta_texts = []

# 初始化图形
fig, ax = plt.subplots()
line1, = ax.plot(df1['distance'], df1['speed'], label='U9X', lw=1, picker=True)
line2, = ax.plot(df2['distance'], df2['speed'], label='SU7U', lw=1, picker=True)
lines = [line1, line2]

# ===== 辅助：局部线性拟合估计 dv/dx =====
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

# ===== 绘图初始化 =====
ax.set_xlabel("Distance")
ax.set_ylabel("Speed")
ax.set_title("Hover: combined tooltip for two curves (show tangent & acceleration)")
ax.grid(True)
ax.legend()

# 每条线对应的动态元素（不含注释，注释用一个共享的 annot）
dynamic_artists = {
    line1: {"dot": None, "tangent": None, "df": df1},
    line2: {"dot": None, "tangent": None, "df": df2},
}

# 共享的单个注释（tooltip），初始化为不可见
shared_annot = ax.annotate(
    "",
    xy=(0, 0),
    xytext=(15, 15),
    textcoords="offset points",
    bbox=dict(boxstyle="round,pad=0.4", fc="w", alpha=0.95),
    arrowprops=dict(arrowstyle="->"),
    zorder=10,
)
shared_annot.set_visible(False)

# 触发阈值：以总距离长度的比例定义（可调）
xmin = min(df1["distance"].min(), df2["distance"].min())
xmax = max(df1["distance"].max(), df2["distance"].max())
x_pick_thresh = (xmax - xmin) * 0.01  # 1% 的距离范围作为“靠近”

def hide_artists_for_line(artists):
    """隐藏某条线的点和切线（但不删除对象，以便重用）"""
    if artists["dot"] is not None:
        try:
            artists["dot"].set_data([], [])
            artists["dot"].set_visible(False)
        except Exception:
            pass
    if artists["tangent"] is not None:
        try:
            artists["tangent"].set_data([], [])
            artists["tangent"].set_visible(False)
        except Exception:
            pass

def show_tangent_and_dot_for_line(line, artists, idx, seg_frac=0.05, window=6):
    """在索引 idx 处为指定的 line 绘制点和切线（并返回文本信息）"""
    df = artists["df"]
    x = df["distance"].values
    y = df["speed"].values
    x0 = x[idx]
    v0 = y[idx]
    dv_dx = local_slope(x, y, idx, window=window)
    a = v0 * dv_dx * 25 / 324 / 9.8

    color = line.get_color()

    # 切线段长度：使用当前坐标轴范围的比例，这样缩放后切线长度也合理
    xlim = ax.get_xlim()
    seg_half_len = (xlim[1] - xlim[0]) * seg_frac
    x_seg = np.array([x0 - seg_half_len, x0 + seg_half_len])
    y_seg = v0 + dv_dx * (x_seg - x0)

    # 点
    if artists["dot"] is None:
        artists["dot"], = ax.plot([x0], [v0], marker="o", markersize=0.5, alpha=0.8, color=color, zorder=8)
    else:
        artists["dot"].set_data([x0], [v0])
        artists["dot"].set_visible(True)

    # 切线
    if artists["tangent"] is None:
        artists["tangent"], = ax.plot(x_seg, y_seg, linestyle="--", lw=1, alpha=0.8, color=color, zorder=7)
    else:
        artists["tangent"].set_data(x_seg, y_seg)
        artists["tangent"].set_visible(True)

    label = line.get_label()
    text = f"{label}: x={x0:.2f}, v={v0:.2f}, a={a:.4f}g"
    return text

def on_motion(event):
    if event.inaxes != ax:
        # 鼠标不在轴上：隐藏所有动态元素与注释
        for ln, arts in dynamic_artists.items():
            hide_artists_for_line(arts)
        shared_annot.set_visible(False)
        fig.canvas.draw_idle()
        return

    if event.xdata is None or event.ydata is None:
        return

    mx = event.xdata

    # 收集靠近的线和对应文本
    texts = []
    any_visible = False

    for ln, arts in dynamic_artists.items():
        df = arts["df"]
        x = df["distance"].values
        y = df["speed"].values

        # 找最近点
        idx = np.searchsorted(x, mx)
        idx = np.clip(idx, 0, len(x)-1)
        if idx > 0 and abs(x[idx-1] - mx) < abs(x[idx] - mx):
            idx = idx - 1

        # 如果离得太远则隐藏该线的动态元素
        if abs(x[idx] - mx) > x_pick_thresh:
            hide_artists_for_line(arts)
            continue

        # 否则显示该线的点和切线，并把文本加入合并注释
        txt = show_tangent_and_dot_for_line(ln, arts, idx)
        texts.append(txt)
        any_visible = True

    if any_visible:
        # 将多个信息合并到一个注释框（换行分隔）
        combined_text = "\n".join(texts)
        # 放置注释到鼠标位置（使用数据坐标作为箭头位置）
        shared_annot.xy = (event.xdata, event.ydata)
        shared_annot.set_text(combined_text)
        shared_annot.set_visible(True)
    else:
        shared_annot.set_visible(False)

    fig.canvas.draw_idle()

def on_axes_leave(event):
    # 鼠标离开 axes -> 隐藏所有
    for ln, arts in dynamic_artists.items():
        hide_artists_for_line(arts)
    shared_annot.set_visible(False)
    fig.canvas.draw_idle()

# ===== Ctrl + 滚轮 缩放（同之前实现） =====
def on_scroll(event):
    key = getattr(event, "key", "")
    ctrl_pressed = ("control" in str(key).lower()) or ("ctrl" in str(key).lower())
    if not ctrl_pressed:
        return

    base_scale = 1.2
    xdata = event.xdata
    ydata = event.ydata
    if xdata is None or ydata is None:
        return

    cur_xlim = ax.get_xlim()
    cur_ylim = ax.get_ylim()
    if event.button == "up":
        scale_factor = 1 / base_scale
    elif event.button == "down":
        scale_factor = base_scale
    else:
        scale_factor = 1.0

    new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
    new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
    relx = (xdata - cur_xlim[0]) / (cur_xlim[1] - cur_xlim[0])
    rely = (ydata - cur_ylim[0]) / (cur_ylim[1] - cur_ylim[0])

    ax.set_xlim(xdata - relx * new_width, xdata + (1 - relx) * new_width)
    ax.set_ylim(ydata - rely * new_height, ydata + (1 - rely) * new_height)
    fig.canvas.draw_idle()

# ===== 事件绑定 =====
fig.canvas.mpl_connect("motion_notify_event", on_motion)
fig.canvas.mpl_connect("axes_leave_event", on_axes_leave)
fig.canvas.mpl_connect("scroll_event", on_scroll)

plt.show()
