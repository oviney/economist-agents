import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5.5))
ax.plot([2021, 2022, 2023], [50, 60, 70])
ax.plot([2021, 2022, 2023], [52, 62, 72])
fig.patches.append(mpatches.Rectangle((0, 0.96), 1, 0.04, transform=fig.transFigure))
fig.text(0.08, 0.90, "Labels collide", fontsize=16)
ax.annotate("Series A", xy=(2022, 60), xytext=(0, 10), textcoords="offset points")
ax.annotate("Series B", xy=(2022, 62), xytext=(0, 10), textcoords="offset points")
fig.text(0.08, 0.03, "Source: test", fontsize=8)
