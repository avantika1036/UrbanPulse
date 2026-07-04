"""
load_database.py

Loads all CSV outputs (real + synthetic) into PostgreSQL in correct
dependency order, per sql/schema.sql.

Uses SQLAlchemy with DATABASE_URL read from the environment. Upserts via
ON CONFLICT DO NOTHING so the script is safe to re-run without duplicating
rows or failing on already-loaded data.

Tables 7-9 (city_scores, recommendations, salary_equivalence) are computed
at runtime by other parts of the pipeline (scoring engine, ML models, API)
and are intentionally left empty here.

Run: python scripts/load_database.py
Requires: DATABASE_URL environment variable, e.g.
  postgresql://user:password@localhost:5432/urbanpulse
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# ── PATHS ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
SYNTHETIC_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")

SCHEMA = "urbanpulse"


def get_engine():
    # Try individual variables first (works with special-character passwords)
    db_host = os.environ.get("DB_HOST")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")

    if db_host and db_name and db_user and db_pass:
        try:
            import psycopg2
            engine = create_engine(
                "postgresql+psycopg2://",
                creator=lambda: psycopg2.connect(
                    host=db_host,
                    port=int(db_port),
                    dbname=db_name,
                    user=db_user,
                    password=db_pass,
                ),
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[load_database] Connected using DB_* variables.")
            return engine
        except Exception as e:
            print(f"\n[load_database] ERROR: Could not connect.\n  {e}\n", file=sys.stderr)
            sys.exit(1)

    # Fall back to DATABASE_URL
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(
            "\n[load_database] ERROR: No database credentials found.\n"
            "  Set either DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASS\n"
            "  or DATABASE_URL environment variable.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"[load_database] Connected using DATABASE_URL.")
        return engine
    except OperationalError as e:
        print(
            f"\n[load_database] ERROR: Could not connect to the database.\n"
            f"  Underlying error: {e}\n",
            file=sys.stderr,
        )
        sys.exit(1)


def verify_schema_exists(engine):
    """Checks that the urbanpulse schema and its tables exist before loading."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :schema ORDER BY table_name"
                ),
                {"schema": SCHEMA},
            )
            tables = [row[0] for row in result]

        if not tables:
            print(
                f"\n[load_database] ERROR: No tables found in schema '{SCHEMA}'.\n"
                f"  Run sql/schema.sql first:\n"
                f"    psql -U <user> -d <database> -f sql/schema.sql\n",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"[load_database] Found {len(tables)} tables in '{SCHEMA}' schema: {tables}")
        return tables

    except ProgrammingError as e:
        print(
            f"\n[load_database] ERROR: Could not query schema '{SCHEMA}'. "
            f"Has sql/schema.sql been run?\n  Underlying error: {e}\n",
            file=sys.stderr,
        )
        sys.exit(1)


