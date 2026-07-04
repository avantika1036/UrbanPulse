"""
load_real_data.py

Reads and cleans all 8 real government CSV files from data/real/, computes
derived metrics, and produces two standardized processed outputs:

  data/processed/city_health_summary.csv  - one row per city per year
  data/processed/city_hospital_counts.csv - one row per city (hospital data only)

Cities with births/deaths data: Bengaluru, Chennai, Delhi, Pune
Cities with hospital/facility data: Bengaluru, Mumbai, Chennai
No real data: Hyderabad (synthetic only, generated separately)

Run standalone:  python scripts/load_real_data.py
"""

import os
import sys
import pandas as pd
import numpy as np

# Allow importing parse_pune_kra.py from the same directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from parse_pune_kra import parse_pune_kra_raw, get_pune_kra_summary, validate_parsed_data

PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
REAL_DIR = os.path.join(PROJECT_ROOT, "data", "real")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

# ── FILE PATHS ───────────────────────────────────────────────────────────────
PATHS = {
    "bengaluru_bd": os.path.join(REAL_DIR, "Bengaluru-Annual-Births-and-Deaths-data.csv"),
    "bengaluru_hosp": os.path.join(REAL_DIR, "Bengaluru-Hospitals.csv"),
    "chennai_bd": os.path.join(REAL_DIR, "Chennai-Annual-Births-and-Deaths-data.csv"),
    "chennai_hosp": os.path.join(REAL_DIR, "Chennai-Health-Centres.csv"),
    "delhi_bd": os.path.join(REAL_DIR, "Delhi-Annual-Births-and-Deaths-data.csv"),
    "mumbai_hosp": os.path.join(REAL_DIR, "Mumbai-City-Public-Health-Centres.csv"),
    "pune_bd": os.path.join(REAL_DIR, "Pune-Annual-Births-and-Deaths-Data.csv"),
    "pune_kra": os.path.join(REAL_DIR, "Pune-Diseases-and-Causes-of-Deaths-Data.csv"),
}

# Approximate population estimates per city per relevant year band, used only
# for crude_birth_rate / crude_death_rate derivation. These are not stored
# in the output, only used as denominators in the rate calculation.
POP_ESTIMATES = {
    # city: {year: population}
    "Bengaluru": {
        2001: 5_690_000, 2011: 8_440_000, 2024: 14_000_000,
    },
    "Chennai": {
        2011: 4_650_000, 2018: 10_900_000, 2024: 11_500_000,
    },
    "Delhi": {
        2011: 16_750_000, 2017: 29_400_000, 2024: 32_900_000,
    },
    "Pune": {
        1981: 1_690_000, 2011: 3_120_000, 2018: 4_100_000,
    },
}


