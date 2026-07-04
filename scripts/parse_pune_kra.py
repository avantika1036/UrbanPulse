"""
parse_pune_kra.py

Parses the messy multi-header Pune Municipal Corporation KRA Daily Report
(Jan 2017 - Dec 2017) CSV into a clean tabular format.

Source structure (hardcoded, based on inspection of the raw file):
  - Row 0: Report title
  - Row 1: Report date
  - Row 2: Column headers (SR.NO, DEPARTMENT NAME, SUBJECT, JANUARY..DECEMBER, PROGRESSIVE CURRENT YEAR)
  - Rows 3-50: Data rows (SR.NO and DEPARTMENT NAME are sparse - only populated on
    the first row of each department block; forward-fill required)
  - Rows 51+: Footer notes (Total / NOTE: ... rows) - discarded

Known validation values (from manual inspection of source):
  - Dengue annual total            = 6390
  - Swine Flu annual cases         = 703
  - Swine Flu annual deaths        = 157
  - Total births (annual)          = 54669
  - Total infant mortality (annual) = 2040

Output: data/processed/pune_kra_2017.csv
Also exposes get_pune_kra_summary() returning a clean dict for
load_real_data.py to consume directly (births_deaths + disease_burden values).
"""

import os
import sys
import pandas as pd
import numpy as np

# ── PATHS ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RAW_PATH = os.path.join(PROJECT_ROOT, "data", "real", "Pune-Diseases-and-Causes-of-Deaths-Data.csv")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
OUTPUT_PATH = os.path.join(PROCESSED_DIR, "pune_kra_2017.csv")

MONTH_COLS = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]

# ── VALIDATION TARGETS ──────────────────────────────────────────────────────
VALIDATION_TARGETS = {
    "Dengue": {"metric": "Dengue", "expected_annual_total": 6390},
    "Swine Flu cases": {"metric": "Swine Flu", "expected_annual_total": 703},
    "Swine Flu deaths": {"metric": "Swine Flu (DEATHS)", "expected_annual_total": 157},
    "Total births": {"metric": "Births - Total", "expected_annual_total": 54669},
    "Infant mortality total": {"metric": "Infant Mortality - Total", "expected_annual_total": 2040},
}


def _clean_numeric(val):
    """Convert a raw cell value to int, handling commas, blanks, and NaN."""
    if pd.isna(val):
        return 0
    if isinstance(val, (int, float)):
        if isinstance(val, float) and np.isnan(val):
            return 0
        return int(val)
    s = str(val).strip().replace(",", "")
    if s == "" or s.lower() == "nan":
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def parse_pune_kra_raw():
    """
    Reads the raw Pune KRA CSV and extracts the structured data block
    (rows 3-50 in the raw file, 0-indexed after header skip).
    Returns a cleaned DataFrame with columns:
      department, subject, jan..dec, annual_total
    """
    if not os.path.exists(RAW_PATH):
        raise FileNotFoundError(
            f"Pune KRA source file not found at: {RAW_PATH}\n"
            f"Expected: data/real/Pune-Diseases-and-Causes-of-Deaths-Data.csv"
        )

    print(f"[parse_pune_kra] Reading raw file: {RAW_PATH}")

    # Read with encoding fallback for BOM characters
    try:
        raw = pd.read_csv(RAW_PATH, encoding="utf-8-sig", header=None, dtype=str)
    except UnicodeDecodeError:
        raw = pd.read_csv(RAW_PATH, encoding="latin-1", header=None, dtype=str)

    print(f"[parse_pune_kra] Raw shape: {raw.shape}")

    # Hardcoded structure: header row is at index 2 (0-indexed), data starts at index 3
    HEADER_ROW_IDX = 3
    DATA_START_IDX = 4
    DATA_END_IDX = 52

    # Verify header row looks as expected
    header_row = raw.iloc[HEADER_ROW_IDX]
    header_check = str(header_row[0]).strip().upper()
    if "SR" not in header_check:
        print(
            f"[parse_pune_kra] WARNING: header row at index {HEADER_ROW_IDX} "
            f"does not match expected 'SR.NO' pattern (found: '{header_check}'). "
            f"Proceeding with hardcoded structure anyway."
        )

    data_block = raw.iloc[DATA_START_IDX:DATA_END_IDX].copy()
    data_block.columns = ["sr_no", "department", "subject"] + MONTH_COLS + ["annual_total"] + \
                          [f"extra_{i}" for i in range(data_block.shape[1] - 16)]

    # Keep only the columns we need
    keep_cols = ["sr_no", "department", "subject"] + MONTH_COLS + ["annual_total"]
    data_block = data_block[keep_cols]

    # Forward-fill department name (sparse in source - only set on first row of block)
    data_block["department"] = data_block["department"].replace("", np.nan)
    data_block["department"] = data_block["department"].ffill()

    # Drop rows where subject is empty/NaN (these are pure separator rows)
    data_block = data_block[data_block["subject"].notna()]
    data_block = data_block[data_block["subject"].astype(str).str.strip() != ""]

    # Clean numeric columns
    for col in MONTH_COLS + ["annual_total"]:
        data_block[col] = data_block[col].apply(_clean_numeric)

    # Clean string columns
    data_block["department"] = data_block["department"].astype(str).str.strip()
    data_block["subject"] = data_block["subject"].astype(str).str.strip()

    data_block = data_block[["department", "subject"] + MONTH_COLS + ["annual_total"]]
    data_block = data_block.reset_index(drop=True)

    print(f"[parse_pune_kra] Parsed {len(data_block)} metric rows from KRA report")

    return data_block


