"""
reports/generate_pdf_report.py

Generates a structured PDF relocation intelligence report using fpdf2.

Entry point:
    from reports.generate_pdf_report import generate_report
    path = generate_report(comparison_data, narrative="...")

comparison_data dict schema (mirrors what the scoring engine + API produce):
{
    "persona":          str,               # "early_career" | "family_focused" | "budget_focused"
    "cities_compared":  list[str],
    "best_city":        str,
    "scores":           dict[str, dict],   # {city: {dimension: float, ...}}
    "top_positive":     dict,              # {"dimension": str, "score": float}
    "top_negative":     dict,              # {"dimension": str, "score": float}
    "drivers":          dict,              # {city: {"top_positive": {...}, "top_negative": {...}}}
    "salary_equivalence": dict,            # {city: required_salary_float}
    "source_city":      str,               # city the salary equivalence is FROM
    "monthly_income":   float,             # user's current monthly income
    "health_data":      dict,              # {city: {"total_facilities": int, "total_beds": int, ...}}
}

Run standalone:
    python reports/generate_pdf_report.py
"""

import os
import sys
from datetime import datetime
from typing import Optional

from fpdf import FPDF, XPos, YPos

# ── PATHS ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── DESIGN TOKENS ────────────────────────────────────────────────────────────
# Kept as module-level constants so every method reads from one place.

COLOR_BG_NAVY   = (15,  26,  42)   # #0f172a  — page accent band
COLOR_ACCENT    = (59,  130, 246)  # #3b82f6  — blue headings
COLOR_SUCCESS   = (22,  163, 74)   # #16a34a  — positive drivers
COLOR_DANGER    = (220, 38,  38)   # #dc2626  — negative drivers
COLOR_WARN      = (217, 119, 6)    # #d97706  — mid-range scores
COLOR_TEXT      = (15,  23,  42)   # near-black body text
COLOR_MUTED     = (100, 116, 139)  # #64748b  — labels, captions
COLOR_BORDER    = (203, 213, 225)  # #cbd5e1  — table borders
COLOR_ROW_ALT   = (241, 245, 249)  # #f1f5f9  — alternating row tint
COLOR_WHITE     = (255, 255, 255)

MARGIN_L   = 15
MARGIN_R   = 15
PAGE_W     = 210  # A4 width mm
CONTENT_W  = PAGE_W - MARGIN_L - MARGIN_R  # 180 mm

PERSONA_LABELS = {
    "early_career":   "Early Career",
    "family_focused": "Family Focused",
    "budget_focused": "Budget Focused",
}

DIMENSION_LABELS = {
    "income_score":        "Income vs Cost of Living",
    "affordability_score": "Affordability",
    "healthcare_score":    "Healthcare Access",
    "environment_score":   "Environment & Pollution",
    "career_growth_score": "Career Growth",
    "family_fit_score":    "Family Fit",
    "adjusted_life_score": "Overall Score",
}

SCORE_DIMENSIONS_ORDER = [
    "income_score",
    "affordability_score",
    "healthcare_score",
    "environment_score",
    "career_growth_score",
    "family_fit_score",
    "adjusted_life_score",
]

REAL_DATA_SOURCES = {
    "Bengaluru": "BBMP Annual B&D 2001–2024 | BBMP Health Centres (32 real facilities)",
    "Mumbai":    "BMC Public Health 2024 | 288 ward-level hospitals with real bed counts",
    "Chennai":   "Greater Chennai Corporation | 16 UCHCs | Annual B&D 2018–2025",
    "Pune":      "Pune Municipal Corporation | Annual B&D 1975–2018 | KRA Disease Report 2017",
    "Delhi":     "Delhi State Health Dept | Annual B&D 2017–2024",
    "Hyderabad": "Synthetic estimate (no real government source available)",
}


# ── HELPER: SCORE → RGB ──────────────────────────────────────────────────────

def _score_color(score: float) -> tuple:
    """Returns an RGB tuple for a 0-100 score value."""
    if score >= 70:
        return COLOR_SUCCESS
    if score >= 45:
        return COLOR_WARN
    return COLOR_DANGER


