"""
backend/scoring.py

Core scoring engine for UrbanPulse.

Computes 7 normalized (0-100) score dimensions per city per persona,
using pandas/numpy only (no ML libraries — this module is pure
deterministic, explainable arithmetic). All functions here are designed
to be imported directly by FastAPI route handlers in backend/routes/.

Score dimensions:
  1. income_score          — salary tier vs cost of living
  2. affordability_score   — rent burden + cost of living (inverted, higher = cheaper)
  3. healthcare_score       — bed density, facility density, inverse death rate
  4. environment_score      — inverse pollution + green space
  5. career_growth_score    — job market + startup ecosystem + salary growth
  6. family_fit_score       — schools, safety, healthcare, children modifier
  7. adjusted_life_score    — persona-weighted composite of dimensions 1-6

All inputs are expected as a pandas DataFrame with (at minimum) the
columns produced by urbanpulse.cities (see sql/schema.sql) joined with
monthly_city_metrics aggregates where relevant. See compute_all_scores()
docstring for the exact expected column list.
"""

import numpy as np
import pandas as pd


# ── PERSONA WEIGHTS ──────────────────────────────────────────────────────────

PERSONA_WEIGHTS = {
    "early_career": {
        "income": 0.30, "career": 0.25, "affordability": 0.20,
        "environment": 0.10, "healthcare": 0.10, "family": 0.05,
    },
    "family_focused": {
        "family": 0.30, "healthcare": 0.25, "affordability": 0.20,
        "environment": 0.15, "income": 0.10, "career": 0.00,
    },
    "budget_focused": {
        "affordability": 0.35, "income": 0.25, "environment": 0.20,
        "healthcare": 0.10, "family": 0.05, "career": 0.05,
    },
}

# Maps the internal dimension keys above to the actual score column names
DIMENSION_TO_SCORE_COLUMN = {
    "income": "income_score",
    "affordability": "affordability_score",
    "healthcare": "healthcare_score",
    "environment": "environment_score",
    "career": "career_growth_score",
    "family": "family_fit_score",
}

VALID_PERSONAS = set(PERSONA_WEIGHTS.keys())

# Human-readable labels for driver explanations
DIMENSION_LABELS = {
    "income_score": "Income vs. Cost of Living",
    "affordability_score": "Affordability",
    "healthcare_score": "Healthcare Access",
    "environment_score": "Environment & Pollution",
    "career_growth_score": "Career Growth",
    "family_fit_score": "Family Fit",
}


# ── NORMALIZATION ────────────────────────────────────────────────────────────

def normalize_scores(df, columns=None):
    """
    Min-max normalizes the given columns of a DataFrame to a 0-100 scale,
    computed ACROSS the rows present (i.e. relative to the set of cities
    passed in, not against a fixed global scale).

    Args:
        df (pd.DataFrame): DataFrame containing raw numeric columns to normalize.
        columns (list[str], optional): Column names to normalize. If None,
            normalizes all numeric columns in the DataFrame.

    Returns:
        pd.DataFrame: A copy of df with the specified columns replaced by
            their 0-100 normalized values. If a column has zero variance
            (all values identical), it is set to 50.0 for every row
            (neutral midpoint — avoids divide-by-zero and avoids implying
            a false ranking among identical values).
    """
    out = df.copy()

    if columns is None:
        columns = out.select_dtypes(include=[np.number]).columns.tolist()

    for col in columns:
        if col not in out.columns:
            continue

        col_min = out[col].min()
        col_max = out[col].max()

        if pd.isna(col_min) or pd.isna(col_max):
            out[col] = 50.0
            continue

        if col_max == col_min:
            out[col] = 50.0
        else:
            out[col] = ((out[col] - col_min) / (col_max - col_min)) * 100.0

    return out


def _invert(series_0_100):
    """Inverts a 0-100 normalized series (100 - x). Used for 'lower is better' metrics."""
    return 100.0 - series_0_100


# ── INDIVIDUAL DIMENSION COMPUTATIONS ────────────────────────────────────────

