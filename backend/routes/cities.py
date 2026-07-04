"""
backend/routes/cities.py

Endpoints exposing city reference data, scores, monthly trends, and
real health statistics.

GET /cities                          — list all 6 cities with key stats
GET /cities/{city_name}              — full city profile + all 3 persona scores
GET /cities/{city_name}/monthly-trends — last 12 months of time-series metrics
GET /cities/{city_name}/health       — real births/deaths + hospital data
"""

import os
import sys
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from database import get_db
from models import CityHealthSummary, CityHospitalCount, MonthlyCityMetric
from scoring import compute_all_scores, VALID_PERSONAS

router = APIRouter()

PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")


def _get_city_df(request: Request) -> pd.DataFrame:
    """Pulls city_df from app.state; raises 503 if not loaded."""
    city_df = request.app.state.city_df
    if city_df is None or city_df.empty:
        raise HTTPException(
            status_code=503,
            detail="City data not yet loaded. Run generate_synthetic_data.py and restart the API.",
        )
    return city_df


def _get_city_row(city_df: pd.DataFrame, city_name: str) -> pd.Series:
    """Returns a single city row; raises 404 if not found."""
    row = city_df[city_df["city_name"].str.lower() == city_name.lower()]
    if row.empty:
        available = sorted(city_df["city_name"].tolist())
        raise HTTPException(
            status_code=404,
            detail=f"City '{city_name}' not found. Available cities: {available}",
        )
    return row.iloc[0]


# ── GET /cities ──────────────────────────────────────────────────────────────

@router.get("/", summary="List all cities with key stats")
def list_cities(request: Request) -> list[dict[str, Any]]:
    """
    Returns a summary list of all 6 covered cities, including key stats
    used in the comparison cards on the frontend landing page.
    """
    city_df = _get_city_df(request)

    result = []
    for _, row in city_df.iterrows():
        result.append({
            "city_id": int(row["city_id"]),
            "city_name": row["city_name"],
            "state": row["state"],
            "region": row["region"],
            "avg_monthly_rent_1bhk": float(row["avg_monthly_rent_1bhk"]),
            "avg_monthly_rent_2bhk": float(row["avg_monthly_rent_2bhk"]),
            "avg_salary_fresher": float(row["avg_salary_fresher"]),
            "cost_of_living_index": float(row["cost_of_living_index"]),
            "pollution_aqi_avg": float(row["pollution_aqi_avg"]),
            "hospital_beds_per_lakh": float(row["hospital_beds_per_lakh"]),
        })

    return result


# ── GET /cities/{city_name} ──────────────────────────────────────────────────

@router.get("/{city_name}", summary="Full city profile with all persona scores")
def get_city_profile(city_name: str, request: Request) -> dict[str, Any]:
    """
    Returns the full city profile including all attributes from city_master.csv
    plus the computed 7-dimension scores for all three personas.
    Scores are computed fresh on each request (sub-millisecond operation —
    no DB write needed for a single city lookup).
    """
    city_df = _get_city_df(request)
    city_row = _get_city_row(city_df, city_name)

    profile = city_row.to_dict()
    # Convert numpy types to Python native for JSON serialization
    profile = {k: (float(v) if hasattr(v, "item") else v) for k, v in profile.items()}

    # Compute scores for all 3 personas relative to the full 6-city set
    # (so scores reflect standing across ALL cities, not just this one)
    scores_by_persona = {}
    for persona in VALID_PERSONAS:
        all_scores = compute_all_scores(city_df, persona, has_children=False)
        scores_by_persona[persona] = all_scores.get(city_row["city_name"], {})

    return {
        "city_profile": profile,
        "scores_by_persona": scores_by_persona,
    }


# ── GET /cities/{city_name}/monthly-trends ───────────────────────────────────

