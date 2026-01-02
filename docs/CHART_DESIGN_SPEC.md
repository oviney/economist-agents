# Economist Chart Design Specification

## Overview

This document codifies the visual design principles for Economist-style charts.
These rules are derived from The Economist's visual style guide and best practices
in data visualization.

## Core Principle

> "The viewer should learn the primary message of the chart after only a few seconds."

Every design decision should support this goal.

---

## 1. LAYOUT ZONES

The chart is divided into distinct zones with NO OVERLAP between them:

```
┌─────────────────────────────────────────────────────────────────┐
│ RED BAR (y: 0.96 - 1.00)                                        │
├─────────────────────────────────────────────────────────────────┤
│ TITLE ZONE (y: 0.88 - 0.94)                                     │
│   Title: y=0.90, bold, 16pt                                     │
│   Subtitle: y=0.85, gray, 11pt                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ CHART ZONE (y: 0.15 - 0.78)                                     │
│   - Data lines/bars                                             │
│   - Inline labels (positioned in CLEAR SPACE, not on lines)    │
│   - Horizontal gridlines only                                   │
│   - Y-axis labels (left side, on gridlines)                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ X-AXIS ZONE (y: 0.08 - 0.14)                                    │
│   - X-axis tick labels                                          │
│   - NO other elements should intrude here                       │
├─────────────────────────────────────────────────────────────────┤
│ SOURCE ZONE (y: 0.01 - 0.06)                                    │
│   Source attribution, 8pt gray                                  │
└─────────────────────────────────────────────────────────────────┘
```

### CRITICAL RULE: No element should cross zone boundaries

---

## 2. INLINE LABEL POSITIONING

Inline labels identify data series WITHOUT a legend box.

### Placement Rules

1. **Find clear space** — Labels go in empty areas of the chart, not on data
2. **Near but not on** — Labels should be close to their line but offset
3. **End of line preferred** — Place labels at the rightmost data point when possible
4. **Use data endpoint labels** — Bold value (e.g., "81%") at line terminus

### Offset Guidelines

For a line chart:
```python
# Label ABOVE a line (for upper series)
ax.annotate('Series Name',
            xy=(x_anchor, y_anchor),      # Point ON the line
            xytext=(0, 20),               # Offset UP in points
            textcoords='offset points',
            va='bottom')                  # Align bottom of text to offset point

# Label BELOW a line (for lower series)
ax.annotate('Series Name',
            xy=(x_anchor, y_anchor),
            xytext=(0, -20),              # Offset DOWN in points
            textcoords='offset points',
            va='top')                     # Align top of text to offset point

# Label at END of line (preferred when space allows)
ax.annotate('Series Name',
            xy=(last_x, last_y),
            xytext=(10, 0),               # Offset RIGHT
            textcoords='offset points',
            ha='left', va='center')
```

### What NOT To Do

❌ Place label directly on the line (overlapping)
❌ Place label in the X-axis zone
❌ Use a legend box (Economist style uses direct labeling)
❌ Let labels overlap each other

---

## 3. COLLISION AVOIDANCE

### Before Placing Any Label, Check:

1. **Does it overlap the data line?**
   - If yes: offset by at least 15 points vertically

2. **Does it overlap another label?**
   - If yes: move one label, use leader lines, or abbreviate

3. **Does it intrude into the X-axis zone?**
   - If yes: move label higher or use end-of-line position

4. **Does it intrude into the title zone?**
   - If yes: chart zone is too tall, reduce top margin

5. **Is it clipped by the chart boundary?**
   - If yes: adjust margins or move label inward

### Safe Positioning Algorithm