def _compute_income_score(city_df, persona):
    """
    Computes income_score: salary appropriate to the persona's tier,
    adjusted against cost of living. Higher = better income-to-CoL ratio.

    Uses avg_salary_fresher for early_career persona, avg_salary_3yr_exp
    for family_focused and budget_focused (representing a more established
    earner), divided by cost_of_living_index, then normalized 0-100.
    """
    salary_col = "avg_salary_fresher" if persona == "early_career" else "avg_salary_3yr_exp"

    raw = city_df[salary_col] / city_df["cost_of_living_index"]
    raw_df = pd.DataFrame({"income_raw": raw})
    normalized = normalize_scores(raw_df, columns=["income_raw"])
    return normalized["income_raw"]


def _compute_affordability_score(city_df, persona):
    """
    Computes affordability_score: inverse of rent burden + cost of living.
    Higher = more affordable.

    rent_burden = avg_monthly_rent_2bhk / avg_salary_3yr_exp (proxy for
    rent-to-income ratio). Combined with cost_of_living_index (inverted),
    each contributing 50% before final normalization.
    """
    rent_burden_raw = city_df["avg_monthly_rent_2bhk"] / city_df["avg_salary_3yr_exp"]
    rent_burden_df = pd.DataFrame({"rent_burden": rent_burden_raw})
    rent_burden_normalized = normalize_scores(rent_burden_df, columns=["rent_burden"])
    rent_burden_score = _invert(rent_burden_normalized["rent_burden"])  # lower burden = higher score

    col_df = pd.DataFrame({"col": city_df["cost_of_living_index"]})
    col_normalized = normalize_scores(col_df, columns=["col"])
    col_score = _invert(col_normalized["col"])  # lower CoL = higher score

    affordability = (rent_burden_score * 0.5) + (col_score * 0.5)
    return affordability


def _compute_healthcare_score(city_df):
    """
    Computes healthcare_score from:
      - hospital_beds_per_lakh (40% weight)
      - health_centres_per_lakh (30% weight)
      - inverse crude_death_rate (30% weight)

    Seeded from real data for Bengaluru, Mumbai, Chennai (bed/facility
    density) and Bengaluru, Chennai, Delhi, Pune (crude_death_rate).
    See data/processed/city_hospital_counts.csv and
    data/processed/city_health_summary.csv for provenance.
    """
    beds_df = pd.DataFrame({"beds": city_df["hospital_beds_per_lakh"]})
    beds_normalized = normalize_scores(beds_df, columns=["beds"])["beds"]

    centres_df = pd.DataFrame({"centres": city_df["health_centres_per_lakh"]})
    centres_normalized = normalize_scores(centres_df, columns=["centres"])["centres"]

    death_rate_df = pd.DataFrame({"death_rate": city_df["crude_death_rate"]})
    death_rate_normalized = normalize_scores(death_rate_df, columns=["death_rate"])["death_rate"]
    death_rate_score = _invert(death_rate_normalized)  # lower death rate = higher score

    healthcare = (
        (beds_normalized * 0.40) +
        (centres_normalized * 0.30) +
        (death_rate_score * 0.30)
    )
    return healthcare


def _compute_environment_score(city_df):
    """
    Computes environment_score from:
      - inverse pollution_aqi_avg (60% weight) — lower AQI = better
      - green_space_index (40% weight) — higher = better
    """
    aqi_df = pd.DataFrame({"aqi": city_df["pollution_aqi_avg"]})
    aqi_normalized = normalize_scores(aqi_df, columns=["aqi"])["aqi"]
    aqi_score = _invert(aqi_normalized)  # lower AQI = higher score

    green_df = pd.DataFrame({"green": city_df["green_space_index"]})
    green_normalized = normalize_scores(green_df, columns=["green"])["green"]

    environment = (aqi_score * 0.60) + (green_normalized * 0.40)
    return environment


