import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5.5))
ax.plot([2021, 2022, 2023], [20, 40, 60])
fig.patches.append(mpatches.Rectangle((0, 0.96), 1, 0.04, transform=fig.transFigure))
fig.text(0.08, 0.90, "Clipped label", fontsize=16)
fig.text(1.02, 0.50, "This label is clipped", fontsize=10)
fig.text(0.08, 0.03, "Source: test", fontsize=8)
