"""
generate_synthetic_data.py

Generates all synthetic data files for UrbanPulse into data/synthetic/.

Seeds hospital_beds_per_lakh and health_centres_per_lakh for Bengaluru,
Mumbai, and Chennai from the real processed data in
data/processed/city_hospital_counts.csv. Delhi and Hyderabad use
realistic manual estimates (no real hospital CSV exists for them).
Pune has a real KRA report but no facility-count CSV, so it also uses
a manual estimate here.

Outputs:
  data/synthetic/city_master.csv            (6 rows)
  data/synthetic/monthly_city_metrics.csv   (~144 rows)
  data/synthetic/user_profiles.csv          (~300 rows)
  data/synthetic/relocation_queries.csv     (~300 rows)

Run standalone: python scripts/generate_synthetic_data.py
"""

import os
import sys
import random
import pandas as pd
import numpy as np
from datetime import date

# ── SEED ─────────────────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── PATHS ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
SYNTHETIC_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")
HOSPITAL_COUNTS_PATH = os.path.join(PROCESSED_DIR, "city_hospital_counts.csv")

os.makedirs(SYNTHETIC_DIR, exist_ok=True)

# ── CITY DEFINITIONS ─────────────────────────────────────────────────────────
CITIES = [
    {"city_id": 1, "city_name": "Mumbai", "state": "Maharashtra", "region": "West"},
    {"city_id": 2, "city_name": "Bengaluru", "state": "Karnataka", "region": "South"},
    {"city_id": 3, "city_name": "Chennai", "state": "Tamil Nadu", "region": "South"},
    {"city_id": 4, "city_name": "Pune", "state": "Maharashtra", "region": "West"},
    {"city_id": 5, "city_name": "Delhi", "state": "Delhi", "region": "North"},
    {"city_id": 6, "city_name": "Hyderabad", "state": "Telangana", "region": "South"},
]
CITY_NAMES = [c["city_name"] for c in CITIES]
CITY_ID_MAP = {c["city_name"]: c["city_id"] for c in CITIES}

# Approximate 2024 population estimates (lakhs = 100,000) used to convert
# raw facility/bed counts into per-lakh rates for real-data cities.
POP_LAKHS_2024 = {
    "Mumbai": 213.0,
    "Bengaluru": 140.0,
    "Chennai": 115.0,
    "Pune": 74.0,
    "Delhi": 329.0,
    "Hyderabad": 105.0,
}

# Manual estimates for cities lacking real hospital facility CSVs
# (Delhi, Hyderabad always; Pune as fallback since it has KRA disease data
# but no facility-count file).
MANUAL_HEALTH_ESTIMATES = {
    "Delhi": {"hospital_beds_per_lakh": 55.0, "health_centres_per_lakh": 3.2},
    "Hyderabad": {"hospital_beds_per_lakh": 48.0, "health_centres_per_lakh": 2.8},
    "Pune": {"hospital_beds_per_lakh": 42.0, "health_centres_per_lakh": 2.5},
}

# Real crude_death_rate anchors (from city_health_summary.csv, recent years,
# approximate mean) — used to seed city_master.crude_death_rate where real
# data exists. Hardcoded here since city_master generation only needs a
# single representative value, not the full time series.
REAL_CRUDE_DEATH_RATE = {
    "Bengaluru": 5.2,   # per 1000, approx mean of pop-based crude_death_rate_per_1000 2019-2024
    "Chennai": 6.4,
    "Delhi": 4.5,
    "Pune": 4.1,
}
# Synthetic estimates for cities without real births/deaths data
SYNTHETIC_CRUDE_DEATH_RATE = {
    "Mumbai": 5.8,
    "Hyderabad": 5.0,
}


