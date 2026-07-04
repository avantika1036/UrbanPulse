# UrbanPulse — Tableau Dashboard Design Notes
**Version 1.0 | For Portfolio Use | Data: Real + Synthetic (seed=42)**

Data source files are in `data/exports/`. Connect Tableau Desktop to each
CSV via **Text File** connector. All 5 sheets use live-refresh connections
(no extract required for a portfolio demo).

---

## Page 1 — City Score Overview

### Purpose
Compare all 6 cities at a glance, filtered by persona. The primary
landing page for any reviewer or hiring manager opening the dashboard.

### Source File
`data/exports/city_score_overview.csv`

### Dimensions
| Field | Role | Notes |
|---|---|---|
| `city_name` | Row label | Displayed on y-axis |
| `persona` | Filter control | Drop-down: early_career / family_focused / budget_focused |
| `region` | Color group (optional) | North / South / West |

### Measures
| Field | Role | Notes |
|---|---|---|
| `adjusted_life_score` | Primary bar length | Sort descending |
| `income_score` | Tooltip | |
| `affordability_score` | Tooltip | |
| `healthcare_score` | Tooltip | |
| `environment_score` | Tooltip | |
| `career_growth_score` | Tooltip | |
| `family_fit_score` | Tooltip | |

### Chart Type
Horizontal bar chart, sorted descending by `adjusted_life_score`.