def _compute_career_growth_score(city_df):
    """
    Computes career_growth_score from:
      - tech_job_count_index (50% weight)
      - startup_ecosystem_score (30% weight)
      - salary growth ratio: avg_salary_3yr_exp / avg_salary_fresher (20% weight)
        (higher ratio = stronger earning trajectory over a career)
    """
    tech_df = pd.DataFrame({"tech": city_df["tech_job_count_index"]})
    tech_normalized = normalize_scores(tech_df, columns=["tech"])["tech"]

    startup_df = pd.DataFrame({"startup": city_df["startup_ecosystem_score"]})
    startup_normalized = normalize_scores(startup_df, columns=["startup"])["startup"]

    growth_ratio_raw = city_df["avg_salary_3yr_exp"] / city_df["avg_salary_fresher"]
    growth_ratio_df = pd.DataFrame({"growth_ratio": growth_ratio_raw})
    growth_ratio_normalized = normalize_scores(growth_ratio_df, columns=["growth_ratio"])["growth_ratio"]

    career_growth = (
        (tech_normalized * 0.50) +
        (startup_normalized * 0.30) +
        (growth_ratio_normalized * 0.20)
    )
    return career_growth


def _compute_family_fit_score(city_df, healthcare_score_series, has_children=False):
    """
    Computes family_fit_score from:
      - school_quality_index (30% weight)
      - inverse crime_index (30% weight) — lower crime = better
      - healthcare_score (25% weight) — reuses the already-computed
        healthcare_score so family fit reflects real healthcare data too
      - has_children modifier: +5 flat bonus to ALL cities equally if
        has_children=True (does not change relative ranking, but signals
        elevated importance of this dimension downstream via persona
        weights — included here per spec as a direct score modifier)

    Note: school_quality_index and crime_index together contribute the
    remaining 45% of weight (30% + 30% = 60% before the 25% healthcare
    share — these three sum to 85%; the explicit spec asks for exactly
    30/30/25 = 85%, so the residual 15% is implicitly distributed as
    headroom for the has_children modifier, capped via clipping below).
    """
    school_df = pd.DataFrame({"school": city_df["school_quality_index"]})
    school_normalized = normalize_scores(school_df, columns=["school"])["school"]

    crime_df = pd.DataFrame({"crime": city_df["crime_index"]})
    crime_normalized = normalize_scores(crime_df, columns=["crime"])["crime"]
    crime_score = _invert(crime_normalized)  # lower crime = higher score

    family_fit = (
        (school_normalized * 0.30) +
        (crime_score * 0.30) +
        (healthcare_score_series * 0.25)
    )

    if has_children:
        family_fit = family_fit + 5.0

    # Clip to valid 0-100 range after modifier application
    family_fit = family_fit.clip(lower=0.0, upper=100.0)

    return family_fit


# ── MAIN SCORE COMPUTATION ───────────────────────────────────────────────────

def compute_all_scores(city_df, persona, has_children=False):
    """
    Computes all 7 score dimensions for every city in city_df, for the
    given persona.

    Args:
        city_df (pd.DataFrame): Must contain at least these columns
            (matching urbanpulse.cities schema):
              city_name, avg_salary_fresher, avg_salary_3yr_exp,
              cost_of_living_index, avg_monthly_rent_2bhk,
              hospital_beds_per_lakh, health_centres_per_lakh,
              crude_death_rate, pollution_aqi_avg, green_space_index,
              tech_job_count_index, startup_ecosystem_score,
              school_quality_index, crime_index
        persona (str): One of 'early_career', 'family_focused', 'budget_focused'.
        has_children (bool): Applies the +5 family_fit_score modifier
            uniformly if True. Default False.

    Returns:
        dict: { city_name: { 'income_score': float, 'affordability_score': float,
                              'healthcare_score': float, 'environment_score': float,
                              'career_growth_score': float, 'family_fit_score': float,
                              'adjusted_life_score': float } }
              All scores are floats rounded to 2 decimal places, range 0-100.

    Raises:
        ValueError: if persona is not a recognized value, or if required
            columns are missing from city_df.
    """
    if persona not in VALID_PERSONAS:
        raise ValueError(
            f"Unknown persona '{persona}'. Must be one of: {sorted(VALID_PERSONAS)}"
        )

    required_columns = [
        "city_name", "avg_salary_fresher", "avg_salary_3yr_exp",
        "cost_of_living_index", "avg_monthly_rent_2bhk",
        "hospital_beds_per_lakh", "health_centres_per_lakh", "crude_death_rate",
        "pollution_aqi_avg", "green_space_index",
        "tech_job_count_index", "startup_ecosystem_score",
        "school_quality_index", "crime_index",
    ]
    missing = set(required_columns) - set(city_df.columns)
    if missing:
        raise ValueError(f"city_df is missing required columns: {missing}")

    df = city_df.reset_index(drop=True).copy()

    income_score = _compute_income_score(df, persona)
    affordability_score = _compute_affordability_score(df, persona)
    healthcare_score = _compute_healthcare_score(df)
    environment_score = _compute_environment_score(df)
    career_growth_score = _compute_career_growth_score(df)
    family_fit_score = _compute_family_fit_score(df, healthcare_score, has_children=has_children)

    weights = PERSONA_WEIGHTS[persona]
    adjusted_life_score = (
        income_score * weights["income"] +
        affordability_score * weights["affordability"] +
        healthcare_score * weights["healthcare"] +
        environment_score * weights["environment"] +
        career_growth_score * weights["career"] +
        family_fit_score * weights["family"]
    )

    results = {}
    for i, row in df.iterrows():
        city = row["city_name"]
        results[city] = {
            "income_score": round(float(income_score.iloc[i]), 2),
            "affordability_score": round(float(affordability_score.iloc[i]), 2),
            "healthcare_score": round(float(healthcare_score.iloc[i]), 2),
            "environment_score": round(float(environment_score.iloc[i]), 2),
            "career_growth_score": round(float(career_growth_score.iloc[i]), 2),
            "family_fit_score": round(float(family_fit_score.iloc[i]), 2),
            "adjusted_life_score": round(float(adjusted_life_score.iloc[i]), 2),
        }

    return results