def load_real_hospital_seeds():
    """
    Loads data/processed/city_hospital_counts.csv (produced by
    load_real_data.py) and converts total_beds / total_facilities into
    per-lakh rates for Bengaluru, Mumbai, Chennai.

    Falls back to MANUAL_HEALTH_ESTIMATES entirely if the file is missing
    (e.g. this script is run standalone before load_real_data.py).
    """
    seeds = {}

    if os.path.exists(HOSPITAL_COUNTS_PATH):
        print(f"[generate_synthetic_data] Loading real hospital seed data from: {HOSPITAL_COUNTS_PATH}")
        hosp_df = pd.read_csv(HOSPITAL_COUNTS_PATH)

        for _, row in hosp_df.iterrows():
            city = row["city"]
            pop_lakhs = POP_LAKHS_2024.get(city)
            if pop_lakhs is None:
                continue

            total_beds = row["total_beds"]
            total_facilities = row["total_facilities"]

            beds_per_lakh = total_beds / pop_lakhs
            centres_per_lakh = total_facilities / pop_lakhs

            # Bengaluru has no real bed data (all beds=0 in source) -
            # fall back to a realistic estimate rather than reporting 0
            if city == "Bengaluru" and total_beds == 0:
                beds_per_lakh = 38.0  # realistic estimate; facilities are real, beds are not
                print(f"  [note] Bengaluru has no real bed data (source beds=0). "
                      f"Using estimated beds_per_lakh={beds_per_lakh}; "
                      f"health_centres_per_lakh={centres_per_lakh:.2f} IS from real facility count.")

            seeds[city] = {
                "hospital_beds_per_lakh": round(beds_per_lakh, 2),
                "health_centres_per_lakh": round(centres_per_lakh, 2),
            }
            print(f"  Seeded {city}: beds_per_lakh={seeds[city]['hospital_beds_per_lakh']}, "
                  f"centres_per_lakh={seeds[city]['health_centres_per_lakh']} "
                  f"(real facilities={total_facilities}, real beds={total_beds})")
    else:
        print(f"[generate_synthetic_data] WARNING: {HOSPITAL_COUNTS_PATH} not found. "
              f"Run load_real_data.py first for accurate seeding. "
              f"Falling back to manual estimates for ALL cities.")

    # Fill in manual estimates for any city not covered by real data
    for city, est in MANUAL_HEALTH_ESTIMATES.items():
        if city not in seeds:
            seeds[city] = est
            print(f"  Manual estimate for {city}: beds_per_lakh={est['hospital_beds_per_lakh']}, "
                  f"centres_per_lakh={est['health_centres_per_lakh']}")

    # Final safety net - any city still missing gets a generic fallback
    for city in CITY_NAMES:
        if city not in seeds:
            print(f"  [warn] No seed found for {city}, using generic fallback")
            seeds[city] = {"hospital_beds_per_lakh": 40.0, "health_centres_per_lakh": 2.5}

    return seeds


# ── 1. CITY MASTER ──────────────────────────────────────────────────────────

