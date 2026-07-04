-- ============================================================================
-- UrbanPulse — PostgreSQL Schema
-- ============================================================================
-- Defines all tables required by the UrbanPulse scoring, recommendation,
-- and salary-equivalence pipeline. All tables live under the urbanpulse
-- schema. Run this file once before any data loading script.
--
-- Run:  psql -U <user> -d <database> -f sql/schema.sql
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS urbanpulse;

SET search_path TO urbanpulse;

-- ============================================================================
-- TABLE 1: cities
-- ============================================================================
-- Purpose: Master dimension table — one row per city. Static reference data
--          covering cost of living, healthcare density, pollution, and
--          career/livability indices.
-- Source:  data/synthetic/city_master.csv
--          hospital_beds_per_lakh / health_centres_per_lakh are seeded from
--          REAL data (data/processed/city_hospital_counts.csv) for Bengaluru,
--          Mumbai, Chennai; manually estimated for Delhi, Pune, Hyderabad.
--          crude_death_rate is REAL for Bengaluru, Chennai, Delhi, Pune;
--          synthetic estimate for Mumbai, Hyderabad.
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.cities CASCADE;

CREATE TABLE urbanpulse.cities (
    city_id                     INTEGER PRIMARY KEY,
    city_name                   VARCHAR(50)     NOT NULL UNIQUE,
    state                       VARCHAR(50)     NOT NULL,
    region                      VARCHAR(20)     NOT NULL,
    avg_monthly_rent_1bhk       NUMERIC(10,2)   NOT NULL,
    avg_monthly_rent_2bhk       NUMERIC(10,2)   NOT NULL,
    avg_salary_fresher          NUMERIC(10,2)   NOT NULL,
    avg_salary_3yr_exp          NUMERIC(10,2)   NOT NULL,
    cost_of_living_index        NUMERIC(6,2)    NOT NULL,
    pollution_aqi_avg           NUMERIC(6,2)    NOT NULL,
    green_space_index           NUMERIC(6,2)    NOT NULL,
    public_transport_score      NUMERIC(6,2)    NOT NULL,
    hospital_beds_per_lakh      NUMERIC(8,2)    NOT NULL,
    health_centres_per_lakh     NUMERIC(8,2)    NOT NULL,
    crude_death_rate            NUMERIC(6,3)    NOT NULL,
    school_quality_index        NUMERIC(6,2)    NOT NULL,
    crime_index                 NUMERIC(6,2)    NOT NULL,
    tech_job_count_index        NUMERIC(6,2)    NOT NULL,
    startup_ecosystem_score     NUMERIC(6,2)    NOT NULL,
    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE urbanpulse.cities IS
    'Master dimension table for the 6 covered cities (Mumbai, Bengaluru, Chennai, Pune, Delhi, Hyderabad). Loaded from data/synthetic/city_master.csv. Healthcare density fields and crude_death_rate are seeded from real government data where available; see column comments for provenance.';

COMMENT ON COLUMN urbanpulse.cities.hospital_beds_per_lakh IS
    'REAL for Mumbai (full bed data) and Chennai (facility count, no bed data, estimated). Bengaluru beds are ESTIMATED — real source had beds=0 for all facilities. Delhi/Pune/Hyderabad fully estimated.';
COMMENT ON COLUMN urbanpulse.cities.health_centres_per_lakh IS
    'REAL for Bengaluru (32 BBMP facilities), Mumbai (288 facilities), Chennai (16 UCHCs). Estimated for Delhi, Pune, Hyderabad.';
COMMENT ON COLUMN urbanpulse.cities.crude_death_rate IS
    'REAL for Bengaluru, Chennai, Delhi, Pune (derived from data/processed/city_health_summary.csv). Synthetic estimate for Mumbai, Hyderabad.';

CREATE INDEX idx_cities_city_name ON urbanpulse.cities (city_name);


-- ============================================================================
-- TABLE 2: monthly_city_metrics
-- ============================================================================
-- Purpose: Time-series table — one row per city per month (Jan 2023–Dec 2024).
--          Drives trend charts, seasonal AQI/rainfall analysis, and ML
--          training features for the recommender.
-- Source:  data/synthetic/monthly_city_metrics.csv (fully synthetic, fixed
--          seed=42, with seasonal rules for AQI, rainfall, temperature)
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.monthly_city_metrics CASCADE;

CREATE TABLE urbanpulse.monthly_city_metrics (
    record_id                   INTEGER PRIMARY KEY,
    city_id                     INTEGER         NOT NULL REFERENCES urbanpulse.cities(city_id),
    city_name                   VARCHAR(50)     NOT NULL,
    year_month                  VARCHAR(7)      NOT NULL,   -- format: 'YYYY-MM'
    avg_aqi                     NUMERIC(6,2)    NOT NULL,
    avg_rent_1bhk                NUMERIC(10,2)   NOT NULL,
    avg_rent_2bhk                NUMERIC(10,2)   NOT NULL,
    job_postings_index          NUMERIC(8,2)    NOT NULL,
    avg_salary_offered          NUMERIC(10,2)   NOT NULL,
    cost_of_living_index        NUMERIC(6,2)    NOT NULL,
    hospital_utilization_rate   NUMERIC(5,2)    NOT NULL,
    disease_outbreak_flag       BOOLEAN         NOT NULL DEFAULT FALSE,
    rainfall_mm                 NUMERIC(7,2)    NOT NULL,
    temperature_avg             NUMERIC(5,2)    NOT NULL,
    CONSTRAINT uq_monthly_city_month UNIQUE (city_id, year_month)
);

COMMENT ON TABLE urbanpulse.monthly_city_metrics IS
    'Synthetic monthly time-series per city, Jan 2023 - Dec 2024 (24 months x 6 cities = 144 rows). Fully synthetic data, generated with seasonal rules (Delhi AQI winter spike, Mumbai/Chennai monsoon rainfall patterns, winter hospital utilization increase). Source: data/synthetic/monthly_city_metrics.csv.';

CREATE INDEX idx_monthly_metrics_city_name ON urbanpulse.monthly_city_metrics (city_name);
CREATE INDEX idx_monthly_metrics_year_month ON urbanpulse.monthly_city_metrics (year_month);
CREATE INDEX idx_monthly_metrics_city_id ON urbanpulse.monthly_city_metrics (city_id);


-- ============================================================================
-- TABLE 3: city_health_summary
-- ============================================================================
-- Purpose: REAL annual births/deaths data per city per year. Feeds the
--          healthcare_score crude death rate trend sub-component.
-- Source:  data/processed/city_health_summary.csv (output of
--          scripts/load_real_data.py). REAL for Bengaluru (2001-2024),
--          Chennai (2018-2025), Delhi (2017-2024), Pune (1975-2018).
--          No rows exist for Mumbai or Hyderabad (no real source data).
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.city_health_summary CASCADE;

CREATE TABLE urbanpulse.city_health_summary (
    bd_id                            SERIAL PRIMARY KEY,
    city_name                        VARCHAR(50)     NOT NULL,
    year                              INTEGER         NOT NULL,
    total_births                      INTEGER,
    total_deaths                      INTEGER,
    births_male                       INTEGER,
    births_female                     INTEGER,
    deaths_male                       INTEGER,
    deaths_female                     INTEGER,
    deaths_others                     INTEGER,
    bbmp_total_births                 INTEGER,
    bbmp_total_deaths                 INTEGER,
    births_registered                 INTEGER,
    deaths_registered                 INTEGER,
    infant_mortality                  INTEGER,
    crude_death_rate                  NUMERIC(8,5),    -- total_deaths / total_births
    crude_birth_rate_per_1000         NUMERIC(8,3),
    crude_death_rate_per_1000         NUMERIC(8,3),
    pop_estimate                      BIGINT,
    bbmp_birth_coverage_pct           NUMERIC(6,4),
    bbmp_death_coverage_pct           NUMERIC(6,4),
    registration_completeness_births  NUMERIC(6,4),
    registration_completeness_deaths  NUMERIC(6,4),
    male_death_share                  NUMERIC(6,4),
    sex_ratio_births                  NUMERIC(7,2),
    partial_year                      BOOLEAN         NOT NULL DEFAULT FALSE,
    data_source                       VARCHAR(20)     NOT NULL DEFAULT 'real',
    CONSTRAINT uq_health_summary_city_year UNIQUE (city_name, year)
);

COMMENT ON TABLE urbanpulse.city_health_summary IS
    'Real annual births/deaths statistics from government sources. Bengaluru, Chennai, Delhi, Pune are REAL government data; Mumbai and Hyderabad have NO rows here (synthetic crude_death_rate is stored directly in cities table instead). Source: data/processed/city_health_summary.csv, output of scripts/load_real_data.py.';

CREATE INDEX idx_health_summary_city_name ON urbanpulse.city_health_summary (city_name);
CREATE INDEX idx_health_summary_year ON urbanpulse.city_health_summary (year);


-- ============================================================================
-- TABLE 4: city_hospital_counts
-- ============================================================================
-- Purpose: REAL facility and bed counts per city, used to seed
--          hospital_beds_per_lakh / health_centres_per_lakh in the cities
--          table, and directly drives the bed-density and facility-density
--          sub-components of healthcare_score.
-- Source:  data/processed/city_hospital_counts.csv (output of
--          scripts/load_real_data.py). REAL for Bengaluru, Mumbai, Chennai.
--          No rows for Delhi, Pune, Hyderabad (no real hospital CSV exists).
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.city_hospital_counts CASCADE;

CREATE TABLE urbanpulse.city_hospital_counts (
    hospital_count_id     SERIAL PRIMARY KEY,
    city_name              VARCHAR(50)     NOT NULL UNIQUE,
    total_facilities       INTEGER         NOT NULL,
    total_beds              INTEGER         NOT NULL,
    has_bed_data            BOOLEAN         NOT NULL DEFAULT FALSE,
    public_count            INTEGER         NOT NULL,
    private_count           INTEGER         NOT NULL,
    data_source             VARCHAR(20)     NOT NULL DEFAULT 'real',
    data_confidence         NUMERIC(3,2)    NOT NULL DEFAULT 1.00
);

COMMENT ON TABLE urbanpulse.city_hospital_counts IS
    'Real hospital/health-facility counts and bed totals per city. Only Bengaluru, Mumbai, Chennai have rows — these are derived from real government CSVs (Bengaluru BBMP centres, Mumbai ward hospitals, Chennai UCHCs). data_confidence reflects known data quality gaps (e.g. Bengaluru beds=0 in source). Source: data/processed/city_hospital_counts.csv, output of scripts/load_real_data.py.';

CREATE INDEX idx_hospital_counts_city_name ON urbanpulse.city_hospital_counts (city_name);


-- ============================================================================
-- TABLE 5: user_profiles
-- ============================================================================
-- Purpose: Synthetic user records used to train the ML city recommender and
--          to generate relocation_queries.
-- Source:  data/synthetic/user_profiles.csv (fully synthetic, seed=42)
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.user_profiles CASCADE;

CREATE TABLE urbanpulse.user_profiles (
    user_id              INTEGER PRIMARY KEY,
    age                   INTEGER         NOT NULL,
    current_city          VARCHAR(50)     NOT NULL,
    target_cities         VARCHAR(300)    NOT NULL,   -- pipe-delimited list, e.g. 'Pune|Chennai'
    persona                VARCHAR(20)     NOT NULL,   -- early_career / family_focused / budget_focused
    monthly_income         NUMERIC(10,2)   NOT NULL,
    dependents_count        INTEGER         NOT NULL DEFAULT 0,
    priority_1              VARCHAR(30),
    priority_2              VARCHAR(30),
    priority_3              VARCHAR(30),
    has_children             BOOLEAN         NOT NULL DEFAULT FALSE,
    years_experience         NUMERIC(4,1)    NOT NULL DEFAULT 0
);

COMMENT ON TABLE urbanpulse.user_profiles IS
    'Synthetic user records (300 rows) used to train the ML city recommender model and generate relocation query/outcome data. Fully synthetic, generated with fixed seed=42. Source: data/synthetic/user_profiles.csv.';

CREATE INDEX idx_user_profiles_persona ON urbanpulse.user_profiles (persona);
CREATE INDEX idx_user_profiles_current_city ON urbanpulse.user_profiles (current_city);


-- ============================================================================
-- TABLE 6: relocation_queries
-- ============================================================================
-- Purpose: Synthetic query log — each row represents a user comparing
--          cities and (implicitly) choosing one. Used as ML training
--          signal for the city recommender.
-- Source:  data/synthetic/relocation_queries.csv (fully synthetic, seed=42)
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.relocation_queries CASCADE;

CREATE TABLE urbanpulse.relocation_queries (
    query_id              INTEGER PRIMARY KEY,
    user_id                INTEGER         NOT NULL REFERENCES urbanpulse.user_profiles(user_id),
    compared_cities         VARCHAR(300)    NOT NULL,   -- pipe-delimited list
    persona                  VARCHAR(20)     NOT NULL,
    selected_city             VARCHAR(50)     NOT NULL,
    query_date                TIMESTAMPTZ     NOT NULL
);

COMMENT ON TABLE urbanpulse.relocation_queries IS
    'Synthetic relocation comparison queries (300 rows, 1:1 with user_profiles). selected_city is correlated with persona (early_career -> Bengaluru/Hyderabad; family_focused -> Pune/Chennai; budget_focused -> Hyderabad/Pune), used as ML training labels. Source: data/synthetic/relocation_queries.csv.';

CREATE INDEX idx_relocation_queries_user_id ON urbanpulse.relocation_queries (user_id);
CREATE INDEX idx_relocation_queries_persona ON urbanpulse.relocation_queries (persona);


-- ============================================================================
-- TABLE 7: city_scores
-- ============================================================================
-- Purpose: Central output table of the scoring engine (backend/scoring.py).
--          One row per city per persona. Stores composite + all 6 dimension
--          scores. Read by every API endpoint.
-- Source:  Computed at runtime by backend/scoring.py — NOT loaded from CSV.
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.city_scores CASCADE;

CREATE TABLE urbanpulse.city_scores (
    score_id                  SERIAL PRIMARY KEY,
    city_id                    INTEGER         NOT NULL REFERENCES urbanpulse.cities(city_id),
    city_name                  VARCHAR(50)     NOT NULL,
    persona                     VARCHAR(20)     NOT NULL,   -- early_career / family_focused / budget_focused
    composite_score              NUMERIC(5,2)    NOT NULL,
    affordability_score          NUMERIC(5,2)    NOT NULL,
    healthcare_score              NUMERIC(5,2)    NOT NULL,
    livability_score               NUMERIC(5,2)    NOT NULL,
    job_market_score                NUMERIC(5,2)    NOT NULL,
    infrastructure_score             NUMERIC(5,2)    NOT NULL,
    growth_score                      NUMERIC(5,2)    NOT NULL,
    composite_rank                     SMALLINT,
    score_version                       VARCHAR(10)     NOT NULL DEFAULT 'v1.0',
    computed_at                          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_city_scores_city_persona_version UNIQUE (city_id, persona, score_version)
);

COMMENT ON TABLE urbanpulse.city_scores IS
    'Computed output of the scoring engine (backend/scoring.py). One row per city per persona per score_version (6 cities x 3 personas = 18 rows per version). All 6 dimension scores are normalized 0-100; composite_score is a persona-weighted average. NOT loaded from CSV — computed at runtime from cities, monthly_city_metrics, city_health_summary, city_hospital_counts.';

CREATE INDEX idx_city_scores_city_name ON urbanpulse.city_scores (city_name);
CREATE INDEX idx_city_scores_persona ON urbanpulse.city_scores (persona);


-- ============================================================================
-- TABLE 8: recommendations
-- ============================================================================
-- Purpose: Best city recommendation per user, with explanation text.
--          Output of the ML recommender (backend/ml/train_city_recommender.py)
--          and the GenAI narrator (backend/genai/gemini_narrator.py).
-- Source:  Computed at runtime — NOT loaded from CSV.
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.recommendations CASCADE;

CREATE TABLE urbanpulse.recommendations (
    recommendation_id        SERIAL PRIMARY KEY,
    user_id                    INTEGER         REFERENCES urbanpulse.user_profiles(user_id),
    query_id                    INTEGER         REFERENCES urbanpulse.relocation_queries(query_id),
    persona                       VARCHAR(20)     NOT NULL,
    recommended_city_id            INTEGER         NOT NULL REFERENCES urbanpulse.cities(city_id),
    recommended_city_name            VARCHAR(50)     NOT NULL,
    confidence_score                  NUMERIC(5,4)    NOT NULL,   -- ML model probability 0-1
    composite_score_at_recommendation  NUMERIC(5,2)    NOT NULL,
    top_contributing_dimension          VARCHAR(30),
    explanation_text                     TEXT,                     -- Gemini-generated narrative
    model_version                         VARCHAR(10)     NOT NULL DEFAULT 'v1.0',
    created_at                             TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE urbanpulse.recommendations IS
    'ML-generated city recommendations with GenAI narrative explanations. user_id/query_id are nullable to support both logged-in synthetic-user recommendations and ad-hoc anonymous API recommendation requests. NOT loaded from CSV — produced at runtime by backend/ml/train_city_recommender.py inference and backend/genai/gemini_narrator.py.';

CREATE INDEX idx_recommendations_user_id ON urbanpulse.recommendations (user_id);
CREATE INDEX idx_recommendations_persona ON urbanpulse.recommendations (persona);
CREATE INDEX idx_recommendations_recommended_city ON urbanpulse.recommendations (recommended_city_id);


-- ============================================================================
-- TABLE 9: salary_equivalence
-- ============================================================================
-- Purpose: Output of the salary equivalence calculator/ML model — given a
--          salary in a source city, what salary is required in a target
--          city for equivalent purchasing power.
-- Source:  Computed at runtime by backend/ml/train_salary_equivalence_model.py
--          inference — NOT loaded from CSV.
-- ============================================================================

DROP TABLE IF EXISTS urbanpulse.salary_equivalence CASCADE;

CREATE TABLE urbanpulse.salary_equivalence (
    equivalence_id            SERIAL PRIMARY KEY,
    user_id                     INTEGER         REFERENCES urbanpulse.user_profiles(user_id),
    source_city_id                INTEGER         NOT NULL REFERENCES urbanpulse.cities(city_id),
    source_city_name                VARCHAR(50)     NOT NULL,
    target_city_id                    INTEGER         NOT NULL REFERENCES urbanpulse.cities(city_id),
    target_city_name                    VARCHAR(50)     NOT NULL,
    current_salary                        NUMERIC(12,2)   NOT NULL,
    required_salary                         NUMERIC(12,2)   NOT NULL,
    col_adjustment_factor                     NUMERIC(6,4)    NOT NULL,
    confidence_interval_low                     NUMERIC(12,2),
    confidence_interval_high                      NUMERIC(12,2),
    model_version                                  VARCHAR(10)     NOT NULL DEFAULT 'v1.0',
    computed_at                                     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_salary_equiv_diff_cities CHECK (source_city_id <> target_city_id)
);

COMMENT ON TABLE urbanpulse.salary_equivalence IS
    'Salary equivalence calculations - given current_salary in source_city, required_salary is the equivalent purchasing-power salary in target_city. user_id nullable for anonymous calculator usage. NOT loaded from CSV - produced at runtime by backend/ml/train_salary_equivalence_model.py inference, exposed via the /recommendations/salary API endpoint.';

CREATE INDEX idx_salary_equivalence_user_id ON urbanpulse.salary_equivalence (user_id);
CREATE INDEX idx_salary_equivalence_source_city ON urbanpulse.salary_equivalence (source_city_id);
CREATE INDEX idx_salary_equivalence_target_city ON urbanpulse.salary_equivalence (target_city_id);


-- ============================================================================
-- RESET search_path
-- ============================================================================
RESET search_path;


-- ============================================================================
-- LOAD ORDER (see scripts/load_database.py for the actual loader)
-- ============================================================================
-- The tables must be populated in this exact order due to foreign key
-- dependencies:
--
--   1. urbanpulse.cities
--        <- data/synthetic/city_master.csv
--        (no dependencies; must be loaded first — every other table
--         references city_id either directly or via city_name lookup)
--
--   2. urbanpulse.city_health_summary
--        <- data/processed/city_health_summary.csv
--        (depends on cities existing for city_name validation, though FK
--         is not enforced on city_name directly — load after cities)
--
--   3. urbanpulse.city_hospital_counts
--        <- data/processed/city_hospital_counts.csv
--        (same as above — load after cities)
--
--   4. urbanpulse.monthly_city_metrics
--        <- data/synthetic/monthly_city_metrics.csv
--        (FK on cities.city_id — must load after cities)
--
--   5. urbanpulse.user_profiles
--        <- data/synthetic/user_profiles.csv
--        (no FK dependency on cities table itself — current_city/target_cities
--         are stored as VARCHAR, not FK — but load after cities for
--         referential sanity)
--
--   6. urbanpulse.relocation_queries
--        <- data/synthetic/relocation_queries.csv
--        (FK on user_profiles.user_id — must load after user_profiles)
--
--   7. urbanpulse.city_scores
--        <- COMPUTED by backend/scoring.py (reads cities, monthly_city_metrics,
--           city_health_summary, city_hospital_counts; writes back to DB)
--        (FK on cities.city_id — must load after cities, and logically
--         after monthly_city_metrics/city_health_summary/city_hospital_counts
--         since the scoring engine reads from them)
--
--   8. urbanpulse.recommendations
--        <- COMPUTED by backend/ml/train_city_recommender.py inference
--        (FK on user_profiles.user_id, relocation_queries.query_id,
--         cities.city_id — must load after all three)
--
--   9. urbanpulse.salary_equivalence
--        <- COMPUTED by backend/ml/train_salary_equivalence_model.py inference
--        (FK on user_profiles.user_id, cities.city_id — must load after both)
--
-- ============================================================================