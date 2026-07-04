"""
backend/routes/analytics.py

Endpoints for aggregate analytics and real-data health summaries.

GET /analytics/overview              — avg scores per city across personas, ranking table
GET /analytics/real-health-summary   — real births/deaths/hospital data summary
GET /analytics/persona-rankings/{persona} — city rankings for one persona
"""

import os
import sys
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from database import get_db
from models import CityHealthSummary, CityHospitalCount
from scoring import compute_all_scores, VALID_PERSONAS

router = APIRouter()


def _require_city_df(request: Request) -> pd.DataFrame:
    city_df = request.app.state.city_df
    if city_df is None or city_df.empty:
        raise HTTPException(
            status_code=503,
            detail="City data not loaded. Run generate_synthetic_data.py and restart the API.",
        )
    return city_df


# ── GET /analytics/overview ──────────────────────────────────────────────────

@router.get("/overview", summary="Average scores per city across all personas")
def analytics_overview(request: Request) -> dict[str, Any]:
    """
    Computes scores for all 6 cities across all 3 personas and returns:
      - Per-city average adjusted_life_score (across personas)
      - Per-dimension average per city
      - Overall city ranking by average adjusted_life_score

    All scores normalized across the full 6-city set for each persona,
    then averaged across personas for the overview ranking.
    """
    city_df = _require_city_df(request)

    all_persona_scores = {}
    for persona in VALID_PERSONAS:
        scores = compute_all_scores(city_df, persona, has_children=False)
        all_persona_scores[persona] = scores

    city_names = city_df["city_name"].tolist()

    dimensions = [
        "income_score", "affordability_score", "healthcare_score",
        "environment_score", "career_growth_score", "family_fit_score",
        "adjusted_life_score",
    ]

    per_city_summary = []
    for city in city_names:
        city_entry: dict[str, Any] = {"city_name": city}

        for dim in dimensions:
            values = [
                all_persona_scores[persona][city][dim]
                for persona in VALID_PERSONAS
                if city in all_persona_scores[persona]
            ]
            city_entry[f"avg_{dim}"] = round(sum(values) / len(values), 2) if values else 0.0

        city_entry["scores_by_persona"] = {
            persona: all_persona_scores[persona].get(city, {})
            for persona in VALID_PERSONAS
        }

        per_city_summary.append(city_entry)

    per_city_summary.sort(key=lambda x: x["avg_adjusted_life_score"], reverse=True)
    for rank, entry in enumerate(per_city_summary, start=1):
        entry["overall_rank"] = rank

    return {
        "total_cities": len(per_city_summary),
        "personas_used": sorted(VALID_PERSONAS),
        "methodology_note": (
            "Scores normalized 0-100 within each persona comparison across all 6 cities. "
            "Average score is mean across all 3 personas. Healthcare scores seeded from "
            "real government data for Bengaluru, Mumbai, Chennai."
        ),
        "city_rankings": per_city_summary,
    }


# ── GET /analytics/real-health-summary ──────────────────────────────────────

@router.get(
    "/real-health-summary",
    summary="Real births/deaths and hospital data summary across all cities",
)
def real_health_summary(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns a summary of real government data held in the database:
      - city_health_summary table: latest year available per city,
        total births, total deaths, crude death rate
      - city_hospital_counts table: facilities, beds, public/private split
        with data confidence ratings

    Cities without real data (Mumbai births/deaths, Hyderabad both)
    are explicitly flagged.
    """
    # Latest non-partial-year health record per city
    latest_health_subq = (
        db.query(
            CityHealthSummary.city_name,
            func.max(CityHealthSummary.year).label("latest_year"),
        )
        .filter(CityHealthSummary.partial_year == False)  # noqa: E712
        .group_by(CityHealthSummary.city_name)
        .subquery()
    )

    latest_health_rows = (
        db.query(CityHealthSummary)
        .join(
            latest_health_subq,
            (CityHealthSummary.city_name == latest_health_subq.c.city_name) &
            (CityHealthSummary.year == latest_health_subq.c.latest_year),
        )
        .all()
    )

    health_summary = [
        {
            "city_name": r.city_name,
            "latest_year": r.year,
            "total_births": r.total_births,
            "total_deaths": r.total_deaths,
            "crude_death_rate_per_1000": float(r.crude_death_rate_per_1000) if r.crude_death_rate_per_1000 else None,
            "crude_birth_rate_per_1000": float(r.crude_birth_rate_per_1000) if r.crude_birth_rate_per_1000 else None,
            "infant_mortality": r.infant_mortality,
            "data_source": r.data_source,
        }
        for r in latest_health_rows
    ]

    hospital_rows = db.query(CityHospitalCount).all()
    hospital_summary = [
        {
            "city_name": r.city_name,
            "total_facilities": r.total_facilities,
            "total_beds": r.total_beds,
            "public_count": r.public_count,
            "private_count": r.private_count,
            "has_bed_data": r.has_bed_data,
            "data_confidence": float(r.data_confidence),
            "data_source": r.data_source,
        }
        for r in hospital_rows
    ]

    cities_with_health = {r["city_name"] for r in health_summary}
    cities_with_hospitals = {r["city_name"] for r in hospital_summary}
    all_cities = {"Mumbai", "Bengaluru", "Chennai", "Pune", "Delhi", "Hyderabad"}

    return {
        "real_data_coverage": {
            "annual_births_deaths": sorted(cities_with_health),
            "hospital_facility_counts": sorted(cities_with_hospitals),
            "no_real_data": sorted(all_cities - cities_with_health - cities_with_hospitals),
        },
        "annual_health_summary": health_summary,
        "hospital_summary": hospital_summary,
    }


# ── GET /analytics/persona-rankings/{persona} ────────────────────────────────

@router.get(
    "/persona-rankings/{persona}",
    summary="City rankings for a specific persona",
)
def persona_rankings(
    persona: str,
    request: Request,
    has_children: bool = False,
) -> dict[str, Any]:
    """
    Returns all 6 cities ranked by adjusted_life_score for the given
    persona, with the full 7-dimension breakdown per city.

    Query param:
      has_children (bool, default False) — applies the +5 family_fit
        modifier when True (most relevant for family_focused persona).
    """
    if persona not in VALID_PERSONAS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid persona '{persona}'. Must be one of: {sorted(VALID_PERSONAS)}",
        )

    city_df = _require_city_df(request)

    try:
        scores = compute_all_scores(city_df, persona, has_children=has_children)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    ranked = sorted(
        scores.items(),
        key=lambda kv: (-kv[1]["adjusted_life_score"], kv[0]),
    )

    rankings = [
        {
            "rank": idx + 1,
            "city_name": city,
            **score_data,
        }
        for idx, (city, score_data) in enumerate(ranked)
    ]

    top_city = rankings[0]["city_name"] if rankings else None
    best_dimension = None
    if top_city:
        dim_scores = {
            k: v for k, v in rankings[0].items()
            if k.endswith("_score") and k != "adjusted_life_score"
        }
        best_dimension = max(dim_scores, key=dim_scores.get) if dim_scores else None

    return {
        "persona": persona,
        "has_children": has_children,
        "top_city": top_city,
        "top_dimension_for_leader": best_dimension,
        "rankings": rankings,
    }