def _read_csv_safe(path, **kwargs):
    """Read CSV with BOM-safe encoding fallback."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required real data file not found: {path}")
    try:
        return pd.read_csv(path, encoding="utf-8-sig", **kwargs)
    except UnicodeDecodeError:
        print(f"  [warn] utf-8-sig failed for {os.path.basename(path)}, falling back to latin-1")
        return pd.read_csv(path, encoding="latin-1", **kwargs)


def _interpolate_population(city, year):
    """
    Linear interpolation/extrapolation of population for a given city/year
    using the anchor points in POP_ESTIMATES. Used only for rate denominators.
    """
    anchors = POP_ESTIMATES.get(city)
    if not anchors:
        return None

    years = sorted(anchors.keys())
    pops = [anchors[y] for y in years]

    if year <= years[0]:
        # Extrapolate backward using first two points
        if len(years) >= 2:
            slope = (pops[1] - pops[0]) / (years[1] - years[0])
            return max(int(pops[0] + slope * (year - years[0])), 1)
        return pops[0]

    if year >= years[-1]:
        # Extrapolate forward using last two points
        if len(years) >= 2:
            slope = (pops[-1] - pops[-2]) / (years[-1] - years[-2])
            return max(int(pops[-1] + slope * (year - years[-1])), 1)
        return pops[-1]

    # Interpolate between two surrounding anchors
    for i in range(len(years) - 1):
        if years[i] <= year <= years[i + 1]:
            y0, y1 = years[i], years[i + 1]
            p0, p1 = pops[i], pops[i + 1]
            frac = (year - y0) / (y1 - y0)
            return int(p0 + frac * (p1 - p0))

    return pops[-1]


# ── BIRTHS / DEATHS PROCESSORS ─────────────────────────────────────────────

def process_bengaluru_births_deaths():
    print("\n[load_real_data] Processing Bengaluru births/deaths...")
    df = _read_csv_safe(PATHS["bengaluru_bd"])
    df.columns = df.columns.str.strip()

    expected_cols = [
        "year", "city", "male_births", "female_births", "total_births",
        "bbmp_total_births", "male_deaths", "female_deaths", "total_deaths",
        "bbmp_total_deaths",
    ]
    missing = set(expected_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Bengaluru births/deaths file missing expected columns: {missing}")

    out = pd.DataFrame()
    out["city"] = df["city"]
    out["year"] = df["year"].astype(int)
    out["total_births"] = df["total_births"].astype(int)
    out["total_deaths"] = df["total_deaths"].astype(int)
    out["births_male"] = df["male_births"].astype(int)
    out["births_female"] = df["female_births"].astype(int)
    out["deaths_male"] = df["male_deaths"].astype(int)
    out["deaths_female"] = df["female_deaths"].astype(int)
    out["deaths_others"] = np.nan
    out["bbmp_total_births"] = df["bbmp_total_births"].astype(int)
    out["bbmp_total_deaths"] = df["bbmp_total_deaths"].astype(int)
    out["births_registered"] = np.nan
    out["deaths_registered"] = np.nan
    out["infant_mortality"] = np.nan
    out["partial_year"] = False
    out["data_source"] = "real"

    out["crude_death_rate"] = out["total_deaths"] / out["total_births"]
    out["bbmp_birth_coverage_pct"] = out["bbmp_total_births"] / out["total_births"]
    out["bbmp_death_coverage_pct"] = out["bbmp_total_deaths"] / out["total_deaths"]

    out["pop_estimate"] = out["year"].apply(lambda y: _interpolate_population("Bengaluru", y))
    out["crude_birth_rate_per_1000"] = (out["total_births"] / out["pop_estimate"]) * 1000
    out["crude_death_rate_per_1000"] = (out["total_deaths"] / out["pop_estimate"]) * 1000

    print(f"  Rows: {len(out)} | Years: {out['year'].min()}-{out['year'].max()}")
    print(f"  Total births (sum): {out['total_births'].sum():,}")
    print(f"  Total deaths (sum): {out['total_deaths'].sum():,}")
    print(f"  Mean crude_death_rate (births-based): {out['crude_death_rate'].mean():.4f}")
    print(f"  Mean crude_death_rate_per_1000 (pop-based): {out['crude_death_rate_per_1000'].mean():.2f}")

    return out


def process_chennai_births_deaths():
    print("\n[load_real_data] Processing Chennai births/deaths...")
    df = _read_csv_safe(PATHS["chennai_bd"])
    df.columns = df.columns.str.strip()

    expected_cols = [
        "year", "city", "births_reported", "births_registered",
        "deaths_reported", "deaths_registered",
    ]
    missing = set(expected_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Chennai births/deaths file missing expected columns: {missing}")

    out = pd.DataFrame()
    out["city"] = df["city"]
    out["year"] = df["year"].astype(int)
    out["total_births"] = df["births_reported"].astype(int)
    out["total_deaths"] = df["deaths_reported"].astype(int)
    out["births_male"] = np.nan
    out["births_female"] = np.nan
    out["deaths_male"] = np.nan
    out["deaths_female"] = np.nan
    out["deaths_others"] = np.nan
    out["bbmp_total_births"] = np.nan
    out["bbmp_total_deaths"] = np.nan
    out["births_registered"] = df["births_registered"].astype(int)
    out["deaths_registered"] = df["deaths_registered"].astype(int)
    out["infant_mortality"] = np.nan
    out["partial_year"] = False
    out["data_source"] = "real"

    out["crude_death_rate"] = out["total_deaths"] / out["total_births"]
    out["registration_completeness_births"] = out["births_registered"] / out["total_births"]
    out["registration_completeness_deaths"] = out["deaths_registered"] / out["total_deaths"]

    out["pop_estimate"] = out["year"].apply(lambda y: _interpolate_population("Chennai", y))
    out["crude_birth_rate_per_1000"] = (out["total_births"] / out["pop_estimate"]) * 1000
    out["crude_death_rate_per_1000"] = (out["total_deaths"] / out["pop_estimate"]) * 1000

    print(f"  Rows: {len(out)} | Years: {out['year'].min()}-{out['year'].max()}")
    print(f"  Total births (sum): {out['total_births'].sum():,}")
    print(f"  Total deaths (sum): {out['total_deaths'].sum():,}")
    print(f"  Mean crude_death_rate: {out['crude_death_rate'].mean():.4f}")
    print(f"  Mean registration completeness (births): {out['registration_completeness_births'].mean():.4f}")

    return out


def process_delhi_births_deaths():
    print("\n[load_real_data] Processing Delhi births/deaths...")
    df = _read_csv_safe(PATHS["delhi_bd"])
    df.columns = df.columns.str.strip()

    expected_cols = ["year", "city", "births", "deaths_male", "deaths_female",
                      "deaths_others", "total_deaths"]
    missing = set(expected_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Delhi births/deaths file missing expected columns: {missing}")

    out = pd.DataFrame()
    out["city"] = df["city"]
    out["year"] = df["year"].astype(int)
    out["total_births"] = df["births"].astype(int)
    out["total_deaths"] = df["total_deaths"].astype(int)
    out["births_male"] = np.nan
    out["births_female"] = np.nan
    out["deaths_male"] = df["deaths_male"].astype(int)
    out["deaths_female"] = df["deaths_female"].astype(int)
    out["deaths_others"] = df["deaths_others"].astype(int)
    out["bbmp_total_births"] = np.nan
    out["bbmp_total_deaths"] = np.nan
    out["births_registered"] = np.nan
    out["deaths_registered"] = np.nan
    out["infant_mortality"] = np.nan
    out["partial_year"] = False
    out["data_source"] = "real"

    out["crude_death_rate"] = out["total_deaths"] / out["total_births"]
    out["male_death_share"] = out["deaths_male"] / out["total_deaths"]

    # Sanity check: deaths_male + deaths_female + deaths_others should equal total_deaths
    check_sum = out["deaths_male"] + out["deaths_female"] + out["deaths_others"]
    mismatch = (check_sum != out["total_deaths"]).sum()
    if mismatch > 0:
        print(f"  [warn] {mismatch} row(s) where deaths_male+female+others != total_deaths")

    out["pop_estimate"] = out["year"].apply(lambda y: _interpolate_population("Delhi", y))
    out["crude_birth_rate_per_1000"] = (out["total_births"] / out["pop_estimate"]) * 1000
    out["crude_death_rate_per_1000"] = (out["total_deaths"] / out["pop_estimate"]) * 1000

    print(f"  Rows: {len(out)} | Years: {out['year'].min()}-{out['year'].max()}")
    print(f"  Total births (sum): {out['total_births'].sum():,}")
    print(f"  Total deaths (sum): {out['total_deaths'].sum():,}")
    print(f"  Mean crude_death_rate: {out['crude_death_rate'].mean():.4f}")
    print(f"  Mean male death share: {out['male_death_share'].mean():.4f}")

    return out


def process_pune_births_deaths():
    print("\n[load_real_data] Processing Pune births/deaths...")
    df = _read_csv_safe(PATHS["pune_bd"])
    df.columns = df.columns.str.strip()

    expected_cols = ["year", "city", "births_male", "births_female",
                      "deaths_male", "deaths_female", "partial_year"]
    missing = set(expected_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Pune births/deaths file missing expected columns: {missing}")

    out = pd.DataFrame()
    out["city"] = df["city"]
    out["year"] = df["year"].astype(int)
    out["births_male"] = df["births_male"].astype(int)
    out["births_female"] = df["births_female"].astype(int)
    out["deaths_male"] = df["deaths_male"].astype(int)
    out["deaths_female"] = df["deaths_female"].astype(int)
    out["total_births"] = out["births_male"] + out["births_female"]
    out["total_deaths"] = out["deaths_male"] + out["deaths_female"]
    out["deaths_others"] = np.nan
    out["bbmp_total_births"] = np.nan
    out["bbmp_total_deaths"] = np.nan
    out["births_registered"] = np.nan
    out["deaths_registered"] = np.nan
    out["infant_mortality"] = np.nan
    # Robust boolean parsing regardless of source representation
    out["partial_year"] = df["partial_year"].astype(str).str.strip().str.lower().isin(
        ["true", "1", "yes"]
    )
    out["data_source"] = "real"

    out["crude_death_rate"] = out["total_deaths"] / out["total_births"]
    out["sex_ratio_births"] = (out["births_female"] / out["births_male"]) * 1000

    out["pop_estimate"] = out["year"].apply(lambda y: _interpolate_population("Pune", y))
    out["crude_birth_rate_per_1000"] = (out["total_births"] / out["pop_estimate"]) * 1000
    out["crude_death_rate_per_1000"] = (out["total_deaths"] / out["pop_estimate"]) * 1000

    # Inject KRA 2017 infant mortality into the matching year row
    print("  Cross-referencing Pune KRA 2017 data via parse_pune_kra...")
    kra_df = parse_pune_kra_raw()
    validate_parsed_data(kra_df)
    kra_summary = get_pune_kra_summary(kra_df)

    year_2017_mask = out["year"] == 2017
    if year_2017_mask.any():
        out.loc[year_2017_mask, "infant_mortality"] = kra_summary["births_deaths"]["infant_mortality"]

        # Cross-check KRA totals against the annual births/deaths file for 2017
        kra_births = kra_summary["births_deaths"]["total_births"]
        kra_deaths = kra_summary["births_deaths"]["total_deaths"]
        file_births = int(out.loc[year_2017_mask, "total_births"].iloc[0])
        file_deaths = int(out.loc[year_2017_mask, "total_deaths"].iloc[0])

        print(f"  KRA 2017 total_births={kra_births:,} vs annual file total_births={file_births:,}")
        print(f"  KRA 2017 total_deaths={kra_deaths:,} vs annual file total_deaths={file_deaths:,}")
        if kra_births != file_births:
            print(f"  [note] KRA and annual-file birth totals differ - "
                  f"both are real but from different reporting systems. Annual file value retained as canonical.")
        if kra_deaths != file_deaths:
            print(f"  [note] KRA and annual-file death totals differ - "
                  f"both are real but from different reporting systems. Annual file value retained as canonical.")

    print(f"  Rows: {len(out)} | Years: {out['year'].min()}-{out['year'].max()}")
    print(f"  Partial year rows: {out['partial_year'].sum()}")
    print(f"  Total births (sum, excl. partial): {out[~out['partial_year']]['total_births'].sum():,}")
    print(f"  Total deaths (sum, excl. partial): {out[~out['partial_year']]['total_deaths'].sum():,}")
    print(f"  Mean crude_death_rate (excl. partial): {out[~out['partial_year']]['crude_death_rate'].mean():.4f}")
    if year_2017_mask.any():
        print(f"  2017 infant_mortality injected from KRA: {out.loc[year_2017_mask, 'infant_mortality'].iloc[0]:,.0f}")

    return out


# ── HOSPITAL / FACILITY PROCESSORS ─────────────────────────────────────────

def process_bengaluru_hospitals():
    print("\n[load_real_data] Processing Bengaluru hospitals...")
    df = _read_csv_safe(PATHS["bengaluru_hosp"], on_bad_lines="skip")
    df.columns = df.columns.str.strip()

    expected_cols = ["city", "facility_name", "facility_type", "beds", "ward", "address"]
    missing = set(expected_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Bengaluru hospitals file missing expected columns: {missing}")

    df["facility_name"] = df["facility_name"].astype(str).str.strip()
    df["facility_type"] = df["facility_type"].astype(str).str.strip()
    df["beds"] = pd.to_numeric(df["beds"], errors="coerce").fillna(0).astype(int)

    total_facilities = len(df)
    total_beds = int(df["beds"].sum())
    has_bed_data = bool((df["beds"] > 0).any())

    # All Bengaluru facilities in this dataset are BBMP (public)
    public_count = int(df["facility_type"].str.contains("BBMP", case=False, na=False).sum())
    private_count = total_facilities - public_count

    facility_type_breakdown = df["facility_type"].value_counts().to_dict()

    print(f"  Total facilities: {total_facilities}")
    print(f"  Total beds: {total_beds} (has_bed_data={has_bed_data} - source has no real bed counts)")
    print(f"  Public: {public_count} | Private: {private_count}")
    print(f"  Facility type breakdown: {facility_type_breakdown}")

    return {
        "city": "Bengaluru",
        "total_facilities": total_facilities,
        "total_beds": total_beds,
        "has_bed_data": has_bed_data,
        "public_count": public_count,
        "private_count": private_count,
        "data_source": "real",
        "data_confidence": 0.80,  # penalized: no real bed data
    }


def process_chennai_hospitals():
    print("\n[load_real_data] Processing Chennai health centres...")
    df = _read_csv_safe(PATHS["chennai_hosp"])
    df.columns = df.columns.str.strip()

    expected_cols = ["sno", "city", "zone_no", "div_no", "facility_name", "address"]
    missing = set(expected_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Chennai health centres file missing expected columns: {missing}")

    df["facility_name"] = df["facility_name"].astype(str).str.strip()

    total_facilities = len(df)
    total_beds = 0  # No bed data in source - all UCHCs
    has_bed_data = False
    public_count = total_facilities  # All UCHCs are government-run
    private_count = 0
    zone_count = df["zone_no"].nunique()

    print(f"  Total facilities (UCHCs): {total_facilities}")
    print(f"  Total beds: {total_beds} (has_bed_data={has_bed_data} - no bed data in source)")
    print(f"  Public: {public_count} | Private: {private_count}")
    print(f"  Distinct zones covered: {zone_count}")

    return {
        "city": "Chennai",
        "total_facilities": total_facilities,
        "total_beds": total_beds,
        "has_bed_data": has_bed_data,
        "public_count": public_count,
        "private_count": private_count,
        "data_source": "real",
        "data_confidence": 0.75,  # penalized: no real bed data, small facility count
    }


def process_mumbai_hospitals():
    print("\n[load_real_data] Processing Mumbai hospitals...")
    df = _read_csv_safe(PATHS["mumbai_hosp"])
    df.columns = df.columns.str.strip()

    expected_cols = ["city", "ward_name", "facility_type", "facility_name", "address", "beds"]
    missing = set(expected_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Mumbai hospitals file missing expected columns: {missing}")

    df["facility_name"] = df["facility_name"].astype(str).str.strip()
    df["facility_type"] = df["facility_type"].astype(str).str.strip()
    df["beds"] = pd.to_numeric(df["beds"], errors="coerce").fillna(0).astype(int)

    total_facilities = len(df)
    total_beds = int(df["beds"].sum())
    has_bed_data = bool((df["beds"] > 0).sum() / total_facilities > 0.5)

    public_types = {"Govt", "BMC", "Municipal"}
    public_count = int(df["facility_type"].isin(public_types).sum())
    private_count = total_facilities - public_count

    ward_count = df["ward_name"].nunique()
    facility_type_breakdown = df["facility_type"].value_counts().to_dict()

    print(f"  Total facilities: {total_facilities}")
    print(f"  Total beds: {total_beds:,} (has_bed_data={has_bed_data})")
    print(f"  Public: {public_count} | Private: {private_count}")
    print(f"  Distinct wards covered: {ward_count}")
    print(f"  Facility type breakdown: {facility_type_breakdown}")

    return {
        "city": "Mumbai",
        "total_facilities": total_facilities,
        "total_beds": total_beds,
        "has_bed_data": has_bed_data,
        "public_count": public_count,
        "private_count": private_count,
        "data_source": "real",
        "data_confidence": 1.00,  # full real data including beds
    }


# ── MAIN ORCHESTRATION ──────────────────────────────────────────────────────

def build_city_health_summary():
    """
    Combines all 4 cities' births/deaths data (Bengaluru, Chennai, Delhi, Pune)
    into a single standardized DataFrame: one row per city per year.
    """
    frames = [
        process_bengaluru_births_deaths(),
        process_chennai_births_deaths(),
        process_delhi_births_deaths(),
        process_pune_births_deaths(),
    ]

    combined = pd.concat(frames, ignore_index=True, sort=False)

    column_order = [
        "city", "year", "total_births", "total_deaths",
        "births_male", "births_female", "deaths_male", "deaths_female", "deaths_others",
        "bbmp_total_births", "bbmp_total_deaths",
        "births_registered", "deaths_registered",
        "infant_mortality",
        "crude_death_rate", "crude_birth_rate_per_1000", "crude_death_rate_per_1000",
        "pop_estimate", "partial_year", "data_source",
    ]
    # Add any extra columns not in the fixed order (e.g. registration_completeness_*)
    extra_cols = [c for c in combined.columns if c not in column_order]
    combined = combined[column_order + extra_cols]

    combined = combined.sort_values(["city", "year"]).reset_index(drop=True)

    return combined


def build_city_hospital_counts():
    """
    Combines hospital/facility summary stats for the 3 cities with real
    hospital data (Bengaluru, Mumbai, Chennai) into one row per city.
    """
    records = [
        process_bengaluru_hospitals(),
        process_mumbai_hospitals(),
        process_chennai_hospitals(),
    ]
    df = pd.DataFrame(records)
    df = df[[
        "city", "total_facilities", "total_beds", "has_bed_data",
        "public_count", "private_count", "data_source", "data_confidence",
    ]]
    return df


def main():
    print("=" * 70)
    print("LOAD REAL DATA — UrbanPulse ETL")
    print("=" * 70)

    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # ── Births / Deaths ──────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("STEP 1: BIRTHS & DEATHS PROCESSING")
    print("-" * 70)

    city_health_summary = build_city_health_summary()
    health_out_path = os.path.join(PROCESSED_DIR, "city_health_summary.csv")
    city_health_summary.to_csv(health_out_path, index=False)

    print(f"\n[load_real_data] Saved city_health_summary.csv -> {health_out_path}")
    print(f"[load_real_data] Shape: {city_health_summary.shape}")
    print(f"[load_real_data] Cities covered: {sorted(city_health_summary['city'].unique().tolist())}")
    print(f"[load_real_data] Year range: {city_health_summary['year'].min()}-{city_health_summary['year'].max()}")

    # ── Hospitals / Facilities ──────────────────────────────────────────
    print("\n" + "-" * 70)
    print("STEP 2: HOSPITAL / FACILITY PROCESSING")
    print("-" * 70)

    city_hospital_counts = build_city_hospital_counts()
    hosp_out_path = os.path.join(PROCESSED_DIR, "city_hospital_counts.csv")
    city_hospital_counts.to_csv(hosp_out_path, index=False)

    print(f"\n[load_real_data] Saved city_hospital_counts.csv -> {hosp_out_path}")
    print(f"[load_real_data] Shape: {city_hospital_counts.shape}")
    print(city_hospital_counts.to_string(index=False))

    # ── Final Summary ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"city_health_summary.csv  : {len(city_health_summary)} rows "
          f"({len(city_health_summary['city'].unique())} cities)")
    print(f"city_hospital_counts.csv : {len(city_hospital_counts)} rows "
          f"({len(city_hospital_counts['city'].unique())} cities)")
    print("\nCities WITHOUT real births/deaths data: Mumbai, Hyderabad (synthetic only)")
    print("Cities WITHOUT real hospital data: Delhi, Pune, Hyderabad (synthetic only)")
    print("\n[load_real_data] Done.")

    return {
        "city_health_summary": city_health_summary,
        "city_hospital_counts": city_hospital_counts,
    }


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[load_real_data] ERROR: {e}", file=sys.stderr)
        sys.exit(1)