# ── DERIVED LOOKUPS ──────────────────────────────────────────────────────────

def get_best_city(scores_dict):
    """
    Returns the city name with the highest adjusted_life_score.

    Args:
        scores_dict (dict): Output of compute_all_scores().

    Returns:
        str: City name with the highest adjusted_life_score. Ties are
            broken by alphabetical order (deterministic).
    """
    if not scores_dict:
        raise ValueError("scores_dict is empty — cannot determine best city.")

    best_city = max(
        scores_dict.keys(),
        key=lambda city: (scores_dict[city]["adjusted_life_score"], -ord(city[0]) if city else 0)
    )
    # Deterministic tie-break: highest score wins; on exact tie, alphabetically first city wins
    max_score = max(v["adjusted_life_score"] for v in scores_dict.values())
    tied_cities = sorted([c for c, v in scores_dict.items() if v["adjusted_life_score"] == max_score])
    return tied_cities[0]


def get_top_positive_driver(scores_dict, city, persona):
    """
    Identifies the dimension that contributes most positively to a city's
    adjusted_life_score for the given persona — i.e. the dimension with
    the highest (score x persona_weight) product among non-zero-weighted
    dimensions.

    Args:
        scores_dict (dict): Output of compute_all_scores().
        city (str): City name to inspect (must be a key in scores_dict).
        persona (str): Persona used to determine weighting.

    Returns:
        tuple(str, float): (human-readable dimension label, raw score value)
            e.g. ("Career Growth", 87.5)

    Raises:
        ValueError: if city not found in scores_dict, or persona unknown.
    """
    if city not in scores_dict:
        raise ValueError(f"City '{city}' not found in scores_dict.")
    if persona not in VALID_PERSONAS:
        raise ValueError(f"Unknown persona '{persona}'.")

    weights = PERSONA_WEIGHTS[persona]
    city_scores = scores_dict[city]

    contributions = {}
    for dim_key, score_col in DIMENSION_TO_SCORE_COLUMN.items():
        weight = weights.get(dim_key, 0.0)
        if weight <= 0:
            continue
        contributions[score_col] = city_scores[score_col] * weight

    if not contributions:
        # All weights zero (shouldn't happen given persona configs) — fallback
        best_col = max(DIMENSION_TO_SCORE_COLUMN.values(), key=lambda c: city_scores[c])
        return (DIMENSION_LABELS[best_col], city_scores[best_col])

    top_col = max(contributions, key=contributions.get)
    return (DIMENSION_LABELS[top_col], city_scores[top_col])


