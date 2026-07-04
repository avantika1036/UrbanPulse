"""
backend/genai/gemini_narrator.py

Generates plain-English relocation narratives using Google Gemini 1.5-flash.

Key design decisions:
  1. In-memory cache keyed by a SHA-256 hash of the serialised input dict,
     so identical comparisons never hit the API twice in the same process
     lifetime. The cache is intentionally process-local (no Redis, no file)
     — keeping the dependency footprint minimal for a portfolio project.

  2. Hard fallback: if the Gemini API call fails for any reason (rate limit,
     bad key, network error), generate_relocation_narrative() returns a
     structured template string built from the input data instead of raising
     an exception. The route layer sets NarrativeResponse.model to "fallback"
     so the frontend can show a subtle indicator.

  3. The prompt explicitly forbids number invention — Gemini is instructed to
     use only the scores and salary figures present in the input dict. This
     is critical for a data-integrity-conscious product-analyst portfolio.

Usage:
    from genai.gemini_narrator import generate_relocation_narrative
    result = generate_relocation_narrative(city_comparison_data)
    # result: {"narrative": str, "cached": bool, "model": str}
"""

import os
import json
import hashlib
import logging
from typing import Optional

logger = logging.getLogger("urbanpulse.gemini")

# ── GEMINI SETUP ─────────────────────────────────────────────────────────────

GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_AVAILABLE = False

try:
    import google.generativeai as genai  # type: ignore

    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        logger.info(f"[gemini_narrator] Gemini configured with model={GEMINI_MODEL}")
    else:
        logger.warning(
            "[gemini_narrator] GEMINI_API_KEY not set — all calls will use "
            "the template fallback. Set GEMINI_API_KEY in your .env file."
        )
except ImportError:
    logger.warning(
        "[gemini_narrator] google-generativeai package not installed. "
        "Run: pip install google-generativeai. Fallback mode active."
    )
    genai = None  # type: ignore

# ── IN-MEMORY CACHE ───────────────────────────────────────────────────────────
# Dict keyed by SHA-256 hex of the JSON-serialised input.
# Value: {"narrative": str, "model": str}
_NARRATIVE_CACHE: dict[str, dict] = {}