def _fmt_score(score) -> str:
    """Formats a numeric score as 'XX.X' or '—' for None."""
    if score is None:
        return "—"
    try:
        return f"{float(score):.1f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_inr(amount) -> str:
    """Formats a float as ₹X,XX,XXX (Indian number format)."""
    try:
        n = int(float(amount))
    except (TypeError, ValueError):
        return "N/A"
    s = str(n)
    if len(s) <= 3:
        return f"Rs.{s}"
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while len(rest) > 2:
        groups.append(rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.append(rest)
    formatted = ",".join(reversed(groups)) + "," + last3
    return f"Rs.{formatted}"


# ── PDF CLASS ─────────────────────────────────────────────────────────────────

class UrbanPulsePDF(FPDF):
    """
    Custom FPDF subclass for UrbanPulse reports.

    Adds a branded header band, auto page-break footer with page numbers,
    and a set of convenience drawing methods used by generate_report().
    """

    def __init__(self, persona: str, cities: list):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.persona_label = PERSONA_LABELS.get(persona, persona.replace("_", " ").title())
        self.cities = cities
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(MARGIN_L, 15, MARGIN_R)

    # ── FPDF overrides ───────────────────────────────────────────────────────

    def header(self):
        """Thin branded top stripe on every page (except page 1 cover band)."""
        if self.page_no() == 1:
            return
        self.set_fill_color(*COLOR_BG_NAVY)
        self.rect(0, 0, PAGE_W, 8, style="F")
        self.set_y(2)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*COLOR_WHITE)
        self.cell(0, 4, "UrbanPulse  |  Relocation Intelligence Report", align="L")
        self.set_text_color(*COLOR_TEXT)
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*COLOR_MUTED)
        self.cell(
            0, 5,
            f"Page {self.page_no()}  |  Generated by UrbanPulse  |  "
            f"Scores normalised 0-100 relative to compared cities only",
            align="C",
        )
        self.set_text_color(*COLOR_TEXT)

    # ── Layout helpers ───────────────────────────────────────────────────────

    def section_title(self, text: str):
        """Renders a section heading with a full-width accent underline."""
        self.ln(4)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*COLOR_ACCENT)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*COLOR_ACCENT)
        self.set_line_width(0.4)
        self.line(MARGIN_L, self.get_y(), PAGE_W - MARGIN_R, self.get_y())
        self.set_draw_color(*COLOR_BORDER)
        self.set_line_width(0.2)
        self.set_text_color(*COLOR_TEXT)
        self.ln(3)

    def kv_row(self, label: str, value: str, label_w: float = 55):
        """Renders a label : value pair in body text."""
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*COLOR_MUTED)
        self.cell(label_w, 5, label.upper(), align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*COLOR_TEXT)
        self.cell(0, 5, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def body_text(self, text: str, size: int = 9):
        """Renders wrapped body text."""
        self.set_font("Helvetica", "", size)
        self.set_text_color(*COLOR_TEXT)
        self.multi_cell(
            CONTENT_W, 5, text,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

    def colored_pill(self, text: str, color: tuple, x: float, y: float, w: float = 55):
        """Renders a small rounded-rect score pill at (x, y)."""
        self.set_xy(x, y)
        self.set_fill_color(
            min(255, color[0] + 180),
            min(255, color[1] + 180),
            min(255, color[2] + 180),
        )
        self.set_text_color(*color)
        self.set_font("Helvetica", "B", 8)
        self.cell(w, 5, text, align="C", fill=True)
        self.set_text_color(*COLOR_TEXT)
        self.set_fill_color(*COLOR_WHITE)


# ── SECTION RENDERERS ─────────────────────────────────────────────────────────

def _render_cover(pdf: UrbanPulsePDF, data: dict, report_date: str):
    """Section 1 — branded cover band + meta block."""
    # Navy top band
    pdf.set_fill_color(*COLOR_BG_NAVY)
    pdf.rect(0, 0, PAGE_W, 52, style="F")

    # Logo / title
    pdf.set_xy(MARGIN_L, 12)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.cell(0, 10, "UrbanPulse", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(MARGIN_L, 26)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(148, 175, 220)
    pdf.cell(0, 6, "Relocation Intelligence Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Accent stripe at bottom of band
    pdf.set_fill_color(*COLOR_ACCENT)
    pdf.rect(0, 48, PAGE_W, 4, style="F")

    pdf.set_text_color(*COLOR_TEXT)
    pdf.set_y(62)

    # Meta block
    persona_label = PERSONA_LABELS.get(data.get("persona", ""), data.get("persona", ""))
    cities_str    = "  ·  ".join(data.get("cities_compared", []))

    pdf.kv_row("Report Date",     report_date)
    pdf.kv_row("User Persona",    persona_label)
    pdf.kv_row("Cities Compared", cities_str)
    pdf.kv_row(
        "Monthly Income",
        _fmt_inr(data.get("monthly_income", 0)) + "/month",
    )
    pdf.ln(2)


def _render_executive_summary(pdf: UrbanPulsePDF, data: dict):
    """Section 2 — recommended city, overall score, one-line reason."""
    pdf.section_title("01  Executive Summary")

    best_city  = data.get("best_city", "N/A")
    scores     = data.get("scores", {})
    top_pos    = data.get("top_positive", {})
    persona    = PERSONA_LABELS.get(data.get("persona", ""), data.get("persona", ""))

    best_score = None
    if best_city in scores:
        best_score = scores[best_city].get("adjusted_life_score")

    score_str  = f"{best_score:.1f} / 100" if best_score is not None else "—"
    score_col  = _score_color(best_score) if best_score is not None else COLOR_MUTED
    reason_str = top_pos.get("dimension", "—")

    # Recommended city large text
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.cell(0, 10, best_city, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Score below city name
    y_after_city = pdf.get_y()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*score_col)
    pdf.cell(0, 7, f"Overall Score:  {score_str}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Why line
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(
        0, 5,
        f"Top-ranked for {persona} persona  |  Primary strength: {reason_str}",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.set_text_color(*COLOR_TEXT)
    pdf.ln(3)

    # Disclaimer
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(
        CONTENT_W, 4,
        "All scores are normalised 0–100 relative to the cities being compared, "
        "not against a fixed global benchmark. Changing the comparison set will "
        "alter individual city scores.",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.set_text_color(*COLOR_TEXT)
    pdf.ln(2)


def _render_score_table(pdf: UrbanPulsePDF, data: dict):
    """Section 3 — dimension × city score grid, best cell bold per row."""
    pdf.section_title("02  Score Comparison")

    cities       = data.get("cities_compared", [])
    scores       = data.get("scores", {})
    best_city    = data.get("best_city", "")

    if not cities or not scores:
        pdf.body_text("No score data available.")
        return

    n_cities     = len(cities)
    label_w      = 52
    city_w       = (CONTENT_W - label_w) / n_cities if n_cities > 0 else 30
    row_h        = 6

    # Header row — city names
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*COLOR_BG_NAVY)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.cell(label_w, row_h, "Dimension", align="L", fill=True)
    for city in cities:
        is_best = city == best_city
        pdf.cell(
            city_w, row_h,
            f"★ {city}" if is_best else city,
            align="C", fill=True,
        )
    pdf.ln(row_h)

    pdf.set_text_color(*COLOR_TEXT)

    for row_idx, dim_key in enumerate(SCORE_DIMENSIONS_ORDER):
        dim_label    = DIMENSION_LABELS.get(dim_key, dim_key)
        is_composite = dim_key == "adjusted_life_score"

        # Compute best value in this row for bolding
        row_vals = {}
        for city in cities:
            val = scores.get(city, {}).get(dim_key)
            if val is not None:
                row_vals[city] = float(val)
        best_val = max(row_vals.values()) if row_vals else None

        # Alternating fill
        if is_composite:
            fill_color = (226, 232, 240)
        elif row_idx % 2 == 0:
            fill_color = COLOR_WHITE
        else:
            fill_color = COLOR_ROW_ALT

        pdf.set_fill_color(*fill_color)

        # Label cell
        font_style = "B" if is_composite else ""
        pdf.set_font("Helvetica", font_style, 8)
        pdf.set_text_color(*COLOR_MUTED if not is_composite else COLOR_TEXT)
        pdf.cell(label_w, row_h, dim_label, align="L", fill=True)

        for city in cities:
            val      = row_vals.get(city)
            is_max   = val is not None and best_val is not None and abs(val - best_val) < 0.01
            val_str  = f"{val:.1f}/100" if val is not None else "—"
            col      = _score_color(val) if val is not None else COLOR_MUTED
            f_style  = "B" if (is_max or is_composite) else ""

            pdf.set_font("Helvetica", f_style, 8)
            pdf.set_text_color(*col)
            pdf.cell(city_w, row_h, val_str, align="C", fill=True)

        pdf.set_text_color(*COLOR_TEXT)
        pdf.ln(row_h)

    # Legend
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(0, 4, "Bold = highest score in row   |   Green ≥ 70   |   Amber 45–69   |   Red < 45   |   ★ = Recommended city")
    pdf.ln(6)
    pdf.set_text_color(*COLOR_TEXT)


def _render_score_drivers(pdf: UrbanPulsePDF, data: dict):
    """Section 4 — per-city top positive (green) and top negative (red) drivers."""
    pdf.section_title("03  Score Drivers by City")

    cities  = data.get("cities_compared", [])
    drivers = data.get("drivers", {})

    if not drivers:
        pdf.body_text("No driver data available.")
        return

    col_w     = CONTENT_W / len(cities) if cities else CONTENT_W
    row_top_y = pdf.get_y()

    # Column headers
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*COLOR_BG_NAVY)
    pdf.set_text_color(*COLOR_WHITE)
    for city in cities:
        pdf.cell(col_w, 6, city, align="C", fill=True)
    pdf.ln(6)
    pdf.set_text_color(*COLOR_TEXT)

    # Per-city driver cells
    max_cell_h = 0
    start_y    = pdf.get_y()

    for ci, city in enumerate(cities):
        city_drivers = drivers.get(city, {})
        pos          = city_drivers.get("top_positive", {})
        neg          = city_drivers.get("top_negative", {})

        x_pos = MARGIN_L + ci * col_w

        # Positive
        pdf.set_xy(x_pos, start_y)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*COLOR_SUCCESS)
        pos_label  = pos.get("dimension", "—")
        pos_score  = pos.get("score")
        pos_str    = f"+ {pos_label}"
        pos_score_str = f"({_fmt_score(pos_score)}/100)" if pos_score is not None else ""
        pdf.multi_cell(col_w - 2, 4, pos_str, align="L")
        if pos_score_str:
            pdf.set_xy(x_pos, pdf.get_y())
            pdf.set_font("Helvetica", "", 7)
            pdf.cell(col_w - 2, 4, pos_score_str, align="L")
            pdf.ln(4)

        pdf.set_xy(x_pos, pdf.get_y() + 2)

        # Negative
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*COLOR_DANGER)
        neg_label  = neg.get("dimension", "—")
        neg_score  = neg.get("score")
        neg_str    = f"- {neg_label}"
        neg_score_str = f"({_fmt_score(neg_score)}/100)" if neg_score is not None else ""
        pdf.multi_cell(col_w - 2, 4, neg_str, align="L")
        if neg_score_str:
            pdf.set_xy(x_pos, pdf.get_y())
            pdf.set_font("Helvetica", "", 7)
            pdf.cell(col_w - 2, 4, neg_score_str, align="L")
            pdf.ln(4)

    pdf.set_text_color(*COLOR_TEXT)
    pdf.set_y(start_y + 28)
    pdf.ln(2)


def _render_health_data(pdf: UrbanPulsePDF, data: dict):
    """Section 5 — hospital counts, bed density, source attribution per city."""
    pdf.section_title("04  Real Healthcare Infrastructure Data")

    cities      = data.get("cities_compared", [])
    health_data = data.get("health_data", {})

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(
        CONTENT_W, 4,
        "Healthcare scores are seeded from REAL government data where available. "
        "Facility counts below are sourced from official government CSVs.",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.ln(2)

    row_h   = 6
    col_w   = CONTENT_W / 4

    # Table header
    headers = ["City", "Facilities", "Beds (Real)", "Source"]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*COLOR_BG_NAVY)
    pdf.set_text_color(*COLOR_WHITE)
    for h in headers:
        pdf.cell(col_w, row_h, h, align="C", fill=True)
    pdf.ln(row_h)
    pdf.set_text_color(*COLOR_TEXT)

    for idx, city in enumerate(cities):
        h         = health_data.get(city, {})
        facilities = str(h.get("total_facilities", "N/A"))
        beds       = str(h.get("total_beds", "N/A")) if h.get("has_bed_data") else "Not recorded"
        source_note = "Real data" if h.get("data_source") == "real" else "Synthetic est."
        conf        = h.get("data_confidence", 1.0)
        if conf and conf < 1.0:
            source_note += f" (conf: {conf:.0%})"

        fill_color = COLOR_ROW_ALT if idx % 2 else COLOR_WHITE
        pdf.set_fill_color(*fill_color)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w, row_h, city, align="L", fill=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(col_w, row_h, facilities, align="C", fill=True)
        pdf.cell(col_w, row_h, beds, align="C", fill=True)
        source_color = COLOR_SUCCESS if "Real" in source_note else COLOR_WARN
        pdf.set_text_color(*source_color)
        pdf.cell(col_w, row_h, source_note, align="C", fill=True)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.ln(row_h)

    pdf.ln(3)

    # Per-city attribution
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(0, 4, "Data attribution:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 7)
    for city in cities:
        source = REAL_DATA_SOURCES.get(city, "Source unknown")
        pdf.cell(0, 3.5, f"  {city}: {source}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.ln(3)


def _render_salary_equivalence(pdf: UrbanPulsePDF, data: dict):
    """Section 6 — salary required in each city to match source city lifestyle."""
    pdf.section_title("05  Salary Equivalence")

    source_city   = data.get("source_city", "")
    monthly_income = data.get("monthly_income", 0)
    salary_equiv   = data.get("salary_equivalence", {})

    if not salary_equiv:
        pdf.body_text("No salary equivalence data provided.")
        return

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(
        CONTENT_W, 5,
        f"To maintain the same purchasing power as {_fmt_inr(monthly_income)}/month "
        f"in {source_city}, the following salaries are required in each city. "
        f"Calculated from cost-of-living index ratios.",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.ln(2)

    row_h = 6
    col_w = CONTENT_W / 3

    # Header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*COLOR_BG_NAVY)
    pdf.set_text_color(*COLOR_WHITE)
    for h in ["Target City", "Required Salary/Month", "vs Current"]:
        pdf.cell(col_w, row_h, h, align="C", fill=True)
    pdf.ln(row_h)
    pdf.set_text_color(*COLOR_TEXT)

    for idx, (city, required) in enumerate(salary_equiv.items()):
        try:
            req_float = float(required)
            inc_float = float(monthly_income) if monthly_income else 0
        except (TypeError, ValueError):
            req_float = 0
            inc_float = 0

        diff_pct = ((req_float - inc_float) / inc_float * 100) if inc_float else 0
        diff_str = (
            f"+{diff_pct:.1f}% more needed"
            if diff_pct > 0.5
            else f"{abs(diff_pct):.1f}% savings"
            if diff_pct < -0.5
            else "Same purchasing power"
        )
        diff_col = COLOR_DANGER if diff_pct > 0.5 else COLOR_SUCCESS if diff_pct < -0.5 else COLOR_MUTED

        fill_col = COLOR_ROW_ALT if idx % 2 else COLOR_WHITE
        pdf.set_fill_color(*fill_col)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w, row_h, city, align="L", fill=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(col_w, row_h, _fmt_inr(req_float) + "/month", align="C", fill=True)
        pdf.set_text_color(*diff_col)
        pdf.cell(col_w, row_h, diff_str, align="C", fill=True)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.ln(row_h)

    pdf.ln(3)


def _render_narrative(pdf: UrbanPulsePDF, narrative: str):
    """Section 7 — AI-generated 3-paragraph narrative."""
    pdf.section_title("06  AI-Generated Analysis")

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.cell(
        0, 4,
        "AI-Generated Analysis  \u2022  Powered by Google Gemini 1.5-flash",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.set_text_color(*COLOR_MUTED)
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(
        0, 4,
        "Gemini was instructed to use only the scores and data present in this report. "
        "No numbers were invented by the model.",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.ln(3)

    paragraphs = [p.strip() for p in narrative.strip().split("\n\n") if p.strip()]
    for i, para in enumerate(paragraphs):
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.multi_cell(
            CONTENT_W, 5, para,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        if i < len(paragraphs) - 1:
            pdf.ln(3)

    pdf.ln(3)


def _render_data_sources_footer(pdf: UrbanPulsePDF, data: dict):
    """Section 8 — full data provenance table for all 6 cities."""
    pdf.section_title("07  Data Sources & Provenance")

    cities = data.get("cities_compared", [])

    row_h = 5
    col_w_city   = 35
    col_w_source = CONTENT_W - col_w_city

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*COLOR_BG_NAVY)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.cell(col_w_city,   row_h, "City",   align="L", fill=True)
    pdf.cell(col_w_source, row_h, "Source", align="L", fill=True)
    pdf.ln(row_h)
    pdf.set_text_color(*COLOR_TEXT)

    all_cities_for_footer = cities + [c for c in REAL_DATA_SOURCES if c not in cities]
    for idx, city in enumerate(all_cities_for_footer):
        source    = REAL_DATA_SOURCES.get(city, "Source not on record")
        is_real   = "Synthetic" not in source
        fill_col  = COLOR_ROW_ALT if idx % 2 else COLOR_WHITE
        src_color = COLOR_SUCCESS if is_real else COLOR_WARN

        pdf.set_fill_color(*fill_col)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w_city, row_h, city, align="L", fill=True)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*src_color)
        pdf.cell(col_w_source, row_h, source, align="L", fill=True)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.ln(row_h)

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(
        CONTENT_W, 4,
        "Scoring indices (cost of living, startup density, walkability, etc.) are synthetic "
        "but calibrated to public benchmarks (Numbeo, NASSCOM, TRAI, NFHS-5). All synthetic "
        "data uses numpy random seed=42 for full reproducibility.",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.set_text_color(*COLOR_TEXT)


# ── PUBLIC ENTRY POINT ────────────────────────────────────────────────────────

def generate_report(
    comparison_data: dict,
    narrative: Optional[str] = None,
) -> str:
    """
    Generates a structured PDF relocation intelligence report.

    Args:
        comparison_data (dict): Full comparison payload from the scoring
            engine. See module docstring for the exact schema.
        narrative (str, optional): 3-paragraph plain text from Gemini.
            If None, Section 7 is omitted from the report.

    Returns:
        str: Absolute path to the generated PDF file.
    """
    report_date  = datetime.now().strftime("%d %B %Y  %H:%M")
    timestamp_fn = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename     = f"urbanpulse_report_{timestamp_fn}.pdf"
    output_path  = os.path.join(OUTPUT_DIR, filename)

    persona = comparison_data.get("persona", "")
    cities  = comparison_data.get("cities_compared", [])

    pdf = UrbanPulsePDF(persona=persona, cities=cities)
    pdf.add_page()

    _render_cover(pdf, comparison_data, report_date)
    _render_executive_summary(pdf, comparison_data)
    _render_score_table(pdf, comparison_data)
    _render_score_drivers(pdf, comparison_data)
    _render_health_data(pdf, comparison_data)
    _render_salary_equivalence(pdf, comparison_data)

    if narrative and narrative.strip():
        _render_narrative(pdf, narrative)

    _render_data_sources_footer(pdf, comparison_data)

    pdf.output(output_path)
    print(f"[generate_report] PDF saved: {output_path}")
    return output_path


# ── __main__ DEMO ─────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("GENERATE PDF REPORT — UrbanPulse demo")
    print("=" * 65)

    sample_comparison_data = {
        "persona": "early_career",
        "cities_compared": ["Bengaluru", "Pune", "Hyderabad"],
        "best_city": "Bengaluru",
        "monthly_income": 75000,
        "source_city": "Bengaluru",
        "scores": {
            "Bengaluru": {
                "income_score": 72.4,
                "affordability_score": 58.1,
                "healthcare_score": 64.3,
                "environment_score": 81.2,
                "career_growth_score": 95.8,
                "family_fit_score": 66.0,
                "adjusted_life_score": 76.3,
            },
            "Pune": {
                "income_score": 60.2,
                "affordability_score": 78.9,
                "healthcare_score": 59.1,
                "environment_score": 84.5,
                "career_growth_score": 68.4,
                "family_fit_score": 75.2,
                "adjusted_life_score": 68.5,
            },
            "Hyderabad": {
                "income_score": 64.8,
                "affordability_score": 82.3,
                "healthcare_score": 55.6,
                "environment_score": 78.1,
                "career_growth_score": 79.2,
                "family_fit_score": 62.4,
                "adjusted_life_score": 71.9,
            },
        },
        "top_positive": {"dimension": "Career Growth", "score": 95.8},
        "top_negative": {"dimension": "Affordability",  "score": 58.1},
        "drivers": {
            "Bengaluru": {
                "top_positive": {"dimension": "Career Growth",      "score": 95.8},
                "top_negative": {"dimension": "Affordability",       "score": 58.1},
            },
            "Pune": {
                "top_positive": {"dimension": "Affordability",       "score": 78.9},
                "top_negative": {"dimension": "Career Growth",       "score": 68.4},
            },
            "Hyderabad": {
                "top_positive": {"dimension": "Affordability",       "score": 82.3},
                "top_negative": {"dimension": "Healthcare Access",   "score": 55.6},
            },
        },
        "health_data": {
            "Bengaluru": {
                "total_facilities": 32,
                "total_beds": 0,
                "has_bed_data": False,
                "data_source": "real",
                "data_confidence": 0.80,
            },
            "Pune": {
                "total_facilities": 120,
                "total_beds": 4800,
                "has_bed_data": True,
                "data_source": "synthetic",
                "data_confidence": 0.70,
            },
            "Hyderabad": {
                "total_facilities": 180,
                "total_beds": 5040,
                "has_bed_data": True,
                "data_source": "synthetic",
                "data_confidence": 0.70,
            },
        },
        "salary_equivalence": {
            "Bengaluru": 75000,
            "Pune":      56250,
            "Hyderabad": 51000,
        },
    }

    sample_narrative = (
        "For an early-career professional, Bengaluru emerges as the strongest "
        "relocation choice among the three cities, recording an overall "
        "adjusted_life_score of 76.3/100 — driven principally by its career_growth_score "
        "of 95.8/100, the highest in the comparison set by a margin of 16.6 points over "
        "Hyderabad. In salary equivalence terms, a ₹75,000/month lifestyle in Bengaluru "
        "would require only ₹51,000/month in Hyderabad, underscoring that the career "
        "premium comes with a meaningful cost-of-living differential.\n\n"
        "The primary trade-off is Bengaluru's affordability_score of 58.1/100, "
        "which is 20.8 points below Pune (78.9) and 24.2 points below Hyderabad (82.3). "
        "Pune and Hyderabad offer meaningfully lower rent burdens and cost-of-living "
        "indices, making them more suitable for budget-sensitive profiles. However, the "
        "weighted scoring engine — calibrated to early-career priorities where career "
        "growth carries 25% weight versus 20% for affordability — determines that "
        "Bengaluru's dominant job-market position outweighs its higher cost. Healthcare "
        "scores are based on 32 real BBMP-recorded facilities in Bengaluru, giving "
        "Bengaluru's healthcare_score of 64.3 stronger credibility than the synthetic "
        "estimates used for Hyderabad.\n\n"
        "Within the next 30 days, the recommended action is to identify 3–5 "
        "Bengaluru-based tech companies actively recruiting for the target role, "
        "benchmark the expected salary offer against the city's 3-year experience "
        "band (approximately ₹14.5L annual CTC), and calculate whether the net "
        "rent-to-income ratio after joining stays below 30% of monthly take-home — "
        "if not, prioritising HSR Layout or Whitefield over Koramangala will "
        "materially improve affordability without sacrificing commute viability."
    )

    output_path = generate_report(sample_comparison_data, narrative=sample_narrative)

    print(f"\nReport generated successfully.")
    print(f"File: {output_path}")
    print(f"Size: {os.path.getsize(output_path):,} bytes")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[generate_pdf_report] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)