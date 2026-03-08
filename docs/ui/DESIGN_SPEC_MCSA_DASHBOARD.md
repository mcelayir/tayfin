# MCSA Score Dashboard — UX Design Specification

**Author:** UX Agent + PM Agent  
**Date:** 2026-03-08  
**Epic:** #20 — MCSA Score Dashboard  
**Status:** Draft — awaiting lead-dev review

---

## 1. Design Goals

| Goal | Rationale |
|---|---|
| **High data density** | Traders need to scan 100+ stocks quickly without excessive scrolling |
| **Score-first hierarchy** | MCSA score is the primary ranking — must be the visual anchor |
| **Progressive disclosure** | Summary → Table → Detail → Evidence (3 levels of depth) |
| **Colorblind-safe palette** | Use luminance contrast + shape indicators alongside color |
| **Dark theme** | Industry standard for trading tools; reduces eye strain |

---

## 2. Information Architecture

### Page Structure (Top → Bottom)

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: Tayfin — MCSA Score Dashboard                  │
│  Subtitle: NASDAQ-100 • Last scored: 2026-03-07         │
├─────────────────────────────────────────────────────────┤
│  SUMMARY BAR                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ Band     │  │ Score    │  │ Component│  │ Total  │  │
│  │ Distrib. │  │ Histogram│  │ Averages │  │ 101    │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
├─────────────────────────────────────────────────────────┤
│  FILTER BAR                                             │
│  [Band ▼]  [Min Score ═══○══]  [Search ticker...]       │
├─────────────────────────────────────────────────────────┤
│  SCORE TABLE                                            │
│  # │ Ticker │ Score │ Band │ Trend │ VCP │ Vol │ Fund  │
│  ──┼────────┼───────┼──────┼───────┼─────┼─────┼─────  │
│  1 │ BKR    │ 69.85 │ ■■■  │ ████  │ ██  │ ███ │      │
│  2 │ WMT    │ 65.90 │ ■■■  │ ████  │ ██  │ ██  │      │
│  3 │ PEP    │ 63.45 │ ■■■  │ ████  │ ██  │ ██  │      │
│  ...                                                    │
├─────────────────────────────────────────────────────────┤
│  DETAIL PANEL (expanded row)                            │
│  ┌─────────────────────────────────────────────────┐    │
│  │  BKR — Score: 69.85 / 100 (neutral)             │    │
│  │                                                   │    │
│  │  ┌─────────┐  ┌──────────────────────────────┐   │    │
│  │  │ Donut   │  │ Evidence Breakdown            │   │    │
│  │  │ Chart   │  │                               │   │    │
│  │  │ 4 parts │  │ Trend (30/30): ✅✅✅✅       │   │    │
│  │  │         │  │ VCP (24.85/35): 71.0 score    │   │    │
│  │  │         │  │ Volume (15/15): ✅✅✅         │   │    │
│  │  │         │  │ Fund (0/20): ⚠ No data        │   │    │
│  │  └─────────┘  └──────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Summary Bar

**Purpose:** At-a-glance distribution overview before diving into the table.

#### Band Distribution Card

```
┌────────────────────────────────┐
│  Band Distribution             │
│                                │
│  ■ Strong    0   ░░░░░░░░░░   │
│  ■ Watchlist 0   ░░░░░░░░░░   │
│  ■ Neutral   14  ████░░░░░░   │
│  ■ Weak      87  █████████░   │
│                                │
│  Total: 101 tickers            │
└────────────────────────────────┘
```

#### Score Histogram Card

```
┌────────────────────────────────┐
│  Score Distribution            │
│                                │
│  90-100  ░                     │
│  80-90   ░                     │
│  70-80   ░                     │
│  60-70   ███  (5)              │
│  50-60   █████  (9)            │
│  40-50   ███████  (12)         │
│  30-40   ██████████  (25)      │
│  20-30   ████████████  (28)    │
│  10-20   ██████  (15)          │
│  0-10    ███  (7)              │
└────────────────────────────────┘
```

#### Component Averages Card

```
┌────────────────────────────────┐
│  Avg Component Scores          │
│                                │
│  Trend  ████████░░  20.1 / 30  │
│  VCP    █████░░░░░  18.3 / 35  │
│  Volume ██░░░░░░░░   4.2 / 15  │
│  Fund   ░░░░░░░░░░   0.0 / 20  │
└────────────────────────────────┘
```

### 3.2 Filter Bar

| Control | Type | Behavior |
|---|---|---|
| Band Filter | Multi-select dropdown | Checkboxes for each band; "All" default |
| Min Score | Range slider | 0–100, step 1, updates table live |
| Ticker Search | Text input | Case-insensitive substring match, debounced 300ms |

