import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5.5))
ax.plot([2021, 2022, 2023], [8, 10, 12])
fig.patches.append(mpatches.Rectangle((0, 0.96), 1, 0.04, transform=fig.transFigure))
fig.text(0.08, 0.90, "Inline label in X-axis zone", fontsize=16)
ax.annotate("Low series", xy=(2022, 8), xytext=(0, -25), textcoords="offset points")
fig.text(0.08, 0.03, "Source: test", fontsize=8)