```python
def find_safe_label_position(line_y_values, x_position, label_height_pts=30):
    """
    Find a y-position for a label that doesn't overlap the line.

    Args:
        line_y_values: Array of y-values for the line
        x_position: X-coordinate where label will be placed
        label_height_pts: Approximate height of label in points

    Returns:
        (y_position, vertical_alignment)
    """
    y_at_x = interpolate_y_at_x(line_y_values, x_position)

    # Check space above vs below
    space_above = 100 - y_at_x  # Assuming y-axis 0-100
    space_below = y_at_x - 0

    if space_above > space_below:
        # Place above
        return (y_at_x, 20, 'bottom')  # offset up 20 points
    else:
        # Place below
        return (y_at_x, -20, 'top')    # offset down 20 points
```

---

## 4. X-AXIS ZONE PROTECTION

The X-axis zone (y: 0.08 - 0.14 in figure coordinates) is RESERVED for:
- X-axis tick labels (years, categories, etc.)
- X-axis line (if shown)

### Nothing Else Goes Here

❌ No inline series labels
❌ No annotations
❌ No data labels

### If a series label would intrude:
1. Move it to end-of-line position (right side of chart)
2. Move it higher in the chart zone
3. Use a shorter label

---

## 5. MULTI-SERIES SPACING

When multiple lines are close together, labels need extra care:

### Rule: Minimum 40pt Vertical Separation Between Labels

```python
# Check if labels would collide
label_1_y = 65  # in data coordinates
label_2_y = 58  # in data coordinates

# Convert to figure points (approximate)
pts_per_unit = fig_height_pts / (y_max - y_min)
separation_pts = abs(label_1_y - label_2_y) * pts_per_unit

if separation_pts < 40:
    # Labels too close - use alternative positioning
    # Option 1: Stagger horizontally
    # Option 2: Use end-of-line labels only
    # Option 3: Combine into single label with multiple lines
```

---

## 6. COLOR CODING

Labels should match the color of their data series:

```python
# Economist palette
COLORS = {
    'primary': '#17648d',    # Navy blue
    'secondary': '#843844',  # Burgundy
    'tertiary': '#51bec7',   # Teal
    'quaternary': '#d6ab63', # Gold
    'highlight': '#e3120b',  # Red (use sparingly)
}

# Label color matches line color
ax.plot(x, y1, color=COLORS['primary'])
ax.annotate('Series 1', ..., color=COLORS['primary'])

ax.plot(x, y2, color=COLORS['secondary'])
ax.annotate('Series 2', ..., color=COLORS['secondary'])
```

---

## 7. TYPOGRAPHY

