import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

fig, ax = plt.subplots()

ax.plot([0, 10], [0, 10])

x1, x2 = 3, 7
ymin, ymax = ax.get_ylim()  # 获取 y 轴范围
rect = Rectangle((x1, ymin), x2 - x1, ymax - ymin,
                 color="blue", alpha=0.3)
ax.add_patch(rect)

plt.show()
