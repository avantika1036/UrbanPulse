"""
backend/routes/narrate.py

Endpoints for AI-powered relocation narrative generation via Gemini 1.5-flash.

POST /narrate/relocation   — generate or retrieve cached 3-paragraph narrative
GET  /narrate/cache-stats  — inspect in-memory cache (debug/portfolio use)
DELETE /narrate/cache      — clear the in-memory cache

The 30-second timeout is enforced at the route level via asyncio.wait_for
wrapping the synchronous Gemini call run in a thread pool executor, so the
main event loop is never blocked.
"""

import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException, Request

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from schemas import NarrateRequest, NarrativeResponse
from genai.gemini_narrator import (
    generate_relocation_narrative,
    get_cache_stats,
    clear_cache,
)
from scoring import (
    compute_all_scores,
    get_top_positive_driver,
    get_top_negative_driver,
    compute_salary_equivalence,
)

logger = logging.getLogger("urbanpulse.narrate")
router = APIRouter()

GEMINI_TIMEOUT_SECONDS = 30

# Thread pool for running the synchronous Gemini SDK call without blocking
# the FastAPI event loop. Single worker is sufficient since Gemini calls
# are sequential (caching means repeat calls never hit the API anyway).
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="gemini")

REAL_HEALTH_NOTES = {
    "Bengaluru": "Bengaluru BBMP: 17 Health Centres + 15 UFWCs (32 real facilities, 2001–2024 B&D data)",
    "Mumbai": "Mumbai BMC: 288 hospitals across all 23 wards with real bed counts (full ward coverage)",
    "Chennai": "Chennai GCC: 16 UCHC zones (2018–2025 B&D data, registration completeness tracked)",
    "Pune": "Pune PMC: Annual B&D 1975–2018 + KRA 2017 disease report (IMR: 37.3/1k live births, real)",
    "Delhi": "Delhi State Health Dept: Annual B&D 2017–2024 including third-gender death tracking",
    "Hyderabad": "Hyderabad: No real government source available — all health metrics are synthetic estimates",
}


def _build_comparison_data(
    body: NarrateRequest,
    city_df,
) -> dict:
    """
    Builds the city_comparison_data dict required by
    generate_relocation_narrative() from the NarrateRequest body.

    Computes salary equivalence for all compared cities relative to the
    best city (source), and assembles the real_health_note from the
    canonical provenance map.
    """
    cities_compared = body.cities_compared
    persona = body.persona
    best_city = body.best_city

    if not city_df.empty and set(cities_compared).issubset(set(city_df["city_name"].tolist())):
        subset_df = city_df[city_df["city_name"].isin(cities_compared)].reset_index(drop=True)
        try:
            scores_dict = compute_all_scores(subset_df, persona, has_children=body.has_children)
        except Exception:
            scores_dict = {}
    else:
        scores_dict = {}

    if not scores_dict:
        scores_dict = {
            city: {
                "income_score": 0.0,
                "affordability_score": 0.0,
                "healthcare_score": 0.0,
                "environment_score": 0.0,
                "career_growth_score": 0.0,
                "family_fit_score": 0.0,
                "adjusted_life_score": 0.0,
            }
            for city in cities_compared
        }

    if best_city in scores_dict:
        top_pos = get_top_positive_driver(scores_dict, best_city, persona)
        top_neg = get_top_negative_driver(scores_dict, best_city, persona)
        top_positive_driver = top_pos[0]
        top_negative_driver = top_neg[0]
    else:
        top_positive_driver = body.top_positive_dimension
        top_negative_driver = body.top_negative_dimension

    salary_equivalence = {}
    if body.required_salary_equivalent and not city_df.empty:
        for city in cities_compared:
            if city != best_city:
                try:
                    required = compute_salary_equivalence(
                        source_city=best_city,
                        target_city=city,
                        current_salary=body.monthly_income,
                        city_df=city_df,
                    )
                    salary_equivalence[city] = required
                except Exception:
                    pass
    elif body.required_salary_equivalent:
        for city in cities_compared:
            if city != best_city:
                salary_equivalence[city] = body.required_salary_equivalent

    real_health_parts = [
        REAL_HEALTH_NOTES[city]
        for city in cities_compared
        if city in REAL_HEALTH_NOTES
    ]
    real_health_note = " | ".join(real_health_parts) if real_health_parts else ""

    return {
        "user_persona": persona,
        "selected_cities": cities_compared,
        "scores": scores_dict,
        "recommended_city": best_city,
        "top_positive_driver": top_positive_driver,
        "top_negative_driver": top_negative_driver,
        "salary_equivalence": salary_equivalence,
        "real_health_note": real_health_note,
    }