### Font Sizes (in points)
- Title: 16pt, bold
- Subtitle: 11pt, regular, gray (#666666)
- Inline labels: 9pt, regular
- End-of-line values: 11pt, bold
- Axis labels: 10pt
- Source: 8pt, gray (#888888)

### Line Spacing
For multi-line labels, use `linespacing=1.2`

---

## 8. VALIDATION CHECKLIST

Before finalizing any chart, verify:

□ Red bar visible at top, not overlapping title
□ Title below red bar with clear gap
□ Subtitle below title
□ All inline labels in clear space (not on lines)
□ No labels in X-axis zone
□ No label-to-label overlap
□ End values visible and not clipped
□ Source line visible at bottom
□ Horizontal gridlines only
□ Y-axis starts at zero (unless justified)
□ No legend box (direct labeling only)

---

## 9. MATPLOTLIB IMPLEMENTATION

### Complete Template

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# === SETUP ===
fig, ax = plt.subplots(figsize=(8, 5.5))
fig.patch.set_facecolor('#f1f0e9')
ax.set_facecolor('#f1f0e9')

# === PLOT DATA ===
years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
series1 = [12, 18, 28, 42, 55, 68, 78, 81]
series2 = [0, 2, 5, 8, 12, 14, 16, 18]

ax.plot(years, series1, color='#17648d', linewidth=2.5, marker='o', markersize=6)
ax.plot(years, series2, color='#843844', linewidth=2.5, marker='s', markersize=6)

# === END-OF-LINE VALUES (preferred label style) ===
ax.annotate(f'{series1[-1]}%',
            xy=(years[-1], series1[-1]),
            xytext=(10, 0),
            textcoords='offset points',
            fontsize=11, fontweight='bold',
            color='#17648d', va='center')

ax.annotate(f'{series2[-1]}%',
            xy=(years[-1], series2[-1]),
            xytext=(10, 0),
            textcoords='offset points',
            fontsize=11, fontweight='bold',
            color='#843844', va='center')

# === INLINE LABELS (in clear space, offset from lines) ===
# Upper series: label ABOVE the line
ax.annotate('AI adoption\nin testing',
            xy=(2023, 68),
            xytext=(0, 20),          # 20 points ABOVE
            textcoords='offset points',
            fontsize=9, color='#17648d',
            ha='center', va='bottom',
            linespacing=1.2)

# Lower series: position carefully to avoid X-axis zone
# Since series2 is low (14 at 2023), place label to the RIGHT at endpoint
ax.annotate('Maintenance\nburden reduction',
            xy=(2021, 8),            # Earlier x to avoid crowding end
            xytext=(0, -25),         # Below, but check it doesn't hit x-axis
            textcoords='offset points',
            fontsize=9, color='#843844',
            ha='center', va='top',
            linespacing=1.2)

# === AXES ===
ax.set_ylim(0, 100)
ax.set_xlim(2017.5, 2026)

# Gridlines: horizontal only
ax.yaxis.grid(True, color='#cccccc', linewidth=0.5)
ax.xaxis.grid(False)

# Spines: only bottom
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#666666')
ax.spines['bottom'].set_linewidth(0.5)

# Y-axis ticks
ax.set_yticks([0, 20, 40, 60, 80, 100])
ax.tick_params(axis='y', length=0)

# X-axis ticks
ax.set_xticks(years)
ax.tick_params(axis='x', length=3, color='#666666')

# === LAYOUT (do this BEFORE adding figure text) ===
plt.tight_layout()
plt.subplots_adjust(top=0.78, bottom=0.15, left=0.10, right=0.88)

# === FIGURE ELEMENTS (after layout) ===
# Red bar
rect = mpatches.Rectangle((0, 0.96), 1, 0.04,
                            transform=fig.transFigure,
                            facecolor='#e3120b',
                            edgecolor='none',
                            clip_on=False)
fig.patches.append(rect)

# Title (y=0.90, safely below red bar)
fig.text(0.10, 0.90, 'The automation gap',
         fontsize=16, fontweight='bold', color='#1a1a1a',
         transform=fig.transFigure, ha='left')

# Subtitle (y=0.85)
fig.text(0.10, 0.85, 'AI adoption in testing vs. maintenance burden reduction, %',
         fontsize=11, color='#666666',
         transform=fig.transFigure, ha='left')

# Source (y=0.03, in source zone)
fig.text(0.10, 0.03, 'Sources: Tricentis Research; TestGuild Survey',
         fontsize=8, color='#888888',
         transform=fig.transFigure, ha='left')

# === SAVE ===
plt.savefig('chart.png', dpi=300, facecolor='#f1f0e9')
plt.close()
```

---

## 10. KNOWN BUGS AND FIXES

| Bug | Symptom | Root Cause | Fix |
|-----|---------|------------|-----|
| Title/red bar overlap | Title hidden by red bar | Title y > 0.94 | Set title y=0.90 |
| Label/line overlap | Text on data line | No xytext offset | Add xytext=(0, ±20) |
| Label/axis overlap | Series label in X-axis zone | Label too low | Move label higher or to end-of-line |
| Label/label overlap | Two labels collide | Insufficient spacing | Stagger position or use end labels |
| Clipped elements | Edges cut off | Margins too tight | Adjust subplots_adjust() |
| Vertical gridlines | Grid in both directions | xgrid not disabled | ax.xaxis.grid(False) |
| Legend box present | Box instead of inline | Using ax.legend() | Remove legend, use ax.annotate() |