def get_top_negative_driver(scores_dict, city, persona):
    """
    Identifies the dimension that contributes LEAST (or most negatively,
    in relative terms) to a city's adjusted_life_score for the given
    persona — the weakest weighted contribution among non-zero-weighted
    dimensions. Useful for explaining why a city scored lower than
    expected.

    Args:
        scores_dict (dict): Output of compute_all_scores().
        city (str): City name to inspect (must be a key in scores_dict).
        persona (str): Persona used to determine weighting.

    Returns:
        tuple(str, float): (human-readable dimension label, raw score value)
            e.g. ("Affordability", 32.1)

    Raises:
        ValueError: if city not found in scores_dict, or persona unknown.
    """
    if city not in scores_dict:
        raise ValueError(f"City '{city}' not found in scores_dict.")
    if persona not in VALID_PERSONAS:
        raise ValueError(f"Unknown persona '{persona}'.")

    weights = PERSONA_WEIGHTS[persona]
    city_scores = scores_dict[city]

    contributions = {}
    for dim_key, score_col in DIMENSION_TO_SCORE_COLUMN.items():
        weight = weights.get(dim_key, 0.0)
        if weight <= 0:
            continue
        contributions[score_col] = city_scores[score_col] * weight

    if not contributions:
        worst_col = min(DIMENSION_TO_SCORE_COLUMN.values(), key=lambda c: city_scores[c])
        return (DIMENSION_LABELS[worst_col], city_scores[worst_col])

    worst_col = min(contributions, key=contributions.get)
    return (DIMENSION_LABELS[worst_col], city_scores[worst_col])


# ── COMPARISON TABLE (API-FACING) ────────────────────────────────────────────

def get_comparison_table(city_list, persona, city_df, has_children=False):
    """
    Builds a structured comparison dict suitable for direct JSON
    serialization by a FastAPI endpoint (e.g. POST /compare/).

    Args:
        city_list (list[str]): City names to include in the comparison
            (must be a subset of city_df['city_name'] values).
        persona (str): One of 'early_career', 'family_focused', 'budget_focused'.
        city_df (pd.DataFrame): Full city reference DataFrame (see
            compute_all_scores() docstring for required columns).
        has_children (bool): Applied to the family_fit_score modifier.

    Returns:
        dict: {
            "persona": str,
            "has_children": bool,
            "cities_compared": list[str],
            "best_city": str,
            "scores": { city_name: { all 7 scores }, ... },
            "drivers": {
                city_name: {
                    "top_positive": {"dimension": str, "score": float},
                    "top_negative": {"dimension": str, "score": float},
                }, ...
            },
            "ranking": [ {"city": str, "adjusted_life_score": float, "rank": int}, ... ]
        }

    Raises:
        ValueError: if any city in city_list is not present in city_df,
            or persona is unrecognized.
    """
    if persona not in VALID_PERSONAS:
        raise ValueError(f"Unknown persona '{persona}'.")

    available_cities = set(city_df["city_name"].tolist())
    missing_cities = set(city_list) - available_cities
    if missing_cities:
        raise ValueError(f"Cities not found in city_df: {missing_cities}")

    subset_df = city_df[city_df["city_name"].isin(city_list)].reset_index(drop=True)

    # Scores are normalized relative to ONLY the cities being compared,
    # so a 2-city comparison and a 6-city comparison will naturally
    # produce different absolute scores for the same city. This is
    # intentional — it reflects relative standing within the comparison set.
    scores_dict = compute_all_scores(subset_df, persona, has_children=has_children)

    best_city = get_best_city(scores_dict)

    drivers = {}
    for city in city_list:
        top_pos_dim, top_pos_score = get_top_positive_driver(scores_dict, city, persona)
        top_neg_dim, top_neg_score = get_top_negative_driver(scores_dict, city, persona)
        drivers[city] = {
            "top_positive": {"dimension": top_pos_dim, "score": top_pos_score},
            "top_negative": {"dimension": top_neg_dim, "score": top_neg_score},
        }

    ranking_sorted = sorted(
        scores_dict.items(),
        key=lambda kv: (-kv[1]["adjusted_life_score"], kv[0])
    )
    ranking = [
        {"city": city, "adjusted_life_score": data["adjusted_life_score"], "rank": idx + 1}
        for idx, (city, data) in enumerate(ranking_sorted)
    ]

    return {
        "persona": persona,
        "has_children": has_children,
        "cities_compared": city_list,
        "best_city": best_city,
        "scores": scores_dict,
        "drivers": drivers,
        "ranking": ranking,
    }


