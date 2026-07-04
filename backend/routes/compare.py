"""
backend/routes/compare.py

Endpoints for city comparison and salary equivalence calculation.

POST /compare                    — compare 2-3 cities by persona, returns full
                                   scoring breakdown + recommendation text
POST /compare/salary-equivalence — compute salary required in target city for
                                   equivalent purchasing power
"""

import os
import sys
from typing import Any

from fastapi import APIRouter, HTTPException, Request

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from schemas import (
    CityCompareRequest,
    ComparisonTableResponse,
    CityScoreDetail,
    DimensionDriver,
    SalaryEquivalenceRequest,
    SalaryEquivalenceResponse,
)
from scoring import (
    compute_all_scores,
    get_comparison_table,
    get_recommendation_text,
    get_top_positive_driver,
    get_top_negative_driver,
    compute_salary_equivalence,
)

router = APIRouter()

VALID_CITIES = {
    "Mumbai", "Bengaluru", "Chennai", "Pune", "Delhi", "Hyderabad",
}


def _require_city_df(request: Request):
    city_df = request.app.state.city_df
    if city_df is None or city_df.empty:
        raise HTTPException(
            status_code=503,
            detail="City data not loaded. Run generate_synthetic_data.py and restart the API.",
        )
    return city_df


def _validate_cities(cities: list[str], city_df) -> list[str]:
    """
    Validates that all requested city names exist in the loaded city_df.
    Returns the canonical (correctly-cased) city names matched
    case-insensitively from city_df.
    """
    available = {c.lower(): c for c in city_df["city_name"].tolist()}
    canonical = []
    unknown = []

    for city in cities:
        match = available.get(city.lower())
        if match:
            canonical.append(match)
        else:
            unknown.append(city)

    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown city name(s): {unknown}. "
                   f"Valid cities: {sorted(available.values())}",
        )

    return canonical


# ── POST /compare ─────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ComparisonTableResponse,
    summary="Compare 2-3 cities by persona and return full score breakdown",
)
def compare_cities(
    body: CityCompareRequest,
    request: Request,
) -> ComparisonTableResponse:
    """
    Core comparison endpoint. Accepts 2-3 cities and a persona, runs
    the scoring engine (scoring.py), and returns:
      - Full score breakdown per city (7 dimensions)
      - Best city recommendation
      - Plain-English recommendation text
      - Top positive and negative score drivers for the best city

    All scores are normalized relative to the cities being compared
    (not across all 6 cities), so comparative rankings within the
    selected set are always meaningful.
    """
    city_df = _require_city_df(request)
    canonical_cities = _validate_cities(body.cities, city_df)

    try:
        comparison = get_comparison_table(
            city_list=canonical_cities,
            persona=body.persona,
            city_df=city_df,
            has_children=body.has_children,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    best_city = comparison["best_city"]
    best_city_scores = comparison["scores"][best_city]

    top_positive_dim = comparison["drivers"][best_city]["top_positive"]["dimension"]
    top_positive_score = comparison["drivers"][best_city]["top_positive"]["score"]
    top_negative_dim = comparison["drivers"][best_city]["top_negative"]["dimension"]
    top_negative_score = comparison["drivers"][best_city]["top_negative"]["score"]

    rec_text = get_recommendation_text(
        best_city=best_city,
        persona=body.persona,
        top_positive=(top_positive_dim, top_positive_score),
        top_negative=(top_negative_dim, top_negative_score),
    )

    scores_list = [
        CityScoreDetail(
            city_name=city,
            income_score=data["income_score"],
            affordability_score=data["affordability_score"],
            healthcare_score=data["healthcare_score"],
            environment_score=data["environment_score"],
            career_growth_score=data["career_growth_score"],
            family_fit_score=data["family_fit_score"],
            adjusted_life_score=data["adjusted_life_score"],
        )
        for city, data in comparison["scores"].items()
    ]

    return ComparisonTableResponse(
        persona=body.persona,
        has_children=body.has_children,
        cities_compared=canonical_cities,
        best_city=best_city,
        scores=scores_list,
        recommendation_text=rec_text,
        top_positive=DimensionDriver(
            dimension=top_positive_dim,
            score=top_positive_score,
        ),
        top_negative=DimensionDriver(
            dimension=top_negative_dim,
            score=top_negative_score,
        ),
    )


# ── POST /compare/salary-equivalence ─────────────────────────────────────────

@router.post(
    "/salary-equivalence",
    response_model=SalaryEquivalenceResponse,
    summary="Compute salary required in target city for equivalent purchasing power",
)
def salary_equivalence(
    body: SalaryEquivalenceRequest,
    request: Request,
) -> SalaryEquivalenceResponse:
    """
    Given a salary in source_city, returns the equivalent salary
    required in target_city to maintain the same purchasing power,
    calculated from cost_of_living_index ratios in the city master data.

    Uses the deterministic formula from scoring.compute_salary_equivalence()
    (not the ML model — the ML model is exposed at /recommendations/salary
    for experimentation, but the deterministic version is the authoritative
    value for this endpoint).

    Formula: required = current_salary × (col_target / col_source)
    """
    city_df = _require_city_df(request)
    validated_cities = _validate_cities(
        [body.source_city, body.target_city], city_df
    )
    source_city, target_city = validated_cities[0], validated_cities[1]

    try:
        required_salary = compute_salary_equivalence(
            source_city=source_city,
            target_city=target_city,
            current_salary=body.current_salary,
            city_df=city_df,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    multiplier = round(required_salary / body.current_salary, 4)

    return SalaryEquivalenceResponse(
        source_city=source_city,
        target_city=target_city,
        current_salary=body.current_salary,
        required_salary=required_salary,
        multiplier=multiplier,
    )