@router.get(
    "/{city_name}/monthly-trends",
    summary="Last 12 months of time-series metrics for a city",
)
def get_monthly_trends(
    city_name: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns the 12 most recent months of synthetic monthly metrics for
    the requested city, sorted ascending by year_month. Used to power
    TrendChart components on the frontend.
    """
    city_df = _get_city_df(request)
    city_row = _get_city_row(city_df, city_name)  # validates city name

    # Pull last 12 months ordered by year_month descending, then re-sort ascending for chart display
    rows = (
        db.query(MonthlyCityMetric)
        .filter(MonthlyCityMetric.city_name == city_row["city_name"])
        .order_by(MonthlyCityMetric.year_month.desc())
        .limit(12)
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No monthly metrics found for '{city_name}'. "
                   f"Run scripts/load_database.py to populate monthly_city_metrics.",
        )

    rows_sorted = sorted(rows, key=lambda r: r.year_month)

    trend_data = [
        {
            "year_month": r.year_month,
            "avg_aqi": float(r.avg_aqi),
            "avg_rent_1bhk": float(r.avg_rent_1bhk),
            "avg_rent_2bhk": float(r.avg_rent_2bhk),
            "job_postings_index": float(r.job_postings_index),
            "avg_salary_offered": float(r.avg_salary_offered),
            "cost_of_living_index": float(r.cost_of_living_index),
            "hospital_utilization_rate": float(r.hospital_utilization_rate),
            "disease_outbreak_flag": bool(r.disease_outbreak_flag),
            "rainfall_mm": float(r.rainfall_mm),
            "temperature_avg": float(r.temperature_avg),
        }
        for r in rows_sorted
    ]

    return {
        "city_name": city_row["city_name"],
        "months_returned": len(trend_data),
        "trends": trend_data,
    }


# ── GET /cities/{city_name}/health ───────────────────────────────────────────

@router.get(
    "/{city_name}/health",
    summary="Real health data: births, deaths, hospital counts",
)
def get_city_health(
    city_name: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns real-data health statistics for the requested city:
      - Annual births and deaths (from data/real/ CSVs, loaded into
        city_health_summary table). Available for Bengaluru, Chennai,
        Delhi, Pune. Returns empty list for Mumbai/Hyderabad (no real source).
      - Hospital/facility counts (from city_hospital_counts table).
        Available for Bengaluru, Mumbai, Chennai.

    All data tagged with data_source field so frontend can show
    'Real data' vs 'Estimated' badges.
    """
    city_df = _get_city_df(request)
    city_row = _get_city_row(city_df, city_name)
    canonical_name = city_row["city_name"]

    # Annual births/deaths
    health_rows = (
        db.query(CityHealthSummary)
        .filter(CityHealthSummary.city_name == canonical_name)
        .filter(CityHealthSummary.partial_year == False)  # noqa: E712
        .order_by(CityHealthSummary.year.desc())
        .limit(10)
        .all()
    )

    health_data = [
        {
            "year": r.year,
            "total_births": r.total_births,
            "total_deaths": r.total_deaths,
            "births_male": r.births_male,
            "births_female": r.births_female,
            "deaths_male": r.deaths_male,
            "deaths_female": r.deaths_female,
            "crude_death_rate": float(r.crude_death_rate) if r.crude_death_rate is not None else None,
            "crude_death_rate_per_1000": float(r.crude_death_rate_per_1000) if r.crude_death_rate_per_1000 is not None else None,
            "crude_birth_rate_per_1000": float(r.crude_birth_rate_per_1000) if r.crude_birth_rate_per_1000 is not None else None,
            "infant_mortality": r.infant_mortality,
            "data_source": r.data_source,
        }
        for r in health_rows
    ]

    # Hospital / facility counts
    hospital_row = (
        db.query(CityHospitalCount)
        .filter(CityHospitalCount.city_name == canonical_name)
        .first()
    )

    hospital_data = None
    if hospital_row:
        hospital_data = {
            "total_facilities": hospital_row.total_facilities,
            "total_beds": hospital_row.total_beds,
            "has_bed_data": hospital_row.has_bed_data,
            "public_count": hospital_row.public_count,
            "private_count": hospital_row.private_count,
            "data_source": hospital_row.data_source,
            "data_confidence": float(hospital_row.data_confidence),
            "hospital_beds_per_lakh": float(city_row["hospital_beds_per_lakh"]),
            "health_centres_per_lakh": float(city_row["health_centres_per_lakh"]),
        }

    return {
        "city_name": canonical_name,
        "annual_health_data": {
            "years_available": len(health_data),
            "data_source_note": (
                "Real government data" if health_data else
                "No real annual data available for this city — "
                "crude_death_rate in city profile is a synthetic estimate"
            ),
            "records": health_data,
        },
        "hospital_data": {
            "data_source_note": (
                "Real government data" if hospital_data else
                "No real facility data available for this city — "
                "hospital_beds_per_lakh in city profile is a manual estimate"
            ),
            "counts": hospital_data,
        },
    }