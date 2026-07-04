"""
scripts/export_tableau_files.py

Exports all UrbanPulse analytics data to data/exports/ for Tableau
consumption and portfolio presentation.

If urbanpulse.city_scores is empty (scoring engine not yet run),
city_score_overview.csv and persona_comparison.csv are computed live
from city_master.csv using backend/scoring.py.

All exports are flat CSVs — no special formatting, just clean column
names and correct data types for direct Tableau connect.

Run: python scripts/export_tableau_files.py
Requires: DATABASE_URL environment variable
          data/synthetic/city_master.csv (for scoring fallback)
"""

import os
import sys
import itertools

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
SYNTHETIC_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
EXPORTS_DIR = os.path.join(PROJECT_ROOT, "data", "exports")

sys.path.insert(0, BACKEND_DIR)
from scoring import compute_all_scores, compute_salary_equivalence, VALID_PERSONAS

SCHEMA = "urbanpulse"
os.makedirs(EXPORTS_DIR, exist_ok=True)


# ── ENGINE ───────────────────────────────────────────────────────────────────

def get_engine():
    database_url = os.environ.get("DATABASE_URL", "postgresql://localhost/urbanpulse")
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"[export] Connected to database.")
        return engine
    except OperationalError as e:
        print(f"[export] ERROR: Could not connect to database.\n  {e}", file=sys.stderr)
        sys.exit(1)


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _load_city_df():
    path = os.path.join(SYNTHETIC_DIR, "city_master.csv")
    if not os.path.exists(path):
        print(
            f"[export] ERROR: city_master.csv not found at {path}. "
            f"Run scripts/generate_synthetic_data.py first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return pd.read_csv(path, encoding="utf-8-sig")


def _save_and_report(df: pd.DataFrame, filename: str) -> str:
    out_path = os.path.join(EXPORTS_DIR, filename)
    df.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}  ({len(df)} rows, {len(df.columns)} columns)")
    return out_path


