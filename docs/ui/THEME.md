# Tayfin UI Theme Tokens

**Version:** 1.0  
**Date:** 2026-03-08  
**Status:** Draft

---

## 1. Base Theme (Dark)

All Tayfin UI components use a dark theme optimized for prolonged use in trading environments.

### Background

| Token | Hex | RGB | Usage |
|---|---|---|---|
| `--bg-base` | `#1e1e2e` | `30, 30, 46` | Page background |
| `--bg-surface` | `#181825` | `24, 24, 37` | Cards, summary panels |
| `--bg-overlay` | `#313244` | `49, 50, 68` | Hover, expanded rows, modals |
| `--bg-input` | `#45475a` | `69, 71, 90` | Input fields, select backgrounds |

### Text

| Token | Hex | Usage |
|---|---|---|
| `--text-primary` | `#cdd6f4` | Primary content text |
| `--text-secondary` | `#a6adc8` | Labels, subtitles |
| `--text-muted` | `#6c7086` | Disabled text, placeholders |
| `--text-inverse` | `#1e1e2e` | Text on bright backgrounds |

### Border & Divider

| Token | Hex | Usage |
|---|---|---|
| `--border-default` | `#45475a` | Table borders, card outlines |
| `--border-subtle` | `#313244` | Row dividers |
| `--border-focus` | `#89b4fa` | Focus rings (2px solid) |

---

## 2. Band Colors

Used for MCSA score band indicators (badges, row accents, score text).

| Band | Badge BG | Badge Text | Row Accent | Score Text |
|---|---|---|---|---|
| Strong (≥85) | `#166534` | `#4ade80` | `#22c55e` | `#4ade80` |
| Watchlist (≥70) | `#1e3a5f` | `#60a5fa` | `#3b82f6` | `#60a5fa` |
| Neutral (≥50) | `#854d0e` | `#fbbf24` | `#f59e0b` | `#fbbf24` |
| Weak (<50) | `#991b1b` | `#f87171` | `#ef4444` | `#f87171` |

### CSS Variables

```css
:root {
  --band-strong-bg: #166534;
  --band-strong-text: #4ade80;
  --band-strong-accent: #22c55e;

  --band-watchlist-bg: #1e3a5f;
  --band-watchlist-text: #60a5fa;
  --band-watchlist-accent: #3b82f6;

  --band-neutral-bg: #854d0e;
  --band-neutral-text: #fbbf24;
  --band-neutral-accent: #f59e0b;

  --band-weak-bg: #991b1b;
  --band-weak-text: #f87171;
  --band-weak-accent: #ef4444;
}
```

---

## 3. Component Colors

Used for the 4 MCSA scoring components in charts, progress bars, and evidence cards.

| Component | Primary | Light (fill) | Hex Primary | Hex Light |
|---|---|---|---|---|
| Trend Structure | Teal | Light Teal | `#2dd4bf` | `#5eead4` |
| VCP Quality | Purple | Light Purple | `#a78bfa` | `#c4b5fd` |
| Volume Quality | Orange | Light Orange | `#fb923c` | `#fdba74` |
| Fundamentals | Pink | Light Pink | `#f472b6` | `#f9a8d4` |

### CSS Variables

```css
:root {
  --component-trend: #2dd4bf;
  --component-trend-light: #5eead4;

  --component-vcp: #a78bfa;
  --component-vcp-light: #c4b5fd;

  --component-volume: #fb923c;
  --component-volume-light: #fdba74;

  --component-fundamentals: #f472b6;
  --component-fundamentals-light: #f9a8d4;
}
```

---

## 4. Semantic Colors

| Token | Hex | Usage |
|---|---|---|
| `--success` | `#4ade80` | Boolean true, check marks (✅) |
| `--warning` | `#fbbf24` | Missing data indicators (⚠) |
| `--error` | `#f87171` | API errors, boolean false (❌) |
| `--info` | `#60a5fa` | Informational badges |

---

## 5. Typography

### Font Stack

| Role | Font | Fallback |
|---|---|---|
| UI text | Inter | system-ui, sans-serif |
| Monospace (tickers, scores) | JetBrains Mono | Consolas, monospace |

### Scale

| Token | Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| `--text-title` | 24px | 700 | 1.2 | Page titles |
| `--text-heading` | 16px | 600 | 1.3 | Section headers |
| `--text-body` | 13px | 400 | 1.5 | Table body text |
| `--text-small` | 12px | 500 | 1.4 | Detail labels |
| `--text-caption` | 11px | 600 | 1.3 | Badge text |
| `--text-th` | 12px | 600 | 1.3 | Table headers (uppercase, 0.5px letter-spacing) |
| `--text-mono` | 13px | 500 | 1.5 | Ticker symbols, scores |

---

## 6. Spacing

| Token | Value | Usage |
|---|---|---|
| `--space-1` | 4px | Tight internal padding |
| `--space-2` | 8px | Badge padding, icon gaps |
| `--space-3` | 12px | Card padding, table cell padding |
| `--space-4` | 16px | Section gaps |
| `--space-5` | 24px | Between major sections |
| `--space-6` | 32px | Page margins |

---

## 7. Border Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | 4px | Buttons, inputs |
| `--radius-md` | 8px | Cards, panels |
| `--radius-lg` | 12px | Modal containers |
| `--radius-full` | 9999px | Badge pills |

---

## 8. Shadows

| Token | Value | Usage |
|---|---|---|
| `--shadow-card` | `0 1px 3px rgba(0,0,0,0.3)` | Cards |
| `--shadow-dropdown` | `0 4px 12px rgba(0,0,0,0.4)` | Dropdowns, popovers |
| `--shadow-modal` | `0 8px 24px rgba(0,0,0,0.5)` | Modal overlays |

---

## 9. Progress Bar Specifications

Used for component score mini-bars in the table.

| Property | Value |
|---|---|
| Height | 6px |
| Border radius | 3px |
| Background (track) | `--bg-overlay` (`#313244`) |
| Fill color | Component color (see §3) |
| Min width (label visible) | 30% of max |

---

This document defines all visual tokens for the Tayfin UI. All components must reference these tokens — no hardcoded colors or sizes in components.
