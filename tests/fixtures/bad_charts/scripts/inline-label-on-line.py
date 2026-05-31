import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5.5))
ax.plot([2021, 2022, 2023], [20, 40, 60])
fig.patches.append(mpatches.Rectangle((0, 0.96), 1, 0.04, transform=fig.transFigure))
fig.text(0.08, 0.90, "Inline label on line", fontsize=16)
ax.annotate("Series A", xy=(2022, 40), xytext=(0, 0), textcoords="offset points")
fig.text(0.08, 0.03, "Source: test", fontsize=8)