# ── RECOMMENDATION TEXT ──────────────────────────────────────────────────────

def get_recommendation_text(best_city, persona, top_positive, top_negative):
    """
    Generates a deterministic 2-sentence plain-English recommendation
    summary. This is a lightweight rule-based fallback/preview — the
    full GenAI narrative (backend/genai/gemini_narrator.py) produces a
    richer version using the same inputs.

    Args:
        best_city (str): Output of get_best_city().
        persona (str): Persona used for the comparison.
        top_positive (tuple(str, float)): Output of get_top_positive_driver()
            for best_city, e.g. ("Career Growth", 87.5).
        top_negative (tuple(str, float)): Output of get_top_negative_driver()
            for best_city, e.g. ("Affordability", 32.1).

    Returns:
        str: A 2-sentence recommendation, e.g.
            "For an early-career professional, Bengaluru is the top match,
            driven primarily by strong Career Growth. The main trade-off
            to weigh is its relatively weaker Affordability score."
    """
    persona_labels = {
        "early_career": "an early-career professional",
        "family_focused": "a family-focused relocator",
        "budget_focused": "a budget-focused relocator",
    }
    persona_phrase = persona_labels.get(persona, "this persona")

    pos_dim, pos_score = top_positive
    neg_dim, neg_score = top_negative

    sentence_1 = (
        f"For {persona_phrase}, {best_city} is the top match, "
        f"driven primarily by strong {pos_dim} ({pos_score:.0f}/100)."
    )
    sentence_2 = (
        f"The main trade-off to weigh is its relatively weaker "
        f"{neg_dim} ({neg_score:.0f}/100)."
    )

    return f"{sentence_1} {sentence_2}"


# ── SALARY EQUIVALENCE ───────────────────────────────────────────────────────

def compute_salary_equivalence(source_city, target_city, current_salary, city_df):
    """
    Computes the salary required in target_city to have equivalent
    purchasing power to current_salary in source_city, based on the
    ratio of cost_of_living_index between the two cities.

    Formula:
        required_salary = current_salary * (col_target / col_source)

    Args:
        source_city (str): City name the user currently earns in.
        target_city (str): City name the user is evaluating moving to.
        current_salary (float): Current annual or monthly salary (any
            consistent unit — output will be in the same unit).
        city_df (pd.DataFrame): Must contain 'city_name' and
            'cost_of_living_index' columns.

    Returns:
        float: The equivalent required salary in target_city, rounded
            to 2 decimal places.

    Raises:
        ValueError: if source_city or target_city not found in city_df,
            or if they are the same city, or current_salary <= 0.
    """
    if source_city == target_city:
        raise ValueError("source_city and target_city must be different.")

    if current_salary <= 0:
        raise ValueError("current_salary must be a positive number.")

    available_cities = set(city_df["city_name"].tolist())
    if source_city not in available_cities:
        raise ValueError(f"source_city '{source_city}' not found in city_df.")
    if target_city not in available_cities:
        raise ValueError(f"target_city '{target_city}' not found in city_df.")

    col_source = city_df.loc[city_df["city_name"] == source_city, "cost_of_living_index"].iloc[0]
    col_target = city_df.loc[city_df["city_name"] == target_city, "cost_of_living_index"].iloc[0]

    required_salary = current_salary * (col_target / col_source)

    return round(float(required_salary), 2)


# ── __main__ DEMO BLOCK ──────────────────────────────────────────────────────