### Color Scale
Continuous diverging: Red (#D73027) at 0 → White at 50 → Green (#1A9850) at 100.
Apply to `adjusted_life_score` using a stepped 5-color palette.

### Filter Controls
- **Persona** (required): Single-select drop-down
  - Changing persona re-ranks all cities dynamically
- **Region** (optional): Multi-select checkbox

### KPI Card
Place a KPI card in the top-right corner:
- **Label**: "Best City for [Persona]"
- **Value**: `MAX(city_name)` where `adjusted_life_score = WINDOW_MAX(MAX(adjusted_life_score))`
- **Sub-label**: Score value formatted as `##.# / 100`

### Headline Insight
> "Hyderabad consistently tops the budget_focused ranking while Bengaluru
> leads early_career — demonstrating that no single city dominates all
> personas, validating the need for persona-weighted scoring."

### Implementation Notes
- Use a parameter `[Selected Persona]` with values {early_career, family_focused, budget_focused}
- Filter the view: `[persona] = [Selected Persona]`
- Add reference line at 50 (midpoint) with dashed grey formatting

---

## Page 2 — Dimension Radar Chart

### Purpose
Show the full 7-dimension score fingerprint for any city × persona
combination, enabling side-by-side comparison of why two cities have
similar composite scores but very different profiles.

### Source File
`data/exports/city_score_overview.csv`

### Dimensions
| Field | Role | Notes |
|---|---|---|
| `city_name` | Filter + color | Multi-select (up to 3 cities for readability) |
| `persona` | Filter | Single-select |
| Dimension label | Axis spoke | Computed field — see below |

### Measures
| Field | Axis Spoke Label | Notes |
|---|---|---|
| `income_score` | Income vs CoL | |
| `affordability_score` | Affordability | |
| `healthcare_score` | Healthcare | Seeded from real data for BLR/MUM/CHE |
| `environment_score` | Environment | |
| `career_growth_score` | Career Growth | |
| `family_fit_score` | Family Fit | |
| `adjusted_life_score` | Composite | Optional — can omit from radar to keep 6 spokes |

### Chart Type
Radar/spider chart. Tableau does not have a native radar chart — use the
following workaround:
1. Create a calculated field `[Angle]` using index-based trigonometry (6 dimensions = 60° apart):
(INDEX()-1) * (360/6)
2. Use dual-axis polar coordinate calculation with SIN/COS on a unit circle
3. **Simpler alternative for portfolio**: Use a `filled area chart` on a
   circular path, or replace with a **Bullet Chart** (one bar per dimension,
   reference line at 50) which is easier to build and equally readable.

### Filter Controls
- **City Name** (required): Multi-select, max 3 cities
- **Persona** (required): Single-select

### Color Encoding
Assign one distinct color per selected city:
- Mumbai: #E63946
- Bengaluru: #457B9D
- Chennai: #2A9D8F
- Pune: #E9C46A
- Delhi: #F4A261
- Hyderabad: #264653

### Headline Insight
> "Bengaluru and Hyderabad have nearly identical composite scores for
> early_career, but Bengaluru scores ~30 points higher on career_growth
> while Hyderabad scores ~25 points higher on affordability — the radar
> reveals trade-offs invisible in a single composite score."

### Implementation Notes
- Add a data label annotation on the lowest spoke for each city:
  "Weakest dimension: [dim name]"
- Tooltip should show: city, dimension, score, and percentile rank among 6 cities

---

## Page 3 — Monthly Trends

### Purpose
Reveal seasonal and year-over-year patterns in AQI, rent, and salary
across cities. Key for showing how the platform uses time-series data,
not just static snapshots.

### Source File
`data/exports/monthly_trends.csv`

### Dimensions
| Field | Role | Notes |
|---|---|---|
| `year_month` | X-axis | Format as MMM YYYY |
| `city_name` | Color / Line series | Multi-select filter |

### Measures
| Field | Y-axis Label | Notes |
|---|---|---|
| `avg_aqi` | Air Quality Index | Lower = better — annotate |
| `avg_rent_1bhk` | Avg 1BHK Rent (₹/month) | |
| `avg_salary_offered` | Avg Salary Offered (₹/month) | |
| `hospital_utilization_rate` | Hospital Utilization (%) | Secondary axis |
| `rainfall_mm` | Rainfall (mm) | Bar overlay on secondary axis |

### Chart Type
Multi-line chart. One line per selected city, colored by city.
Add a secondary bar chart (dual axis) for `rainfall_mm` to show
monsoon correlation with utilization rate.

### Filter Controls
- **City Name** (required): Multi-select checkbox — default: all 6
- **Metric** (required): Parameter to switch Y-axis measure:
  - Options: AQI / Rent 1BHK / Salary Offered / Hospital Utilization / Rainfall
- **Year** (optional): Range slider — 2023, 2024

### Reference Annotations
- Annotate Oct–Dec 2023 and Oct–Dec 2024 on Delhi AQI line: "Winter pollution spike"
- Annotate Jun–Sep on Mumbai/Chennai rainfall bars: "Monsoon season"

### Headline Insight
> "Delhi's AQI peaks above 300 every Oct–Dec (both 2023 and 2024),
> while Bengaluru's AQI stays below 90 year-round — a 3× quality-of-life
> gap that the static annual average (Delhi: 215 vs Bengaluru: 62) only
> partially captures."

### Implementation Notes
- Use a `[Selected Metric]` string parameter with a CASE statement in a
  calculated field `[Y Axis Value]` to drive the metric toggle
- Format `year_month` as a continuous date axis (convert YYYY-MM to DATE)
- Include a footnote: "Source: Synthetic data with seasonal rules (seed=42). AQI profiles calibrated to known city profiles."

---

## Page 4 — Real Health Data (⚠️ REAL DATA PAGE)

### Purpose
Showcase the platform's real government data foundation. This page
intentionally differentiates UrbanPulse from synthetic-only dashboards.
The data provenance annotation is mandatory on this page.

### Source File
`data/exports/health_summary_real.csv`

### Dimensions
| Field | Role | Notes |
|---|---|---|
| `city_name` | X-axis (Chart 1 & 2) | |
| `year` | X-axis detail (Chart 1) | Range: 2001–2024 depending on city |
| `data_source` | Badge label | 'real' / 'synthetic_estimate' |

### Measures
| Field | Chart | Notes |
|---|---|---|
| `crude_death_rate_per_1000` | Chart 1 — line chart | Y-axis: per 1,000 population |
| `total_births` | Chart 1 tooltip | |
| `total_deaths` | Chart 1 tooltip | |
| `hospital_beds_per_lakh` | Chart 2 — bar chart | Y-axis: per 1 lakh population |
| `health_centres_per_lakh` | Chart 2 — bar overlay | Secondary axis |
| `infant_mortality` | Chart 2 tooltip | Pune 2017 only — real value |

### Chart 1: Crude Death Rate Trend
- **Type**: Line chart with year on X-axis
- **Series**: One line per city (only cities with real data: Bengaluru, Chennai, Delhi, Pune)
- **Annotation**: Add a reference band for 2020–2021 labeled "COVID-19 spike"
- **Color**: Same city color palette as Page 2

### Chart 2: Healthcare Infrastructure
- **Type**: Grouped bar chart — `hospital_beds_per_lakh` as primary bar,
  `health_centres_per_lakh` as dot overlay (secondary axis)
- **All 6 cities** shown — bars for real-data cities are solid;
  bars for synthetic-estimate cities (Delhi, Hyderabad, Pune) are hatched/lighter

### Source Annotation (MANDATORY — place in dashboard footer)
Source: Bengaluru — BBMP Annual Births & Deaths + BBMP Health Centres (2001–2024)
Mumbai — BMC Ward-Wise Public Health Centres (288 facilities, real bed counts)
Chennai — GCC Urban Community Health Centres (16 UCHCs) + Annual B&D (2018–2025)
Pune — PMC Annual Births & Deaths (1975–2018) + KRA Daily Report 2017
Delhi — State Health Dept Annual Births & Deaths (2017–2024)
Hyderabad — All metrics are synthetic estimates (no real CSV available)

### Filter Controls
- **City Name** (required): Multi-select checkbox — default: all cities with real data
- **Year Range** (Chart 1 only): Range slider
- **Data Source Badge** toggle: "Show real data only" checkbox — hides synthetic-estimate cities from Chart 2

### Headline Insight
> "COVID-19 caused a 35% spike in crude death rates across Bengaluru,
> Chennai, and Delhi in 2021 — visible in the real government data —
> with Chennai showing the sharpest single-year increase (+35.3%),
> recovering to near-2019 levels by 2023."

### Implementation Notes
- Add a banner at the top of the page: "⬛ = Real government data | ▨ = Synthetic estimate"
- The `data_source` field in health_summary_real.csv drives this distinction
- Tooltip on every bar should show: city, year, value, and data_source badge

---

## Page 5 — Relocation Outcomes

### Purpose
Show how the synthetic user behavioral data supports the ML model —
demonstrating that user choices were correlated with persona (not random),
validating the recommender's training signal.

### Source File
`data/exports/relocation_outcomes.csv`

### Dimensions
| Field | Role | Notes |
|---|---|---|
| `persona` | X-axis grouping | 3 groups |
| `selected_city` | Color/bar sub-group | 6 cities |

### Measures
| Field | Y-axis | Notes |
|---|---|---|
| `COUNT([selected_city])` | Bar height | Absolute count per persona × city |
| Percentage of persona total | Label | `COUNT / TOTAL(COUNT)` — shown as %, one decimal place |

### Chart Type
Grouped bar chart:
- X-axis: `persona` (3 groups)
- Within each group: one bar per `selected_city` (6 bars)
- Bar height: COUNT of selections
- Bar label: percentage of that persona's total selections
- Color: city color palette from Page 2

### Filter Controls
- **Persona** (optional): Single-select filter to isolate one persona's bar group
- **City** (optional): Multi-select to highlight specific cities across all personas

### Calculated Field: Selection Share
[Persona City Share] = COUNT([selected_city]) / TOTAL(COUNT([selected_city]))
Format as percentage to 1 decimal place. Use as bar label.

### Annotations
- Add a text annotation on the highest bar in each persona group:
  "Most selected: [city] ([pct]%)"
- Add a note below the chart:
  "Persona-city selection correlations are by design — the synthetic data
   generator applied weighted city probabilities per persona (early_career →
   Bengaluru 32% / Hyderabad 26%; family_focused → Pune 30% / Chennai 26%;
   budget_focused → Hyderabad 30% / Pune 26%). These weights serve as ML
   training labels for the city recommender."

### Headline Insight
> "The relocation query dataset shows strong persona-city correlation:
> early_career users selected Bengaluru or Hyderabad in ~58% of cases,
> family_focused users chose Pune or Chennai in ~56% of cases, and
> budget_focused users chose Hyderabad or Pune in ~56% of cases —
> providing a statistically meaningful training signal for the
> RandomForest classifier."

### Implementation Notes
- Sort cities within each persona group by COUNT descending
- Add a second view below the grouped bar: a **Sankey/flow chart** alternative
  mapping persona → selected_city (can be built with a custom polygon workaround
  or a Tableau extension) — optional but visually striking for portfolio use
- Include total N count per persona in the group header label

---

## Dashboard-Level Notes

### Connection Setup
1. Open Tableau Desktop
2. Connect → Text File → navigate to `data/exports/`
3. Connect all 5 CSVs as separate data sources
4. For Pages 1–3: use `city_score_overview.csv` (primary), join with `monthly_trends.csv` on `city_name`
5. For Page 4: use `health_summary_real.csv` as standalone source
6. For Page 5: use `relocation_outcomes.csv` as standalone source

### Color Palette (use consistently across all pages)
| City | Hex |
|---|---|
| Mumbai | #E63946 |
| Bengaluru | #457B9D |
| Chennai | #2A9D8F |
| Pune | #E9C46A |
| Delhi | #F4A261 |
| Hyderabad | #264653 |

### Fonts
- Title: Tableau Bold or Georgia Bold, 18pt
- Subtitles: Tableau Medium, 13pt
- Labels: Tableau Light, 10pt
- Footer/attribution: Tableau Light Italic, 9pt, color #666666

### Dashboard Size
Fixed: 1400 × 900px (standard widescreen laptop). Tiled layout, no floating.

### Portfolio Framing
Add a cover page with:
- Project name: **UrbanPulse**
- Tagline: *Salary-adjusted city intelligence for India's mobile workforce*
- Data note: *Healthcare scores seeded from real government data (BBMP, BMC, GCC, PMC, Delhi Health Dept). All other metrics are synthetic (seed=42) or derived from public cost-of-living benchmarks.*
- Tech stack badge: Python | FastAPI | PostgreSQL | scikit-learn | React | Tableau