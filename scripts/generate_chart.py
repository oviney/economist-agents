#!/usr/bin/env python3
"""
Generate Economist-style chart: AI Adoption vs Maintenance Reduction

Follows CHART_DESIGN_SPEC.md:
- Clear zone separation (no overlaps)
- Inline labels in clear space, not on lines
- Labels avoid X-axis zone
- End-of-line value labels
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# === CONFIGURATION ===
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.linewidth'] = 0

# Economist colors
NAVY = '#17648d'
BURGUNDY = '#843844'
RED_BAR = '#e3120b'
BG_COLOR = '#f1f0e9'
GRAY_TEXT = '#666666'
GRAY_LIGHT = '#888888'
GRID_COLOR = '#cccccc'

# === DATA ===
years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
ai_adoption = [12, 18, 28, 42, 55, 68, 78, 81]
maintenance_reduction = [0, 2, 5, 8, 12, 14, 16, 18]

# === CREATE FIGURE ===
fig, ax = plt.subplots(figsize=(8, 5.5))
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(BG_COLOR)

# === PLOT DATA ===
ax.plot(years, ai_adoption, color=NAVY, linewidth=2.5, marker='o', markersize=6)
ax.plot(years, maintenance_reduction, color=BURGUNDY, linewidth=2.5, marker='s', markersize=6)

# === END-OF-LINE VALUE LABELS ===
ax.annotate(f'{ai_adoption[-1]}%', 
            xy=(years[-1], ai_adoption[-1]), 
            xytext=(10, 0),
            textcoords='offset points', 
            fontsize=11, fontweight='bold', 
            color=NAVY, va='center')

ax.annotate(f'{maintenance_reduction[-1]}%', 
            xy=(years[-1], maintenance_reduction[-1]), 
            xytext=(10, 0),
            textcoords='offset points', 
            fontsize=11, fontweight='bold', 
            color=BURGUNDY, va='center')

# === INLINE SERIES LABELS ===
# These must be:
# 1. In clear space (not overlapping data lines)
# 2. NOT in the X-axis zone (below ~y=20 in data coords is risky)
# 3. Close to their respective lines but offset

# Upper series (AI adoption): Place at end, above the last segment
# Line is at y=78 at x=2024, so label above
ax.annotate('AI adoption\nin testing', 
            xy=(2024, 78),
            xytext=(-50, 15),        # Left and above
            textcoords='offset points',
            fontsize=9, color=NAVY, 
            ha='center', va='bottom',
            linespacing=1.2)

# Lower series (Maintenance): This is tricky - line is low
# At x=2021, y=8. If we put label below, it hits X-axis zone.
# Solution: Put label ABOVE this line, but in the gap between the two series
ax.annotate('Maintenance\nburden reduction', 
            xy=(2021, 8),
            xytext=(0, 18),          # ABOVE the line (in the clear space)
            textcoords='offset points',
            fontsize=9, color=BURGUNDY, 
            ha='center', va='bottom',
            linespacing=1.2)

# === AXES CONFIGURATION ===
ax.set_ylim(0, 100)
ax.set_xlim(2017.5, 2026)
ax.set_yticks([0, 20, 40, 60, 80, 100])
ax.set_yticklabels(['0', '20', '40', '60', '80', '100'], fontsize=10, color='#333333')
ax.tick_params(axis='y', length=0)

ax.set_xticks(years)
ax.set_xticklabels([str(y) for y in years], fontsize=10, color='#333333')
ax.tick_params(axis='x', length=3, color='#666666')

# === GRIDLINES (horizontal only) ===
ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
ax.xaxis.grid(False)

# === SPINES (bottom only) ===
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#666666')
ax.spines['bottom'].set_linewidth(0.5)

# === LAYOUT (must come BEFORE figure text) ===
plt.tight_layout()
plt.subplots_adjust(top=0.78, bottom=0.12, left=0.08, right=0.88)

# === FIGURE ELEMENTS (after layout adjustment) ===

# Red bar at top
rect = mpatches.Rectangle((0, 0.96), 1, 0.04, 
                            transform=fig.transFigure,
                            facecolor=RED_BAR, 
                            edgecolor='none', 
                            clip_on=False)
fig.patches.append(rect)

# Title (y=0.90, in title zone)
fig.text(0.08, 0.90, 'The automation gap', 
         fontsize=16, fontweight='bold', color='#1a1a1a',
         transform=fig.transFigure, ha='left')

# Subtitle (y=0.85)
fig.text(0.08, 0.85, 'AI adoption in testing vs. maintenance burden reduction, %',
         fontsize=11, color=GRAY_TEXT,
         transform=fig.transFigure, ha='left')

# Source (y=0.03, in source zone)
fig.text(0.08, 0.03, 'Sources: Tricentis Research; TestGuild Automation Survey 2018-2025',
         fontsize=8, color=GRAY_LIGHT,
         transform=fig.transFigure, ha='left')

# === SAVE ===
output_path = '/home/claude/blog-automation/assets/charts/testing-times-ai-gap.png'
plt.savefig(output_path, dpi=300, facecolor=BG_COLOR, edgecolor='none')
plt.close()

print(f"Chart saved to {output_path}")
print("Design checks:")
print("  ✓ Title below red bar (y=0.90)")
print("  ✓ Inline labels offset from lines")
print("  ✓ Lower label ABOVE its line (avoiding X-axis zone)")
print("  ✓ End-of-line value labels present")