def _build_dummy_city_df():
    """Builds a small dummy city DataFrame for standalone testing of this module."""
    data = {
        "city_name": ["Mumbai", "Bengaluru", "Chennai", "Pune", "Delhi", "Hyderabad"],
        "avg_salary_fresher": [550000, 600000, 480000, 520000, 580000, 560000],
        "avg_salary_3yr_exp": [1250000, 1450000, 1050000, 1150000, 1400000, 1300000],
        "cost_of_living_index": [100.0, 85.0, 72.0, 75.0, 92.0, 68.0],
        "avg_monthly_rent_2bhk": [62000, 42000, 28000, 31000, 40000, 29000],
        "hospital_beds_per_lakh": [62.5, 38.0, 18.2, 42.0, 55.0, 48.0],
        "health_centres_per_lakh": [1.35, 0.71, 0.14, 2.50, 3.20, 2.80],
        "crude_death_rate": [5.8, 5.2, 6.4, 4.1, 4.5, 5.0],
        "pollution_aqi_avg": [145.0, 62.0, 58.0, 78.0, 215.0, 68.0],
        "green_space_index": [28.0, 38.0, 22.0, 42.0, 18.0, 30.0],
        "tech_job_count_index": [78.0, 98.0, 68.0, 75.0, 70.0, 88.0],
        "startup_ecosystem_score": [72.0, 96.0, 55.0, 68.0, 65.0, 80.0],
        "school_quality_index": [72.0, 78.0, 76.0, 80.0, 70.0, 74.0],
        "crime_index": [52.0, 45.0, 40.0, 38.0, 58.0, 42.0],
    }
    return pd.DataFrame(data)


def main():
    print("=" * 70)
    print("SCORING ENGINE DEMO — UrbanPulse backend/scoring.py")
    print("=" * 70)

    city_df = _build_dummy_city_df()
    print(f"\nDummy city_df ({len(city_df)} cities):")
    print(city_df[["city_name", "cost_of_living_index", "pollution_aqi_avg",
                    "hospital_beds_per_lakh"]].to_string(index=False))

    for persona in VALID_PERSONAS:
        for has_children in ([False, True] if persona == "family_focused" else [False]):
            print("\n" + "-" * 70)
            label = f"PERSONA: {persona}" + (f" (has_children={has_children})" if has_children else "")
            print(label)
            print("-" * 70)

            scores = compute_all_scores(city_df, persona, has_children=has_children)

            print("\nAll scores:")
            scores_df = pd.DataFrame(scores).T
            scores_df = scores_df.sort_values("adjusted_life_score", ascending=False)
            print(scores_df.round(2).to_string())

            best_city = get_best_city(scores)
            print(f"\nBest city: {best_city}")

            top_pos = get_top_positive_driver(scores, best_city, persona)
            top_neg = get_top_negative_driver(scores, best_city, persona)
            print(f"Top positive driver: {top_pos[0]} ({top_pos[1]:.2f})")
            print(f"Top negative driver: {top_neg[0]} ({top_neg[1]:.2f})")

            recommendation = get_recommendation_text(best_city, persona, top_pos, top_neg)
            print(f"\nRecommendation text:\n  {recommendation}")

    print("\n" + "-" * 70)
    print("COMPARISON TABLE DEMO (3 cities, early_career persona)")
    print("-" * 70)
    comparison = get_comparison_table(
        city_list=["Bengaluru", "Pune", "Hyderabad"],
        persona="early_career",
        city_df=city_df,
        has_children=False,
    )
    print(f"\nBest city: {comparison['best_city']}")
    print(f"\nRanking:")
    for r in comparison["ranking"]:
        print(f"  #{r['rank']}: {r['city']} — {r['adjusted_life_score']:.2f}")
    print(f"\nDrivers for {comparison['best_city']}:")
    print(f"  Top positive: {comparison['drivers'][comparison['best_city']]['top_positive']}")
    print(f"  Top negative: {comparison['drivers'][comparison['best_city']]['top_negative']}")

    print("\n" + "-" * 70)
    print("SALARY EQUIVALENCE DEMO")
    print("-" * 70)
    test_cases = [
        ("Mumbai", "Pune", 2000000),
        ("Pune", "Mumbai", 1400000),
        ("Hyderabad", "Delhi", 1000000),
    ]
    for source, target, salary in test_cases:
        equivalent = compute_salary_equivalence(source, target, salary, city_df)
        print(f"  ₹{salary:,} in {source} ≈ ₹{equivalent:,.0f} in {target}")

    print("\n" + "=" * 70)
    print("[scoring.py] Demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()