def _cache_key(city_comparison_data: dict) -> str:
    """
    Produces a deterministic cache key for a city_comparison_data dict by
    JSON-serialising it with sorted keys, then SHA-256 hashing the result.
    This ensures that two dicts with the same content but different key
    insertion orders produce the same cache key.
    """
    serialised = json.dumps(city_comparison_data, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


# ── PROMPT BUILDER ────────────────────────────────────────────────────────────

def _build_prompt(data: dict) -> str:
    """
    Builds the Gemini prompt from city_comparison_data.

    Strict instructions are embedded to prevent number invention and to
    enforce exactly 3 paragraphs. The prompt is designed to produce
    professional, data-grounded prose suitable for a product-analyst
    portfolio showcase.
    """
    persona = data.get("user_persona", "professional")
    cities = data.get("selected_cities", [])
    scores = data.get("scores", {})
    recommended = data.get("recommended_city", "")
    top_positive = data.get("top_positive_driver", "")
    top_negative = data.get("top_negative_driver", "")
    salary_equiv = data.get("salary_equivalence", {})
    real_health_note = data.get("real_health_note", "")

    persona_labels = {
        "early_career": "an early-career professional (22–30 years, prioritises job market and affordability)",
        "family_focused": "a family-focused relocator (prioritises healthcare, schools, and safety)",
        "budget_focused": "a budget-focused relocator (primary priority is minimising cost of living)",
    }
    persona_phrase = persona_labels.get(persona, f"a {persona.replace('_', '-')} professional")

    scores_text = []
    for city in cities:
        city_scores = scores.get(city, {})
        if city_scores:
            scores_text.append(
                f"  {city}:\n"
                f"    - Overall (adjusted_life_score): {city_scores.get('adjusted_life_score', 'N/A')}\n"
                f"    - Income vs CoL: {city_scores.get('income_score', 'N/A')}\n"
                f"    - Affordability: {city_scores.get('affordability_score', 'N/A')}\n"
                f"    - Healthcare: {city_scores.get('healthcare_score', 'N/A')}\n"
                f"    - Environment: {city_scores.get('environment_score', 'N/A')}\n"
                f"    - Career Growth: {city_scores.get('career_growth_score', 'N/A')}\n"
                f"    - Family Fit: {city_scores.get('family_fit_score', 'N/A')}"
            )
    scores_block = "\n".join(scores_text) if scores_text else "  (No score data provided)"

    salary_text = ""
    if salary_equiv:
        lines = [
            f"  {city}: ₹{int(required_salary):,}/month"
            for city, required_salary in salary_equiv.items()
        ]
        salary_text = "Salary equivalence (same purchasing power):\n" + "\n".join(lines)

    health_text = ""
    if real_health_note:
        health_text = f"Real healthcare infrastructure data:\n  {real_health_note}"

    prompt = f"""You are a professional relocation advisor specialising in Indian cities. \
Your clients are young Indian professionals making data-driven relocation decisions.

You have been given the following structured comparison data for {persona_phrase}. \
Write a relocation narrative based STRICTLY on the data provided. \
Do NOT invent any numbers, percentages, or facts not present in the input below.

===== INPUT DATA =====

Cities compared: {', '.join(cities)}
Recommended city: {recommended}
Persona: {persona}
Top strength of recommended city: {top_positive}
Main trade-off of recommended city: {top_negative}

Score breakdown (all scores normalised 0–100 relative to compared cities):
{scores_block}

{salary_text}

{health_text}

===== WRITING INSTRUCTIONS =====

Write a 3-paragraph narrative explaining the city recommendation. Use plain prose with no headers or bullet points. Separate paragraphs with blank lines.

Paragraph 1: Explain why {recommended} is the top recommendation for this persona. Reference specific scores from the data (e.g. "career_growth_score of XX.X", "affordability_score of XX.X") and explain what they mean for this persona's priorities. Include salary equivalence data if available.

Paragraph 2: Discuss key trade-offs honestly. If another city scores higher on dimensions that matter to this persona, acknowledge it and explain why {recommended} still wins overall. Use score differences to quantify trade-offs. Reference healthcare data if present.

Paragraph 3: Give one concrete, actionable next step the user should take within 30 days, specific to their persona and the recommended city. Make it practical advice (e.g., negotiate a specific salary range, visit specific areas for housing).

Tone: Professional, data-grounded, confident but balanced. Write in third person. Avoid phrases like "Congratulations!", "Amazing!", "I hope". Do not start paragraphs with "In conclusion" or "To summarise".
"""
    return prompt.strip()


# ── FALLBACK TEMPLATE ─────────────────────────────────────────────────────────

def _build_fallback_narrative(data: dict) -> str:
    """
    Generates a structured template narrative from input data when the
    Gemini API call fails. Uses only data present in the input dict.
    Returns a 3-paragraph plain string that reads naturally.
    """
    persona = data.get("user_persona", "professional")
    cities = data.get("selected_cities", [])
    recommended = data.get("recommended_city", "")
    top_positive = data.get("top_positive_driver", "")
    top_negative = data.get("top_negative_driver", "")
    scores = data.get("scores", {})
    salary_equiv = data.get("salary_equivalence", {})

    persona_labels = {
        "early_career": "an early-career professional",
        "family_focused": "a family-focused relocator",
        "budget_focused": "a budget-focused relocator",
    }
    persona_phrase = persona_labels.get(persona, "a professional")

    rec_scores = scores.get(recommended, {})
    overall_score = rec_scores.get("adjusted_life_score")
    top_driver_score = None
    driver_key_map = {
        "Income vs. Cost of Living": "income_score",
        "Affordability": "affordability_score",
        "Healthcare Access": "healthcare_score",
        "Environment & Pollution": "environment_score",
        "Career Growth": "career_growth_score",
        "Family Fit": "family_fit_score",
    }
    driver_key = driver_key_map.get(top_positive)
    if driver_key:
        top_driver_score = rec_scores.get(driver_key)

    other_cities = [c for c in cities if c != recommended]
    other_city_str = " and ".join(other_cities) if other_cities else "other cities"

    salary_sentence = ""
    if salary_equiv:
        for city, required in salary_equiv.items():
            if city != recommended:
                salary_sentence = (
                    f" In salary terms, ₹{int(required):,}/month in {city} is required "
                    f"to match the same purchasing power available in {recommended}."
                )
                break

    overall_str = f"{overall_score:.1f}/100" if overall_score is not None else "the highest"
    driver_str = (
        f"{top_positive} score of {top_driver_score:.1f}/100"
        if top_driver_score is not None
        else f"strong {top_positive}"
    )

    para1 = (
        f"For {persona_phrase}, {recommended} emerges as the strongest choice among "
        f"{', '.join(cities)}, recording an overall adjusted_life_score of {overall_str}. "
        f"The city's {driver_str} is the primary contributor to this outcome, "
        f"directly aligning with the most important priorities for this persona.{salary_sentence} "
        f"This combination of scores makes {recommended} the most practical relocation "
        f"option given the stated preferences."
    )

    para2 = (
        f"The comparison with {other_city_str} reveals meaningful trade-offs. "
        f"The main limitation of {recommended} is its {top_negative} performance, "
        f"which scores below the comparison set average — a factor worth weighing "
        f"carefully depending on individual circumstances. "
        f"However, the weighted scoring engine, calibrated to this persona's priorities, "
        f"determines that {recommended}'s strengths in {top_positive} outweigh this shortfall. "
        f"Where available, healthcare scores are grounded in real government facility data "
        f"(BBMP, BMC, GCC, PMC), adding credibility to the comparison."
    )

    persona_next_steps = {
        "early_career": (
            f"The immediate next step is to identify 3–5 companies in {recommended}'s "
            f"tech or finance corridor that are actively hiring for the relevant role, "
            f"benchmark the expected salary range against the city's fresher and "
            f"3-year-experience salary bands, and initiate applications within the next "
            f"30 days before the next campus hiring cycle begins."
        ),
        "family_focused": (
            f"Within the next 30 days, identify 2–3 residential neighbourhoods in "
            f"{recommended} that fall within a 5km radius of both a quality school "
            f"(using the school_quality_index sub-score as a guide) and a public or "
            f"municipal hospital — then request a 2-day in-person visit to evaluate "
            f"commute times and housing costs before signing any employment offer."
        ),
        "budget_focused": (
            f"The concrete next step is to calculate the exact rent-to-income ratio "
            f"for a 1BHK in {recommended} using the current average monthly rent figure, "
            f"verify that it stays below 30% of the offered monthly salary, and use "
            f"the salary equivalence calculator to confirm that the offer represents "
            f"a genuine purchasing-power improvement over the current city."
        ),
    }
    para3 = persona_next_steps.get(
        persona,
        f"The recommended next step is to visit {recommended} for a 2-day in-person "
        f"assessment, focusing specifically on the dimensions where the city scored "
        f"lowest, to validate whether the data-driven recommendation aligns with "
        f"personal experience before committing to a relocation decision.",
    )

    return f"{para1}\n\n{para2}\n\n{para3}"


# ── MAIN PUBLIC FUNCTION ──────────────────────────────────────────────────────

def generate_relocation_narrative(city_comparison_data: dict) -> dict:
    """
    Generates a 3-paragraph plain-English relocation narrative for the
    given city comparison data.

    Args:
        city_comparison_data (dict): Must contain:
            user_persona (str): "early_career" | "family_focused" | "budget_focused"
            selected_cities (list[str]): cities being compared
            scores (dict): {city_name: {income_score, affordability_score,
                healthcare_score, environment_score, career_growth_score,
                family_fit_score, adjusted_life_score}}
            recommended_city (str): top-recommended city name
            top_positive_driver (str): human-readable dimension label
            top_negative_driver (str): human-readable dimension label
            salary_equivalence (dict, optional): {city: required_salary}
            real_health_note (str, optional): provenance note for healthcare scores

    Returns:
        dict: {
            "narrative": str — 3-paragraph plain prose,
            "cached": bool — True if served from in-memory cache,
            "model": str — "gemini-1.5-flash", "fallback", or "cached"
        }
    """
    cache_key = _cache_key(city_comparison_data)

    if cache_key in _NARRATIVE_CACHE:
        cached_entry = _NARRATIVE_CACHE[cache_key]
        logger.info("[gemini_narrator] Cache hit — returning cached narrative.")
        return {
            "narrative": cached_entry["narrative"],
            "cached": True,
            "model": cached_entry["model"],
        }

    if not GEMINI_AVAILABLE or genai is None:
        logger.info("[gemini_narrator] Gemini unavailable — using fallback template.")
        narrative = _build_fallback_narrative(city_comparison_data)
        result = {"narrative": narrative, "cached": False, "model": "fallback"}
        _NARRATIVE_CACHE[cache_key] = {"narrative": narrative, "model": "fallback"}
        return result

    prompt = _build_prompt(city_comparison_data)

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)

        generation_config = genai.types.GenerationConfig(
            temperature=0.4,  # low temperature = more factual, less creative
            max_output_tokens=4096,  # Maximum to ensure complete 3-paragraph narratives
            top_p=0.85,
        )

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        narrative = response.text.strip()

        if not narrative:
            raise ValueError("Gemini returned an empty response.")

        # Log completion reason for debugging
        if hasattr(response, 'candidates') and response.candidates:
            finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'unknown'
            logger.info(
                f"[gemini_narrator] Narrative generated successfully "
                f"({len(narrative)} chars) via {GEMINI_MODEL}. "
                f"Finish reason: {finish_reason}"
            )
        else:
            logger.info(
                f"[gemini_narrator] Narrative generated successfully "
                f"({len(narrative)} chars) via {GEMINI_MODEL}."
            )

        result = {"narrative": narrative, "cached": False, "model": GEMINI_MODEL}
        _NARRATIVE_CACHE[cache_key] = {"narrative": narrative, "model": GEMINI_MODEL}
        return result

    except Exception as e:
        logger.error(
            f"[gemini_narrator] Gemini API call failed: {e}. "
            f"Returning template fallback."
        )
        narrative = _build_fallback_narrative(city_comparison_data)
        result = {"narrative": narrative, "cached": False, "model": "fallback"}
        _NARRATIVE_CACHE[cache_key] = {"narrative": narrative, "model": "fallback"}
        return result


def get_cache_stats() -> dict:
    """
    Returns basic stats about the in-memory narrative cache.
    Exposed via the /narrate/ router for debugging.
    """
    return {
        "cached_entries": len(_NARRATIVE_CACHE),
        "models_in_cache": list({v["model"] for v in _NARRATIVE_CACHE.values()}),
    }


def clear_cache() -> int:
    """Clears the in-memory narrative cache. Returns number of entries cleared."""
    count = len(_NARRATIVE_CACHE)
    _NARRATIVE_CACHE.clear()
    logger.info(f"[gemini_narrator] Cache cleared — {count} entries removed.")
    return count