def generate_city_master(health_seeds):
    print("\n[generate_synthetic_data] Generating city_master.csv...")

    # Profile-driven base values per city, designed to reflect the
    # qualitative city profiles given in the brief.
    profiles = {
        "Mumbai": {
            "avg_monthly_rent_1bhk": 38000, "avg_monthly_rent_2bhk": 62000,
            "avg_salary_fresher": 550000, "avg_salary_3yr_exp": 1250000,
            "cost_of_living_index": 100.0,  # base city
            "pollution_aqi_avg": 145.0, "green_space_index": 28.0,
            "public_transport_score": 78.0,
            "school_quality_index": 72.0, "crime_index": 52.0,
            "tech_job_count_index": 78.0, "startup_ecosystem_score": 72.0,
        },
        "Bengaluru": {
            "avg_monthly_rent_1bhk": 26000, "avg_monthly_rent_2bhk": 42000,
            "avg_salary_fresher": 600000, "avg_salary_3yr_exp": 1450000,
            "cost_of_living_index": 85.0,
            "pollution_aqi_avg": 62.0, "green_space_index": 38.0,
            "public_transport_score": 48.0,  # traffic-heavy, weaker transit
            "school_quality_index": 78.0, "crime_index": 45.0,
            "tech_job_count_index": 98.0, "startup_ecosystem_score": 96.0,
        },
        "Chennai": {
            "avg_monthly_rent_1bhk": 17000, "avg_monthly_rent_2bhk": 28000,
            "avg_salary_fresher": 480000, "avg_salary_3yr_exp": 1050000,
            "cost_of_living_index": 72.0,
            "pollution_aqi_avg": 58.0, "green_space_index": 22.0,
            "public_transport_score": 64.0,
            "school_quality_index": 76.0, "crime_index": 40.0,
            "tech_job_count_index": 68.0, "startup_ecosystem_score": 55.0,
        },
        "Pune": {
            "avg_monthly_rent_1bhk": 19000, "avg_monthly_rent_2bhk": 31000,
            "avg_salary_fresher": 520000, "avg_salary_3yr_exp": 1150000,
            "cost_of_living_index": 75.0,
            "pollution_aqi_avg": 78.0, "green_space_index": 42.0,
            "public_transport_score": 55.0,
            "school_quality_index": 80.0, "crime_index": 38.0,
            "tech_job_count_index": 75.0, "startup_ecosystem_score": 68.0,
        },
        "Delhi": {
            "avg_monthly_rent_1bhk": 24000, "avg_monthly_rent_2bhk": 40000,
            "avg_salary_fresher": 580000, "avg_salary_3yr_exp": 1400000,
            "cost_of_living_index": 92.0,
            "pollution_aqi_avg": 215.0,  # highest pollution (annual avg, spikes much higher Oct-Dec)
            "green_space_index": 18.0,
            "public_transport_score": 72.0,  # extensive metro
            "school_quality_index": 70.0, "crime_index": 58.0,
            "tech_job_count_index": 70.0, "startup_ecosystem_score": 65.0,
        },
        "Hyderabad": {
            "avg_monthly_rent_1bhk": 18000, "avg_monthly_rent_2bhk": 29000,
            "avg_salary_fresher": 560000, "avg_salary_3yr_exp": 1300000,
            "cost_of_living_index": 68.0,  # best affordability
            "pollution_aqi_avg": 68.0, "green_space_index": 30.0,
            "public_transport_score": 58.0,
            "school_quality_index": 74.0, "crime_index": 42.0,
            "tech_job_count_index": 88.0, "startup_ecosystem_score": 80.0,
        },
    }

    rows = []
    for city_def in CITIES:
        name = city_def["city_name"]
        profile = profiles[name]
        seeds = health_seeds[name]

        crude_death_rate = REAL_CRUDE_DEATH_RATE.get(name, SYNTHETIC_CRUDE_DEATH_RATE.get(name))

        row = {
            "city_id": city_def["city_id"],
            "city_name": name,
            "state": city_def["state"],
            "region": city_def["region"],
            "avg_monthly_rent_1bhk": profile["avg_monthly_rent_1bhk"],
            "avg_monthly_rent_2bhk": profile["avg_monthly_rent_2bhk"],
            "avg_salary_fresher": profile["avg_salary_fresher"],
            "avg_salary_3yr_exp": profile["avg_salary_3yr_exp"],
            "cost_of_living_index": profile["cost_of_living_index"],
            "pollution_aqi_avg": profile["pollution_aqi_avg"],
            "green_space_index": profile["green_space_index"],
            "public_transport_score": profile["public_transport_score"],
            "hospital_beds_per_lakh": seeds["hospital_beds_per_lakh"],
            "health_centres_per_lakh": seeds["health_centres_per_lakh"],
            "crude_death_rate": crude_death_rate,
            "school_quality_index": profile["school_quality_index"],
            "crime_index": profile["crime_index"],
            "tech_job_count_index": profile["tech_job_count_index"],
            "startup_ecosystem_score": profile["startup_ecosystem_score"],
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(SYNTHETIC_DIR, "city_master.csv")
    df.to_csv(out_path, index=False)

    print(f"[generate_synthetic_data] Saved city_master.csv -> {out_path}")
    print(f"[generate_synthetic_data] Rows: {len(df)}")
    print(df[["city_name", "hospital_beds_per_lakh", "health_centres_per_lakh",
              "crude_death_rate", "pollution_aqi_avg"]].to_string(index=False))

    return df


# ── 2. MONTHLY CITY METRICS ─────────────────────────────────────────────────

def _month_range(start_year, start_month, end_year, end_month):
    """Yields (year, month) tuples inclusive of both endpoints."""
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def generate_monthly_metrics(city_master_df):
    print("\n[generate_synthetic_data] Generating monthly_city_metrics.csv...")

    months = list(_month_range(2023, 1, 2024, 12))  # 24 months
    rows = []
    record_id = 1

    city_lookup = city_master_df.set_index("city_name").to_dict(orient="index")

    for city_def in CITIES:
        name = city_def["city_name"]
        city_id = city_def["city_id"]
        base = city_lookup[name]

        base_aqi = base["pollution_aqi_avg"]
        base_rent_1bhk = base["avg_monthly_rent_1bhk"]
        base_rent_2bhk = base["avg_monthly_rent_2bhk"]
        base_col = base["cost_of_living_index"]
        base_salary_offered = base["avg_salary_fresher"]

        for (year, month) in months:
            year_month = f"{year}-{month:02d}"

            # ── AQI seasonal logic ──────────────────────────────────────
            if name == "Delhi":
                if month in (10, 11, 12):
                    avg_aqi = np.random.uniform(300, 400)
                elif month in (7, 8):
                    avg_aqi = np.random.uniform(80, 120)
                else:
                    avg_aqi = np.random.uniform(140, 220)
            elif name == "Mumbai":
                if month in (11, 12, 1, 2):
                    avg_aqi = np.random.uniform(120, 170)
                elif month in (6, 7, 8, 9):
                    avg_aqi = np.random.uniform(45, 85)  # monsoon clears air
                else:
                    avg_aqi = np.random.uniform(90, 140)
            else:
                # Bengaluru, Chennai, Pune, Hyderabad: mild seasonal variation
                avg_aqi = np.random.uniform(base_aqi * 0.7, base_aqi * 1.3)

            avg_aqi = max(15.0, round(avg_aqi, 1))

            # ── Rainfall seasonal logic ──────────────────────────────────
            if name == "Mumbai":
                if month in (6, 7, 8, 9):
                    rainfall_mm = np.random.uniform(200, 600)
                else:
                    rainfall_mm = np.random.uniform(0, 15)
            elif name == "Chennai":
                if month in (10, 11, 12):
                    rainfall_mm = np.random.uniform(180, 420)  # NE monsoon
                elif month in (6, 7, 8, 9):
                    rainfall_mm = np.random.uniform(40, 120)  # weak SW monsoon
                else:
                    rainfall_mm = np.random.uniform(0, 25)
            elif name in ("Bengaluru", "Pune", "Hyderabad"):
                if month in (6, 7, 8, 9):
                    rainfall_mm = np.random.uniform(80, 220)
                elif month in (10, 11):
                    rainfall_mm = np.random.uniform(30, 90)
                else:
                    rainfall_mm = np.random.uniform(0, 20)
            elif name == "Delhi":
                if month in (7, 8):
                    rainfall_mm = np.random.uniform(100, 250)
                elif month in (6, 9):
                    rainfall_mm = np.random.uniform(20, 90)
                else:
                    rainfall_mm = np.random.uniform(0, 15)
            else:
                rainfall_mm = np.random.uniform(0, 50)

            rainfall_mm = round(max(0.0, rainfall_mm), 1)

            # ── Temperature seasonal logic (rough regional profile) ──────
            if name == "Delhi":
                if month in (5, 6):
                    temp = np.random.uniform(34, 42)
                elif month in (12, 1):
                    temp = np.random.uniform(8, 16)
                else:
                    temp = np.random.uniform(20, 32)
            elif name in ("Mumbai", "Chennai"):
                # Coastal cities: warm year-round, less variation
                temp = np.random.uniform(24, 34)
            elif name in ("Bengaluru", "Pune"):
                # Moderate climate, cooler
                if month in (12, 1):
                    temp = np.random.uniform(15, 22)
                else:
                    temp = np.random.uniform(20, 30)
            elif name == "Hyderabad":
                if month in (4, 5):
                    temp = np.random.uniform(32, 40)
                elif month in (12, 1):
                    temp = np.random.uniform(14, 22)
                else:
                    temp = np.random.uniform(22, 32)
            else:
                temp = np.random.uniform(20, 32)

            temperature_avg = round(temp, 1)

            # ── Rent: small month-to-month noise around base, mild upward
            # drift across the 24-month window (rent inflation) ──────────
            month_index = months.index((year, month))
            drift_factor = 1.0 + (month_index / len(months)) * 0.06  # ~6% drift over 2 years
            avg_rent_1bhk = round(base_rent_1bhk * drift_factor * np.random.uniform(0.96, 1.04))
            avg_rent_2bhk = round(base_rent_2bhk * drift_factor * np.random.uniform(0.96, 1.04))

            # ── Cost of living index: tracks rent drift, small noise ─────
            cost_of_living_index = round(base_col * drift_factor * np.random.uniform(0.98, 1.02), 1)

            # ── Job postings index: city-specific base with growth trend
            # and persona-aligned bias (Bengaluru/Hyderabad strongest growth) ──
            job_growth_cities = {"Bengaluru": 1.15, "Hyderabad": 1.18, "Pune": 1.08}
            job_growth_factor = job_growth_cities.get(name, 1.03)
            base_job_index = {
                "Mumbai": 82, "Bengaluru": 95, "Chennai": 68,
                "Pune": 72, "Delhi": 78, "Hyderabad": 88,
            }[name]
            job_postings_index = round(
                base_job_index * (job_growth_factor ** (month_index / len(months)))
                * np.random.uniform(0.90, 1.10), 1
            )

            # ── Salary offered: drifts upward with job market growth ─────
            avg_salary_offered = round(
                base_salary_offered * drift_factor * np.random.uniform(0.95, 1.08)
            )

            # ── Hospital utilization: higher in winter months (flu/resp.
            # illness season across all cities) ──────────────────────────
            if month in (11, 12, 1, 2):
                hospital_utilization_rate = round(np.random.uniform(72, 92), 1)
            elif month in (6, 7, 8) and name in ("Mumbai", "Chennai", "Bengaluru", "Pune", "Hyderabad"):
                # monsoon-related illness bump for monsoon-affected cities
                hospital_utilization_rate = round(np.random.uniform(65, 85), 1)
            else:
                hospital_utilization_rate = round(np.random.uniform(45, 68), 1)

            # ── Disease outbreak flag: rare, slightly more likely in
            # monsoon months (vector-borne disease season) ───────────────
            outbreak_prob = 0.12 if month in (7, 8, 9, 10) else 0.03
            disease_outbreak_flag = int(np.random.random() < outbreak_prob)

            rows.append({
                "record_id": record_id,
                "city_id": city_id,
                "city_name": name,
                "year_month": year_month,
                "avg_aqi": avg_aqi,
                "avg_rent_1bhk": avg_rent_1bhk,
                "avg_rent_2bhk": avg_rent_2bhk,
                "job_postings_index": job_postings_index,
                "avg_salary_offered": avg_salary_offered,
                "cost_of_living_index": cost_of_living_index,
                "hospital_utilization_rate": hospital_utilization_rate,
                "disease_outbreak_flag": disease_outbreak_flag,
                "rainfall_mm": rainfall_mm,
                "temperature_avg": temperature_avg,
            })
            record_id += 1

    df = pd.DataFrame(rows)
    out_path = os.path.join(SYNTHETIC_DIR, "monthly_city_metrics.csv")
    df.to_csv(out_path, index=False)

    print(f"[generate_synthetic_data] Saved monthly_city_metrics.csv -> {out_path}")
    print(f"[generate_synthetic_data] Rows: {len(df)} (expected {len(CITIES)} cities x {len(months)} months = {len(CITIES)*len(months)})")

    # Validation prints for key seasonal rules
    delhi_oct_dec = df[(df["city_name"] == "Delhi") & (df["year_month"].str[5:7].isin(["10", "11", "12"]))]
    delhi_jul_aug = df[(df["city_name"] == "Delhi") & (df["year_month"].str[5:7].isin(["07", "08"]))]
    print(f"  Delhi AQI Oct-Dec: mean={delhi_oct_dec['avg_aqi'].mean():.1f} (target 300-400)")
    print(f"  Delhi AQI Jul-Aug: mean={delhi_jul_aug['avg_aqi'].mean():.1f} (target 80-120)")

    mumbai_monsoon = df[(df["city_name"] == "Mumbai") & (df["year_month"].str[5:7].isin(["06", "07", "08", "09"]))]
    mumbai_dry = df[(df["city_name"] == "Mumbai") & (~df["year_month"].str[5:7].isin(["06", "07", "08", "09"]))]
    print(f"  Mumbai rainfall Jun-Sep: mean={mumbai_monsoon['rainfall_mm'].mean():.1f}mm (target 200-600)")
    print(f"  Mumbai rainfall rest-of-year: mean={mumbai_dry['rainfall_mm'].mean():.1f}mm (target ~0)")

    chennai_ne_monsoon = df[(df["city_name"] == "Chennai") & (df["year_month"].str[5:7].isin(["10", "11", "12"]))]
    print(f"  Chennai rainfall Oct-Dec: mean={chennai_ne_monsoon['rainfall_mm'].mean():.1f}mm (NE monsoon spike)")

    winter_util = df[df["year_month"].str[5:7].isin(["11", "12", "01", "02"])]
    other_util = df[~df["year_month"].str[5:7].isin(["11", "12", "01", "02"])]
    print(f"  Hospital utilization winter: mean={winter_util['hospital_utilization_rate'].mean():.1f}% "
          f"vs other months: mean={other_util['hospital_utilization_rate'].mean():.1f}%")

    return df


# ── 3. USER PROFILES ────────────────────────────────────────────────────────

PERSONAS = ["early_career", "family_focused", "budget_focused"]
PERSONA_WEIGHTS = [0.40, 0.30, 0.30]

PRIORITY_OPTIONS = [
    "affordability", "healthcare", "job_market", "livability",
    "infrastructure", "growth", "schools", "pollution", "safety",
]

PERSONA_PRIORITY_BIAS = {
    "early_career": ["job_market", "growth", "affordability", "livability"],
    "family_focused": ["healthcare", "schools", "safety", "livability"],
    "budget_focused": ["affordability", "infrastructure", "job_market", "pollution"],
}


def _sample_priorities(persona):
    """
    Samples 3 distinct priorities for a user, biased toward the persona's
    typical concerns but with some randomness so it's not deterministic.
    """
    biased_pool = PERSONA_PRIORITY_BIAS[persona]
    # 70% chance each of the 3 picks comes from the biased pool, else random
    chosen = []
    pool_remaining = list(PRIORITY_OPTIONS)

    for _ in range(3):
        if np.random.random() < 0.7 and any(p in pool_remaining for p in biased_pool):
            available_biased = [p for p in biased_pool if p in pool_remaining]
            pick = random.choice(available_biased)
        else:
            pick = random.choice(pool_remaining)
        chosen.append(pick)
        pool_remaining.remove(pick)

    return chosen[0], chosen[1], chosen[2]


def generate_user_profiles(n=300):
    print("\n[generate_synthetic_data] Generating user_profiles.csv...")

    rows = []
    for user_id in range(1, n + 1):
        persona = np.random.choice(PERSONAS, p=PERSONA_WEIGHTS)

        if persona == "early_career":
            age = int(np.random.randint(22, 31))
            years_experience = round(np.random.uniform(0, 5), 1)
            monthly_income = int(np.random.uniform(28000, 85000))
            dependents_count = int(np.random.choice([0, 0, 0, 1], p=[0.6, 0.2, 0.15, 0.05]))
            has_children = False
        elif persona == "family_focused":
            age = int(np.random.randint(28, 46))
            years_experience = round(np.random.uniform(5, 20), 1)
            monthly_income = int(np.random.uniform(65000, 280000))
            dependents_count = int(np.random.choice([1, 2, 3, 4], p=[0.25, 0.40, 0.25, 0.10]))
            has_children = bool(np.random.random() < 0.82)
        else:  # budget_focused
            age = int(np.random.randint(24, 50))
            years_experience = round(np.random.uniform(1, 22), 1)
            monthly_income = int(np.random.uniform(22000, 95000))
            dependents_count = int(np.random.choice([0, 1, 2, 3], p=[0.35, 0.30, 0.25, 0.10]))
            has_children = bool(dependents_count >= 1 and np.random.random() < 0.6)

        current_city = random.choice(CITY_NAMES)

        # target_cities: 2-4 cities the user is considering, excluding current city
        other_cities = [c for c in CITY_NAMES if c != current_city]
        num_targets = np.random.choice([2, 3, 4], p=[0.35, 0.45, 0.20])
        target_cities = random.sample(other_cities, k=min(num_targets, len(other_cities)))
        target_cities_str = "|".join(target_cities)

        priority_1, priority_2, priority_3 = _sample_priorities(persona)

        rows.append({
            "user_id": user_id,
            "age": age,
            "current_city": current_city,
            "target_cities": target_cities_str,
            "persona": persona,
            "monthly_income": monthly_income,
            "dependents_count": dependents_count,
            "priority_1": priority_1,
            "priority_2": priority_2,
            "priority_3": priority_3,
            "has_children": has_children,
            "years_experience": years_experience,
        })

    df = pd.DataFrame(rows)
    out_path = os.path.join(SYNTHETIC_DIR, "user_profiles.csv")
    df.to_csv(out_path, index=False)

    print(f"[generate_synthetic_data] Saved user_profiles.csv -> {out_path}")
    print(f"[generate_synthetic_data] Rows: {len(df)}")
    print(f"  Persona distribution:\n{df['persona'].value_counts(normalize=True).round(3).to_string()}")
    print(f"  Mean monthly_income by persona:\n{df.groupby('persona')['monthly_income'].mean().round(0).to_string()}")

    return df


# ── 4. RELOCATION QUERIES ───────────────────────────────────────────────────

# Persona -> weighted preference for selected_city, designed so the
# "most likely" cities dominate but aren't guaranteed (realistic noise).
PERSONA_CITY_WEIGHTS = {
    "early_career": {
        "Bengaluru": 0.32, "Hyderabad": 0.26, "Pune": 0.14,
        "Mumbai": 0.12, "Chennai": 0.09, "Delhi": 0.07,
    },
    "family_focused": {
        "Pune": 0.30, "Chennai": 0.26, "Hyderabad": 0.16,
        "Bengaluru": 0.12, "Mumbai": 0.10, "Delhi": 0.06,
    },
    "budget_focused": {
        "Hyderabad": 0.30, "Pune": 0.26, "Chennai": 0.18,
        "Bengaluru": 0.13, "Delhi": 0.08, "Mumbai": 0.05,
    },
}


def _weighted_city_choice(persona, exclude_city=None):
    """Picks a city for selected_city based on persona weighting, optionally excluding one city."""
    weights = dict(PERSONA_CITY_WEIGHTS[persona])
    if exclude_city and exclude_city in weights:
        del weights[exclude_city]

    cities = list(weights.keys())
    probs = np.array(list(weights.values()))
    probs = probs / probs.sum()

    return np.random.choice(cities, p=probs)


def generate_relocation_queries(user_profiles_df):
    print("\n[generate_synthetic_data] Generating relocation_queries.csv...")

    rows = []
    query_id = 1

    start_date = date(2023, 1, 1)
    end_date = date(2024, 12, 31)
    date_range_days = (end_date - start_date).days

    for _, user in user_profiles_df.iterrows():
        user_id = user["user_id"]
        persona = user["persona"]
        current_city = user["current_city"]
        target_cities_list = user["target_cities"].split("|")

        # compared_cities: current_city + target_cities (deduplicated)
        compared_cities = [current_city] + [c for c in target_cities_list if c != current_city]
        compared_cities_str = "|".join(compared_cities)

        # selected_city: weighted by persona, must be one of the compared cities
        # Build a persona-weighted choice restricted to the compared set
        weights = dict(PERSONA_CITY_WEIGHTS[persona])
        candidate_weights = {c: weights.get(c, 0.02) for c in compared_cities if c != current_city}

        if not candidate_weights:
            # Edge case: only current_city in compared list (shouldn't happen given target_cities >= 2)
            selected_city = current_city
        else:
            cities = list(candidate_weights.keys())
            probs = np.array(list(candidate_weights.values()))
            probs = probs / probs.sum()
            selected_city = np.random.choice(cities, p=probs)

        random_offset = int(np.random.randint(0, date_range_days))
        query_date = pd.Timestamp(start_date) + pd.Timedelta(days=random_offset)

        rows.append({
            "query_id": query_id,
            "user_id": user_id,
            "compared_cities": compared_cities_str,
            "persona": persona,
            "selected_city": selected_city,
            "query_date": query_date.strftime("%Y-%m-%d"),
        })
        query_id += 1

    df = pd.DataFrame(rows)
    out_path = os.path.join(SYNTHETIC_DIR, "relocation_queries.csv")
    df.to_csv(out_path, index=False)

    print(f"[generate_synthetic_data] Saved relocation_queries.csv -> {out_path}")
    print(f"[generate_synthetic_data] Rows: {len(df)}")

    print("\n  Selected city distribution by persona:")
    for persona in PERSONAS:
        subset = df[df["persona"] == persona]
        dist = subset["selected_city"].value_counts(normalize=True).round(3)
        print(f"\n  {persona} (n={len(subset)}):")
        print(f"  {dist.to_string()}")

    return df


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("GENERATE SYNTHETIC DATA — UrbanPulse")
    print(f"Random seed: {SEED}")
    print("=" * 70)

    health_seeds = load_real_hospital_seeds()

    city_master_df = generate_city_master(health_seeds)
    monthly_metrics_df = generate_monthly_metrics(city_master_df)
    user_profiles_df = generate_user_profiles(n=300)
    relocation_queries_df = generate_relocation_queries(user_profiles_df)

    print("\n" + "=" * 70)
    print("FINAL ROW COUNT SUMMARY")
    print("=" * 70)
    print(f"city_master.csv            : {len(city_master_df)} rows")
    print(f"monthly_city_metrics.csv   : {len(monthly_metrics_df)} rows")
    print(f"user_profiles.csv          : {len(user_profiles_df)} rows")
    print(f"relocation_queries.csv     : {len(relocation_queries_df)} rows")
    print(f"\nAll files saved to: {SYNTHETIC_DIR}")
    print("\n[generate_synthetic_data] Done.")

    return {
        "city_master": city_master_df,
        "monthly_city_metrics": monthly_metrics_df,
        "user_profiles": user_profiles_df,
        "relocation_queries": relocation_queries_df,
    }


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[generate_synthetic_data] ERROR: {e}", file=sys.stderr)
        sys.exit(1)