def _require_city_df(request: Request):
    city_df = request.app.state.city_df
    if city_df is None or city_df.empty:
        raise HTTPException(
            status_code=503,
            detail="City data not loaded. Run generate_synthetic_data.py and restart the API.",
        )
    return city_df


# ── POST /narrate/relocation ─────────────────────────────────────────────────

@router.post(
    "/relocation",
    response_model=NarrativeResponse,
    summary="Generate a 3-paragraph AI relocation narrative via Google Gemini",
)
async def generate_narrative(
    body: NarrateRequest,
    request: Request,
) -> NarrativeResponse:
    """
    Generates a professional 3-paragraph relocation narrative for the
    given city comparison result.

    Paragraph 1: Why the recommended city wins for this persona (with scores).
    Paragraph 2: Key trade-offs vs the other compared cities.
    Paragraph 3: One concrete actionable next step for the user.

    The Gemini call is run in a thread pool executor with a 30-second
    timeout. If the API is unavailable or times out, a clean template
    narrative is returned with model="fallback" — the endpoint never
    returns a 5xx for GenAI failures.

    Responses are cached in-memory by a hash of the input — identical
    comparisons return instantly on subsequent calls.
    """
    try:
        city_df = _require_city_df(request)
    except HTTPException:
        import pandas as pd
        city_df = pd.DataFrame()

    comparison_data = _build_comparison_data(body, city_df)

    loop = asyncio.get_event_loop()

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                generate_relocation_narrative,
                comparison_data,
            ),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            f"[narrate] Gemini call timed out after {GEMINI_TIMEOUT_SECONDS}s — "
            f"returning fallback narrative."
        )
        from genai.gemini_narrator import _build_fallback_narrative
        fallback_text = _build_fallback_narrative(comparison_data)
        result = {
            "narrative": fallback_text,
            "cached": False,
            "model": "fallback (timeout)",
        }
    except Exception as e:
        logger.error(f"[narrate] Unexpected error in narrative generation: {e}")
        from genai.gemini_narrator import _build_fallback_narrative
        fallback_text = _build_fallback_narrative(comparison_data)
        result = {
            "narrative": fallback_text,
            "cached": False,
            "model": "fallback (error)",
        }

    return NarrativeResponse(
        narrative=result["narrative"],
        cached=result.get("cached", False),
        model=result.get("model", "unknown"),
    )


# ── GET /narrate/cache-stats ─────────────────────────────────────────────────

@router.get(
    "/cache-stats",
    summary="In-memory narrative cache statistics (debug)",
)
def cache_stats() -> dict[str, Any]:
    """
    Returns the number of cached narratives and the model(s) used to
    generate them. Useful for verifying the cache is working correctly
    during a portfolio demo.
    """
    stats = get_cache_stats()
    return {
        "status": "ok",
        **stats,
    }


# ── DELETE /narrate/cache ────────────────────────────────────────────────────

@router.delete(
    "/cache",
    summary="Clear the in-memory narrative cache",
)
def clear_narrative_cache() -> dict[str, Any]:
    """
    Clears all cached narratives from memory. Useful when testing
    different prompts or after changing the scoring engine weights.
    """
    cleared = clear_cache()
    return {
        "status": "ok",
        "entries_cleared": cleared,
    }