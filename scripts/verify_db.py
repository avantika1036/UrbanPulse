"""
verify_db.py

Connects to PostgreSQL and verifies row counts for every table in the
urbanpulse schema against expected values. Prints a clean ASCII summary
table and exits with code 1 if any REQUIRED data table is empty.

city_scores, recommendations, salary_equivalence are expected to be 0
on a fresh load (they're populated later by the scoring engine, ML
inference, and the API) — these are exempt from the "must not be empty"
check, but their counts are still reported.

Run: python scripts/verify_db.py
Requires: DATABASE_URL environment variable
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

SCHEMA = "urbanpulse"

# Expected row counts. Tables marked allow_empty=True are computed at
# runtime and are NOT required to have data on a fresh load.
EXPECTED_ROWS = {
    "cities":                {"expected": 6,   "allow_empty": False},
    "monthly_city_metrics":  {"expected": 144, "allow_empty": False},
    "city_health_summary":   {"expected": 84,  "allow_empty": False},  # ~84: 24+8+8+44 rows
    "city_hospital_counts":  {"expected": 3,   "allow_empty": False},
    "user_profiles":         {"expected": 300, "allow_empty": False},
    "relocation_queries":    {"expected": 300, "allow_empty": False},
    "city_scores":           {"expected": 0,   "allow_empty": True},
    "recommendations":       {"expected": 0,   "allow_empty": True},
    "salary_equivalence":    {"expected": 0,   "allow_empty": True},
}

# Tolerance for "approximate" expected counts (e.g. city_health_summary
# can legitimately vary slightly based on exact year ranges in source data)
TOLERANCE = {
    "city_health_summary": 5,  # allow +/- 5 rows before flagging MISMATCH
}


def get_engine():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print(
            "\n[verify_db] ERROR: DATABASE_URL environment variable is not set.\n"
            "  Set it before running this script, e.g.:\n"
            "    export DATABASE_URL='postgresql://user:password@localhost:5432/urbanpulse'\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except OperationalError as e:
        print(
            f"\n[verify_db] ERROR: Could not connect to the database.\n"
            f"  Check that PostgreSQL is running and DATABASE_URL is correct.\n"
            f"  Underlying error: {e}\n",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"\n[verify_db] ERROR: Unexpected error while connecting: {e}\n", file=sys.stderr)
        sys.exit(1)


def get_actual_row_count(engine, table_name):
    """Returns the row count, or None if the table doesn't exist."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{table_name}"))
            return result.scalar()
    except Exception:
        return None


def determine_status(table_name, expected, actual, allow_empty):
    """
    Returns one of: 'OK', 'EMPTY', 'MISSING', 'MISMATCH'
    """
    if actual is None:
        return "MISSING"

    if actual == 0:
        if allow_empty:
            return "OK"  # 0 rows is expected/correct for computed tables
        else:
            return "EMPTY"

    tolerance = TOLERANCE.get(table_name, 0)
    if abs(actual - expected) <= tolerance:
        return "OK"

    if allow_empty and actual > 0:
        # Computed table has data already (e.g. re-run after scoring) - fine
        return "OK"

    return "MISMATCH"


def print_ascii_table(rows):
    """
    Prints a clean ASCII table.
    rows: list of dicts with keys: table_name, expected, actual, status
    """
    headers = ["Table Name", "Expected Rows", "Actual Rows", "Status"]

    table_name_w = max(len(headers[0]), max(len(r["table_name"]) for r in rows)) + 2
    expected_w = max(len(headers[1]), max(len(str(r["expected"])) for r in rows)) + 2
    actual_w = max(len(headers[2]), max(len(str(r["actual"])) for r in rows)) + 2
    status_w = max(len(headers[3]), max(len(r["status"]) for r in rows)) + 2

    def sep_line(char="-"):
        return (
            "+" + char * table_name_w +
            "+" + char * expected_w +
            "+" + char * actual_w +
            "+" + char * status_w +
            "+"
        )

    def format_row(table_name, expected, actual, status):
        return (
            f"|{table_name.center(table_name_w)}"
            f"|{str(expected).center(expected_w)}"
            f"|{str(actual).center(actual_w)}"
            f"|{status.center(status_w)}|"
        )

    print(sep_line("="))
    print(format_row(*headers))
    print(sep_line("="))

    for r in rows:
        print(format_row(r["table_name"], r["expected"], r["actual"], r["status"]))

    print(sep_line("-"))


def main():
    print("=" * 70)
    print("VERIFY DATABASE — UrbanPulse")
    print("=" * 70)

    engine = get_engine()
    print(f"[verify_db] Connected successfully.\n")

    rows = []
    has_critical_failure = False

    for table_name, config in EXPECTED_ROWS.items():
        expected = config["expected"]
        allow_empty = config["allow_empty"]
        actual = get_actual_row_count(engine, table_name)

        status = determine_status(table_name, expected, actual, allow_empty)

        rows.append({
            "table_name": f"urbanpulse.{table_name}",
            "expected": expected,
            "actual": actual if actual is not None else "N/A",
            "status": status,
        })

        if status in ("EMPTY", "MISSING"):
            has_critical_failure = True
        elif status == "MISMATCH":
            # Mismatch is a warning, not necessarily critical, but flagged
            pass

    print_ascii_table(rows)

    # ── Summary ──────────────────────────────────────────────────────────
    print()
    ok_count = sum(1 for r in rows if r["status"] == "OK")
    empty_count = sum(1 for r in rows if r["status"] == "EMPTY")
    missing_count = sum(1 for r in rows if r["status"] == "MISSING")
    mismatch_count = sum(1 for r in rows if r["status"] == "MISMATCH")

    print(f"Summary: {ok_count} OK | {empty_count} EMPTY | {missing_count} MISSING | {mismatch_count} MISMATCH")

    if mismatch_count > 0:
        print(
            "\n[verify_db] WARNING: Some tables have row counts that differ from "
            "expected beyond tolerance. This may indicate a partial load or "
            "changed source data. Review the table above."
        )

    if has_critical_failure:
        print(
            "\n[verify_db] FAILURE: One or more required data tables are EMPTY or MISSING.\n"
            "  Required tables (must have data): cities, monthly_city_metrics, "
            "city_health_summary, city_hospital_counts, user_profiles, relocation_queries\n"
            "  Run scripts/load_database.py to populate them.\n"
        )
        sys.exit(1)

    print("\n[verify_db] All required data tables are populated correctly.")
    print("[verify_db] Done.")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n[verify_db] ERROR: {e}", file=sys.stderr)
        sys.exit(1)