def validate_parsed_data(df):
    """Cross-check known values against the parsed data. Raises on mismatch."""
    print("\n[parse_pune_kra] === VALIDATION ===")
    all_passed = True

    for label, target in VALIDATION_TARGETS.items():
        match = df[df["subject"] == target["metric"]]
        if match.empty:
            print(f"  FAIL  {label}: subject '{target['metric']}' not found in parsed data")
            all_passed = False
            continue

        actual = int(match.iloc[0]["annual_total"])
        expected = target["expected_annual_total"]
        status = "PASS" if actual == expected else "FAIL"
        if actual != expected:
            all_passed = False
        print(f"  {status}  {label}: expected={expected}, actual={actual}")

    print("[parse_pune_kra] === VALIDATION " + ("PASSED" if all_passed else "FAILED") + " ===\n")

    if not all_passed:
        raise ValueError(
            "Pune KRA validation failed - parsed values do not match known reference "
            "values. Check the hardcoded row indices in parse_pune_kra_raw()."
        )

    return all_passed


def get_pune_kra_summary(df=None):
    """
    Returns a clean dict summarizing the key KRA metrics, structured for
    direct consumption by load_real_data.py.

    Returns:
        {
            "city": "Pune",
            "year": 2017,
            "births_deaths": {
                "total_births": int, "births_male": int, "births_female": int,
                "total_deaths": int, "deaths_male": int, "deaths_female": int,
                "infant_mortality": int, "infant_mortality_male": int,
                "infant_mortality_female": int,
            },
            "disease_burden": [
                {"disease": str, "annual_cases": int, "annual_deaths": int}, ...
            ]
        }
    """
    if df is None:
        df = parse_pune_kra_raw()

    def get_val(subject):
        match = df[df["subject"] == subject]
        if match.empty:
            return 0
        return int(match.iloc[0]["annual_total"])

    births_deaths = {
        "total_births": get_val("Births - Total"),
        "births_male": get_val("Births - Male"),
        "births_female": get_val("Births - Female"),
        "total_deaths": get_val("Deaths - Total"),
        "deaths_male": get_val("Deaths - Male"),
        "deaths_female": get_val("Deaths - Female"),
        "infant_mortality": get_val("Infant Mortality - Total"),
        "infant_mortality_male": get_val("Infant Mortality - Male"),
        "infant_mortality_female": get_val("Infant Mortality - Female"),
    }

    disease_burden = [
        {
            "disease": "Dengue",
            "annual_cases": get_val("Dengue"),
            "annual_deaths": get_val("No. of Dengue Death"),
        },
        {
            "disease": "Chikungunya",
            "annual_cases": get_val("Chikunguinia"),
            "annual_deaths": get_val("No. of Chikunguinia Death"),
        },
        {
            "disease": "Malaria",
            "annual_cases": get_val("Malaria"),
            "annual_deaths": get_val("No. of Malaria Death"),
        },
        {
            "disease": "Swine Flu",
            "annual_cases": get_val("Swine Flu"),
            "annual_deaths": get_val("Swine Flu (DEATHS)"),
        },
        {
            "disease": "Rabies",
            "annual_cases": get_val("Rabies Case Found"),
            "annual_deaths": get_val("Rabies Death (PMC)") + get_val("Rabies Death (OPMC)"),
        },
    ]

    return {
        "city": "Pune",
        "year": 2017,
        "births_deaths": births_deaths,
        "disease_burden": disease_burden,
    }


def main():
    print("=" * 70)
    print("PUNE KRA 2017 PARSER")
    print("=" * 70)

    df = parse_pune_kra_raw()
    validate_parsed_data(df)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"[parse_pune_kra] Saved cleaned KRA data to: {OUTPUT_PATH}")
    print(f"[parse_pune_kra] Output shape: {df.shape}")

    summary = get_pune_kra_summary(df)

    print("\n[parse_pune_kra] === SUMMARY ===")
    print(f"City: {summary['city']}, Year: {summary['year']}")
    print("\nBirths & Deaths:")
    for k, v in summary["births_deaths"].items():
        print(f"  {k}: {v:,}")
    print("\nDisease Burden:")
    for d in summary["disease_burden"]:
        print(f"  {d['disease']}: {d['annual_cases']:,} cases, {d['annual_deaths']:,} deaths")

    # Computed IMR check
    imr = (summary["births_deaths"]["infant_mortality"] /
           summary["births_deaths"]["total_births"]) * 1000
    print(f"\nDerived Infant Mortality Rate: {imr:.2f} per 1,000 live births")

    print("\n[parse_pune_kra] Done.")
    return summary


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[parse_pune_kra] ERROR: {e}", file=sys.stderr)
        sys.exit(1)