Filters are applied **client-side** on the loaded dataset (≤101 items). No server round-trip needed for filtering.

### 3.3 Score Table

**Headers (all sortable):**

| Column | Width | Align | Visual Treatment |
|---|---|---|---|
| # | 40px | Right | Row index (recalculates after sort/filter) |
| Ticker | 80px | Left | Bold, monospace font (`JetBrains Mono`) |
| Score | 80px | Right | Band-colored text, 1 decimal place |
| Band | 90px | Center | Colored badge (rounded pill) |
| Trend | 80px | Center | Mini horizontal bar (0–30 scale) |
| VCP | 80px | Center | Mini horizontal bar (0–35 scale) |
| Volume | 80px | Center | Mini horizontal bar (0–15 scale) |
| Fundamentals | 80px | Center | Mini horizontal bar (0–20 scale) |

**Row behavior:**
- Hover: subtle background highlight (#2a2a3a)
- Click: expands detail panel below the row
- Active row: left border accent in band color

**Mini progress bars:**
- Background: `#313244` (dark gray)
- Fill: Band color of that row
- Label: score value inside the bar (if bar is wide enough) or beside

### 3.4 Score Detail Panel

Triggered by clicking a table row. Expands below the clicked row (inline accordion pattern).

**Layout:** Two-column

| Left Column (40%) | Right Column (60%) |
|---|---|
| Component donut chart | Evidence breakdown cards |

#### Donut Chart

- 4 segments: Trend, VCP, Volume, Fundamentals
- Segment size = actual score (not weight)
- Segment color = component-specific color
- Center text: total score + band
- Missing components shown as gray segment

**Component Colors:**
| Component | Color | Hex |
|---|---|---|
| Trend | Teal | `#2dd4bf` |
| VCP | Purple | `#a78bfa` |
| Volume | Orange | `#fb923c` |
| Fundamentals | Pink | `#f472b6` |

#### Evidence Breakdown (Right Column)

4 cards stacked vertically, one per component:

**Trend Evidence Card:**
```
┌──────────────────────────────────────────┐
│  📈 Trend Structure    30 / 30           │
│  ───────────────────────────────────     │
│  ✅ Price > SMA50                        │
│  ✅ SMA50 > SMA150                       │
│  ✅ SMA150 > SMA200                      │
│  ✅ Within 15% of 52w High (8.35%)       │
└──────────────────────────────────────────┘
```

**VCP Evidence Card:**
```
┌──────────────────────────────────────────┐
│  🔄 VCP Quality        24.85 / 35       │
│  ───────────────────────────────────     │
│  VCP Score: 71.0 / 100                   │
│  Pattern Detected: ✅ Yes                │
└──────────────────────────────────────────┘
```

**Volume Evidence Card:**
```
┌──────────────────────────────────────────┐
│  📊 Volume Quality     15 / 15           │
│  ───────────────────────────────────     │
│  ✅ Pullback below volume SMA            │
│  ✅ Volume dry-up detected               │
│  ✅ No abnormal selling spikes           │
└──────────────────────────────────────────┘
```

**Fundamentals Evidence Card:**
```
┌──────────────────────────────────────────┐
│  💰 Fundamentals       0 / 20            │
│  ───────────────────────────────────     │
│  ⚠ Revenue Growth YoY: No data          │
│  ⚠ Earnings Growth YoY: No data         │
│  ⚠ ROE: No data                         │
│  ⚠ Net Margin: No data                  │
│  ⚠ Debt/Equity: No data                 │
│                                          │
│  ⚠ Missing fields: 5                    │
└──────────────────────────────────────────┘
```

### 3.5 States

| State | Visual |
|---|---|
| **Loading** | Skeleton placeholders (animated pulse) for summary cards + table rows |
| **Error (API down)** | Red alert banner: "Unable to load MCSA data. Screener API unreachable." with retry button |
| **Empty (no results)** | Centered message: "No MCSA results match your filters." with reset button |
| **Partial data** | Yellow warning icon on rows with `missing_fields.length > 0` |
| **Data loaded** | Full UI with data |

---

## 4. Typography

| Element | Font | Size | Weight |
|---|---|---|---|
| Page title | Inter | 24px | 700 |
| Section headers | Inter | 16px | 600 |
| Table headers | Inter | 12px | 600 (uppercase, letter-spacing: 0.5px) |
| Table body | Inter | 13px | 400 |
| Ticker symbol | JetBrains Mono | 13px | 600 |
| Score numbers | JetBrains Mono | 13px | 500 |
| Badge text | Inter | 11px | 600 |
| Detail labels | Inter | 12px | 500 |
| Detail values | JetBrains Mono | 12px | 400 |

---

## 5. Color System

### Base Theme (Dark)

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#1e1e2e` | Page background |
| `--bg-surface` | `#181825` | Cards, panels |
| `--bg-overlay` | `#313244` | Hover states, expanded panels |
| `--text-primary` | `#cdd6f4` | Main text |
| `--text-secondary` | `#a6adc8` | Subdued labels |
| `--text-muted` | `#6c7086` | Disabled, placeholders |
| `--border` | `#45475a` | Dividers, table borders |

### Band Colors

| Band | Badge BG | Badge Text | Row Accent |
|---|---|---|---|
| Strong (≥85) | `#166534` | `#4ade80` | `#22c55e` |
| Watchlist (≥70) | `#1e3a5f` | `#60a5fa` | `#3b82f6` |
| Neutral (≥50) | `#854d0e` | `#fbbf24` | `#f59e0b` |
| Weak (<50) | `#991b1b` | `#f87171` | `#ef4444` |

### Component Colors

| Component | Primary | Light (bars) |
|---|---|---|
| Trend | `#2dd4bf` | `#5eead4` |
| VCP | `#a78bfa` | `#c4b5fd` |
| Volume | `#fb923c` | `#fdba74` |
| Fundamentals | `#f472b6` | `#f9a8d4` |

### Semantic Colors

| Token | Hex | Usage |
|---|---|---|
| `--success` | `#4ade80` | Boolean true, check marks |
| `--warning` | `#fbbf24` | Missing data indicators |
| `--error` | `#f87171` | API errors, boolean false |
| `--info` | `#60a5fa` | Informational badges |

---

## 6. Accessibility

| Requirement | Implementation |
|---|---|
| Color contrast | All text meets WCAG AA (4.5:1 minimum) |
| Colorblind support | Band badges include text label, not just color |
| Screen reader | Table uses `<th scope="col">`, ARIA labels on interactive elements |
| Keyboard navigation | Tab through filter controls; Enter/Space to expand rows |
| Focus indicators | 2px solid `#89b4fa` focus ring |

---

## 7. Responsive Breakpoints

| Breakpoint | Layout Change |
|---|---|
| ≥1200px (Desktop) | Full layout: summary bar (4-col grid) + full table + side detail |
| 768–1199px (Tablet) | Summary bar (2-col grid), table hides Fundamentals column |
| <768px (Mobile) | Summary bar stacked, table shows only Ticker + Score + Band, detail as full-width overlay |

**Note:** Primary target is desktop. Mobile is "functional but not optimized."

---

## 8. Interaction Model

### Table Sorting
- Click column header → sort ascending
- Click again → sort descending
- Active sort column shows ▲ or ▼ icon
- Default: `Score ▼` (descending)

### Row Expansion
- Click row → expand detail panel below (accordion)
- Only one row expanded at a time
- Click expanded row → collapse
- ESC key → collapse

### Filtering
- All filters apply client-side (dataset ≤101 items)
- No debounce for band filter (instant)
- 300ms debounce for ticker search
- Slider updates on mouse release (not drag)
- URL query params sync: `?band=neutral&min_score=50&sort=score&order=desc`

---

## 9. API Integration

### Data Flow

```
[Page Load] → GET /api/mcsa/dashboard → [Render Table]
[Click Row] → GET /api/mcsa/{ticker} → [Render Detail]
```

**Optimization:** The `/api/mcsa/dashboard` response already includes `evidence` and `missing_fields`. The detail panel should use the **already-loaded data** for the expanded row, avoiding an extra API call. The per-ticker endpoint is only needed if we want the freshest single-ticker data (optional).

### Caching
- Dashboard data: 5-minute browser cache (`Cache-Control: max-age=300`)
- No real-time updates needed (scores computed by batch jobs)

---

## 10. Reference Designs

Design patterns inspired by:

| Feature | Reference | Pattern |
|---|---|---|
| Data table | FinViz Screener | High-density sortable table with compact rows |
| Score visualization | TradingView Technicals | Gauge/meter for single score |
| Component breakdown | Morningstar Style Box | Grid of categorical indicators |
| Color system | Catppuccin Mocha | Dark theme with pastel accents |
| Detail expansion | Bloomberg Terminal | Inline expansion for deep data |

---

This document is the authoritative UX specification for the MCSA Score Dashboard. All UI implementation must conform to these wireframes, color tokens, and interaction patterns.