def _read_csv_safe(path, label):
    """Reads a CSV with a clear error if the file is missing."""
    if not os.path.exists(path):
        print(
            f"\n[load_database] ERROR: Required input file not found for '{label}':\n"
            f"  {path}\n"
            f"  Run the relevant upstream script first "
            f"(load_real_data.py / generate_synthetic_data.py).\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return pd.read_csv(path, encoding="utf-8-sig")


def upsert_dataframe(engine, df, table_name, conflict_column, schema=SCHEMA):
    """
    Upserts a DataFrame into a PostgreSQL table using
    INSERT ... ON CONFLICT (conflict_column) DO NOTHING.

    This avoids duplicate-key errors on re-run while keeping the script
    idempotent. conflict_column should be the table's primary key or a
    column with a UNIQUE constraint.
    """
    if df.empty:
        print(f"  [warn] DataFrame for {table_name} is empty — skipping load.")
        return 0

    # Replace NaN with None so they map to SQL NULL correctly
    df = df.where(pd.notnull(df), None)

    columns = list(df.columns)
    columns_sql = ", ".join(f'"{c}"' for c in columns)
    placeholders_sql = ", ".join(f":{c}" for c in columns)

    insert_sql = text(
        f'INSERT INTO {schema}.{table_name} ({columns_sql}) '
        f'VALUES ({placeholders_sql}) '
        f'ON CONFLICT ("{conflict_column}") DO NOTHING'
    )

    records = df.to_dict(orient="records")

    inserted_count = 0
    with engine.begin() as conn:
        for record in records:
            result = conn.execute(insert_sql, record)
            inserted_count += result.rowcount if result.rowcount and result.rowcount > 0 else 0

    return inserted_count


def upsert_dataframe_composite_conflict(engine, df, table_name, conflict_columns, schema=SCHEMA):
    """
    Same as upsert_dataframe but for tables with a composite UNIQUE
    constraint (e.g. city_health_summary on (city_name, year)) instead of
    a single-column primary key.
    """
    if df.empty:
        print(f"  [warn] DataFrame for {table_name} is empty — skipping load.")
        return 0

    df = df.where(pd.notnull(df), None)

    columns = list(df.columns)
    columns_sql = ", ".join(f'"{c}"' for c in columns)
    placeholders_sql = ", ".join(f":{c}" for c in columns)
    conflict_sql = ", ".join(f'"{c}"' for c in conflict_columns)

    insert_sql = text(
        f'INSERT INTO {schema}.{table_name} ({columns_sql}) '
        f'VALUES ({placeholders_sql}) '
        f'ON CONFLICT ({conflict_sql}) DO NOTHING'
    )

    records = df.to_dict(orient="records")

    inserted_count = 0
    with engine.begin() as conn:
        for record in records:
            result = conn.execute(insert_sql, record)
            inserted_count += result.rowcount if result.rowcount and result.rowcount > 0 else 0

    return inserted_count


def get_row_count(engine, table_name, schema=SCHEMA):
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{table_name}"))
        return result.scalar()


# ── LOAD FUNCTIONS — ONE PER TABLE, IN DEPENDENCY ORDER ────────────────────

def load_cities(engine):
    print("\n[load_database] (1/9) Loading urbanpulse.cities ...")
    path = os.path.join(SYNTHETIC_DIR, "city_master.csv")
    df = _read_csv_safe(path, "cities")

    inserted = upsert_dataframe(engine, df, "cities", conflict_column="city_id")
    total = get_row_count(engine, "cities")
    print(f"  Source rows: {len(df)} | Newly inserted: {inserted} | Table total: {total}")
    return total


def load_city_health_summary(engine):
    print("\n[load_database] (2/9) Loading urbanpulse.city_health_summary ...")
    path = os.path.join(PROCESSED_DIR, "city_health_summary.csv")
    df = _read_csv_safe(path, "city_health_summary")

    # bd_id in source is implicit (DataFrame index based); table uses
    # bd_id SERIAL, so we must NOT pass it. Drop if present, drop city
    # column duplication issues are not expected since processed CSV
    # already uses 'city' as the column name — schema expects 'city_name'.
    if "city" in df.columns and "city_name" not in df.columns:
        df = df.rename(columns={"city": "city_name"})

    if "bd_id" in df.columns:
        df = df.drop(columns=["bd_id"])

    # Keep only columns that exist in the target table schema
    valid_columns = [
        "city_name", "year", "total_births", "total_deaths",
        "births_male", "births_female", "deaths_male", "deaths_female", "deaths_others",
        "bbmp_total_births", "bbmp_total_deaths",
        "births_registered", "deaths_registered", "infant_mortality",
        "crude_death_rate", "crude_birth_rate_per_1000", "crude_death_rate_per_1000",
        "pop_estimate", "bbmp_birth_coverage_pct", "bbmp_death_coverage_pct",
        "registration_completeness_births", "registration_completeness_deaths",
        "male_death_share", "sex_ratio_births", "partial_year", "data_source",
    ]
    df = df[[c for c in valid_columns if c in df.columns]]

    inserted = upsert_dataframe_composite_conflict(
        engine, df, "city_health_summary", conflict_columns=["city_name", "year"]
    )
    total = get_row_count(engine, "city_health_summary")
    print(f"  Source rows: {len(df)} | Newly inserted: {inserted} | Table total: {total}")
    return total


def load_city_hospital_counts(engine):
    print("\n[load_database] (3/9) Loading urbanpulse.city_hospital_counts ...")
    path = os.path.join(PROCESSED_DIR, "city_hospital_counts.csv")
    df = _read_csv_safe(path, "city_hospital_counts")

    if "city" in df.columns and "city_name" not in df.columns:
        df = df.rename(columns={"city": "city_name"})

    valid_columns = [
        "city_name", "total_facilities", "total_beds", "has_bed_data",
        "public_count", "private_count", "data_source", "data_confidence",
    ]
    df = df[[c for c in valid_columns if c in df.columns]]

    inserted = upsert_dataframe(engine, df, "city_hospital_counts", conflict_column="city_name")
    total = get_row_count(engine, "city_hospital_counts")
    print(f"  Source rows: {len(df)} | Newly inserted: {inserted} | Table total: {total}")
    return total


def load_monthly_city_metrics(engine):
    print("\n[load_database] (4/9) Loading urbanpulse.monthly_city_metrics ...")
    path = os.path.join(SYNTHETIC_DIR, "monthly_city_metrics.csv")
    df = _read_csv_safe(path, "monthly_city_metrics")

    # Convert 0/1 flags to boolean
    if "disease_outbreak_flag" in df.columns:
        df["disease_outbreak_flag"] = df["disease_outbreak_flag"].apply(
            lambda x: bool(x) if x is not None else None
        )

    inserted = upsert_dataframe(engine, df, "monthly_city_metrics", conflict_column="record_id")
    total = get_row_count(engine, "monthly_city_metrics")
    print(f"  Source rows: {len(df)} | Newly inserted: {inserted} | Table total: {total}")
    return total


def load_user_profiles(engine):
    print("\n[load_database] (5/9) Loading urbanpulse.user_profiles ...")
    path = os.path.join(SYNTHETIC_DIR, "user_profiles.csv")
    df = _read_csv_safe(path, "user_profiles")

    inserted = upsert_dataframe(engine, df, "user_profiles", conflict_column="user_id")
    total = get_row_count(engine, "user_profiles")
    print(f"  Source rows: {len(df)} | Newly inserted: {inserted} | Table total: {total}")
    return total


def load_relocation_queries(engine):
    print("\n[load_database] (6/9) Loading urbanpulse.relocation_queries ...")
    path = os.path.join(SYNTHETIC_DIR, "relocation_queries.csv")
    df = _read_csv_safe(path, "relocation_queries")

    inserted = upsert_dataframe(engine, df, "relocation_queries", conflict_column="query_id")
    total = get_row_count(engine, "relocation_queries")
    print(f"  Source rows: {len(df)} | Newly inserted: {inserted} | Table total: {total}")
    return total


def confirm_empty_tables(engine):
    """
    city_scores, recommendations, salary_equivalence are intentionally
    left empty here — they are populated at runtime by the scoring engine,
    ML inference, and the API respectively. Just confirm they exist and
    report current row counts (should be 0 on a fresh DB).
    """
    print("\n[load_database] (7-9/9) Confirming computed tables exist (left empty by design) ...")
    for table_name in ["city_scores", "recommendations", "salary_equivalence"]:
        total = get_row_count(engine, table_name)
        print(f"  urbanpulse.{table_name}: {total} rows (populated later by scoring/ML/API)")


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("LOAD DATABASE — UrbanPulse")
    print("=" * 70)

    engine = get_engine()
    verify_schema_exists(engine)

    results = {}
    results["cities"] = load_cities(engine)
    results["city_health_summary"] = load_city_health_summary(engine)
    results["city_hospital_counts"] = load_city_hospital_counts(engine)
    results["monthly_city_metrics"] = load_monthly_city_metrics(engine)
    results["user_profiles"] = load_user_profiles(engine)
    results["relocation_queries"] = load_relocation_queries(engine)
    confirm_empty_tables(engine)

    print("\n" + "=" * 70)
    print("LOAD SUMMARY")
    print("=" * 70)
    for table_name, count in results.items():
        print(f"  urbanpulse.{table_name:<28} : {count} rows")

    print("\n[load_database] Done. Run scripts/verify_db.py to validate the full load.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n[load_database] ERROR: {e}", file=sys.stderr)
        sys.exit(1)