def _compute_scores_for_all_personas(city_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calls compute_all_scores() for each persona and assembles a flat
    DataFrame: one row per city × persona with all 7 score columns.
    """
    rows = []
    for persona in sorted(VALID_PERSONAS):
        scores = compute_all_scores(city_df, persona, has_children=False)
        for city_name, score_dict in scores.items():
            city_meta = city_df[city_df["city_name"] == city_name].iloc[0]
            rows.append({
                "city_name": city_name,
                "state": city_meta["state"],
                "region": city_meta["region"],
                "persona": persona,
                "cost_of_living_index": float(city_meta["cost_of_living_index"]),
                "pollution_aqi_avg": float(city_meta["pollution_aqi_avg"]),
                "hospital_beds_per_lakh": float(city_meta["hospital_beds_per_lakh"]),
                "income_score": score_dict["income_score"],
                "affordability_score": score_dict["affordability_score"],
                "healthcare_score": score_dict["healthcare_score"],
                "environment_score": score_dict["environment_score"],
                "career_growth_score": score_dict["career_growth_score"],
                "family_fit_score": score_dict["family_fit_score"],
                "adjusted_life_score": score_dict["adjusted_life_score"],
            })
    return pd.DataFrame(rows)


# ── EXPORT 1: city_score_overview.csv ────────────────────────────────────────

def export_city_score_overview(engine, city_df: pd.DataFrame) -> pd.DataFrame:
    print("\n[export] (1/6) city_score_overview.csv ...")

    # Try DB first; fall back to live scoring if table is empty
    try:
        with engine.connect() as conn:
            db_scores = pd.read_sql(
                text(f"SELECT * FROM {SCHEMA}.city_scores ORDER BY persona, composite_rank"),
                conn,
            )
    except Exception:
        db_scores = pd.DataFrame()

    if not db_scores.empty:
        print(f"  Source: urbanpulse.city_scores table ({len(db_scores)} rows)")
        # Rename to match export schema (DB uses composite_score; export uses adjusted_life_score)
        export_df = db_scores.rename(columns={"composite_score": "adjusted_life_score"})
    else:
        print(f"  Source: live scoring via backend/scoring.py (city_scores table is empty)")
        export_df = _compute_scores_for_all_personas(city_df)

    _save_and_report(export_df, "city_score_overview.csv")
    return export_df


# ── EXPORT 2: monthly_trends.csv ─────────────────────────────────────────────

def export_monthly_trends(engine) -> pd.DataFrame:
    print("\n[export] (2/6) monthly_trends.csv ...")

    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text(
                    f"SELECT city_name, year_month, avg_aqi, avg_rent_1bhk, "
                    f"avg_rent_2bhk, avg_salary_offered, job_postings_index, "
                    f"cost_of_living_index, hospital_utilization_rate, "
                    f"rainfall_mm, temperature_avg "
                    f"FROM {SCHEMA}.monthly_city_metrics "
                    f"ORDER BY city_name, year_month"
                ),
                conn,
            )
    except Exception as e:
        print(f"  [warn] Could not query monthly_city_metrics: {e}. "
              f"Falling back to CSV.")
        path = os.path.join(
            os.path.dirname(SCRIPT_DIR), "data", "synthetic", "monthly_city_metrics.csv"
        )
        if os.path.exists(path):
            raw = pd.read_csv(path, encoding="utf-8-sig")
            df = raw[[
                "city_name", "year_month", "avg_aqi", "avg_rent_1bhk",
                "avg_rent_2bhk", "avg_salary_offered", "job_postings_index",
                "cost_of_living_index", "hospital_utilization_rate",
                "rainfall_mm", "temperature_avg",
            ]]
        else:
            print(f"  [error] monthly_city_metrics.csv not found either. Skipping.", file=sys.stderr)
            return pd.DataFrame()

    _save_and_report(df, "monthly_trends.csv")
    return df


# ── EXPORT 3: persona_comparison.csv ─────────────────────────────────────────

def export_persona_comparison(score_overview_df: pd.DataFrame) -> pd.DataFrame:
    print("\n[export] (3/6) persona_comparison.csv ...")

    frames = []
    for persona in sorted(VALID_PERSONAS):
        subset = score_overview_df[score_overview_df["persona"] == persona].copy()
        subset = subset.sort_values("adjusted_life_score", ascending=False).reset_index(drop=True)
        subset["rank"] = subset.index + 1
        frames.append(subset)

    df = pd.concat(frames, ignore_index=True)
    cols_first = ["persona", "rank", "city_name", "adjusted_life_score"]
    remaining = [c for c in df.columns if c not in cols_first]
    df = df[cols_first + remaining]

    _save_and_report(df, "persona_comparison.csv")
    return df


# ── EXPORT 4: health_summary_real.csv ────────────────────────────────────────

def export_health_summary_real(engine, city_df: pd.DataFrame) -> pd.DataFrame:
    print("\n[export] (4/6) health_summary_real.csv ...")

    # City-level static health fields from city_master
    city_health_static = city_df[[
        "city_name", "hospital_beds_per_lakh", "health_centres_per_lakh", "crude_death_rate",
    ]].copy()

    # Annual time-series from city_health_summary table
    try:
        with engine.connect() as conn:
            health_ts = pd.read_sql(
                text(
                    f"SELECT city_name, year, total_births, total_deaths, "
                    f"crude_death_rate_per_1000, crude_birth_rate_per_1000, "
                    f"infant_mortality, data_source "
                    f"FROM {SCHEMA}.city_health_summary "
                    f"WHERE partial_year = FALSE "
                    f"ORDER BY city_name, year"
                ),
                conn,
            )
    except Exception as e:
        print(f"  [warn] Could not query city_health_summary: {e}. "
              f"Falling back to processed CSV.")
        processed_path = os.path.join(PROCESSED_DIR, "city_health_summary.csv")
        if os.path.exists(processed_path):
            raw = pd.read_csv(processed_path, encoding="utf-8-sig")
            if "city" in raw.columns and "city_name" not in raw.columns:
                raw = raw.rename(columns={"city": "city_name"})
            health_ts = raw[raw["partial_year"].astype(str).str.lower() != "true"][[
                "city_name", "year", "total_births", "total_deaths",
                "crude_death_rate_per_1000", "crude_birth_rate_per_1000",
                "infant_mortality", "data_source",
            ]]
        else:
            health_ts = pd.DataFrame()

    if health_ts.empty:
        # Return just static per-city data if time-series unavailable
        df = city_health_static.copy()
        df["year"] = None
        df["total_births"] = None
        df["total_deaths"] = None
        df["crude_death_rate_per_1000"] = None
        df["crude_birth_rate_per_1000"] = None
        df["infant_mortality"] = None
        df["data_source"] = "synthetic_estimate"
    else:
        df = health_ts.merge(city_health_static, on="city_name", how="left")

    col_order = [
        "city_name", "year", "total_births", "total_deaths",
        "crude_death_rate_per_1000", "crude_birth_rate_per_1000",
        "infant_mortality", "hospital_beds_per_lakh",
        "health_centres_per_lakh", "crude_death_rate", "data_source",
    ]
    df = df[[c for c in col_order if c in df.columns]]

    _save_and_report(df, "health_summary_real.csv")
    return df


# ── EXPORT 5: salary_equivalence_matrix.csv ──────────────────────────────────

def export_salary_equivalence_matrix(city_df: pd.DataFrame) -> pd.DataFrame:
    print("\n[export] (5/6) salary_equivalence_matrix.csv ...")

    BASE_SALARY = 100_000  # ₹1,00,000/month

    cities = sorted(city_df["city_name"].tolist())

    rows = []
    for source_city in cities:
        row = {"source_city": source_city, "base_salary_monthly_inr": BASE_SALARY}
        for target_city in cities:
            if source_city == target_city:
                row[f"required_in_{target_city.lower()}"] = BASE_SALARY
            else:
                try:
                    required = compute_salary_equivalence(
                        source_city=source_city,
                        target_city=target_city,
                        current_salary=BASE_SALARY,
                        city_df=city_df,
                    )
                    row[f"required_in_{target_city.lower()}"] = required
                except ValueError:
                    row[f"required_in_{target_city.lower()}"] = None
        rows.append(row)

    df = pd.DataFrame(rows)
    _save_and_report(df, "salary_equivalence_matrix.csv")
    return df


# ── EXPORT 6: relocation_outcomes.csv ────────────────────────────────────────

def export_relocation_outcomes(engine) -> pd.DataFrame:
    print("\n[export] (6/6) relocation_outcomes.csv ...")

    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text(
                    f"SELECT rq.persona, rq.compared_cities, rq.selected_city, "
                    f"rq.query_date, up.age, up.monthly_income, "
                    f"up.current_city, up.dependents_count, up.has_children "
                    f"FROM {SCHEMA}.relocation_queries rq "
                    f"JOIN {SCHEMA}.user_profiles up ON rq.user_id = up.user_id "
                    f"ORDER BY rq.query_date DESC"
                ),
                conn,
            )
    except Exception as e:
        print(f"  [warn] Could not query relocation_queries: {e}. Falling back to CSV.")
        path = os.path.join(SYNTHETIC_DIR, "relocation_queries.csv")
        if os.path.exists(path):
            queries = pd.read_csv(path, encoding="utf-8-sig")
            profiles_path = os.path.join(SYNTHETIC_DIR, "user_profiles.csv")
            if os.path.exists(profiles_path):
                profiles = pd.read_csv(profiles_path, encoding="utf-8-sig")[
                    ["user_id", "age", "monthly_income", "current_city", "dependents_count", "has_children"]
                ]
                df = queries.merge(profiles, on="user_id", how="left")
            else:
                df = queries
        else:
            print(f"  [error] relocation_queries.csv not found. Skipping.", file=sys.stderr)
            return pd.DataFrame()

    _save_and_report(df, "relocation_outcomes.csv")
    return df


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("EXPORT TABLEAU FILES — UrbanPulse")
    print("=" * 70)

    engine = get_engine()
    city_df = _load_city_df()

    score_overview = export_city_score_overview(engine, city_df)
    export_monthly_trends(engine)
    export_persona_comparison(score_overview)
    export_health_summary_real(engine, city_df)
    export_salary_equivalence_matrix(city_df)
    export_relocation_outcomes(engine)

    print("\n" + "=" * 70)
    print(f"All exports saved to: {EXPORTS_DIR}")
    print("[export_tableau_files] Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[export_tableau_files] ERROR: {e}", file=sys.stderr)
        sys.exit(1)