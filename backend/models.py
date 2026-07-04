"""
backend/models.py

SQLAlchemy ORM models for all 9 UrbanPulse tables, matching sql/schema.sql
column-for-column. All models target the 'urbanpulse' PostgreSQL schema.

Relationships:
  City.monthly_metrics      -> one-to-many -> MonthlyCityMetric
  City.scores                -> one-to-many -> CityScore
  UserProfile.queries          -> one-to-many -> RelocationQuery
  UserProfile.recommendations    -> one-to-many -> Recommendation
  UserProfile.salary_equivalences  -> one-to-many -> SalaryEquivalence
"""

from sqlalchemy import (
    Column, Integer, BigInteger, SmallInteger, String, Text,
    Numeric, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

SCHEMA = "urbanpulse"


# ── TABLE 1: cities ──────────────────────────────────────────────────────────

class City(Base):
    __tablename__ = "cities"
    __table_args__ = {"schema": SCHEMA}

    city_id = Column(Integer, primary_key=True)
    city_name = Column(String(50), nullable=False, unique=True)
    state = Column(String(50), nullable=False)
    region = Column(String(20), nullable=False)
    avg_monthly_rent_1bhk = Column(Numeric(10, 2), nullable=False)
    avg_monthly_rent_2bhk = Column(Numeric(10, 2), nullable=False)
    avg_salary_fresher = Column(Numeric(10, 2), nullable=False)
    avg_salary_3yr_exp = Column(Numeric(10, 2), nullable=False)
    cost_of_living_index = Column(Numeric(6, 2), nullable=False)
    pollution_aqi_avg = Column(Numeric(6, 2), nullable=False)
    green_space_index = Column(Numeric(6, 2), nullable=False)
    public_transport_score = Column(Numeric(6, 2), nullable=False)
    hospital_beds_per_lakh = Column(Numeric(8, 2), nullable=False)
    health_centres_per_lakh = Column(Numeric(8, 2), nullable=False)
    crude_death_rate = Column(Numeric(6, 3), nullable=False)
    school_quality_index = Column(Numeric(6, 2), nullable=False)
    crime_index = Column(Numeric(6, 2), nullable=False)
    tech_job_count_index = Column(Numeric(6, 2), nullable=False)
    startup_ecosystem_score = Column(Numeric(6, 2), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    monthly_metrics = relationship(
        "MonthlyCityMetric", back_populates="city", cascade="all, delete-orphan"
    )
    scores = relationship(
        "CityScore", back_populates="city", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<City(city_id={self.city_id}, city_name='{self.city_name}')>"


# ── TABLE 2: monthly_city_metrics ───────────────────────────────────────────

class MonthlyCityMetric(Base):
    __tablename__ = "monthly_city_metrics"
    __table_args__ = (
        UniqueConstraint("city_id", "year_month", name="uq_monthly_city_month"),
        {"schema": SCHEMA},
    )

    record_id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey(f"{SCHEMA}.cities.city_id"), nullable=False)
    city_name = Column(String(50), nullable=False)
    year_month = Column(String(7), nullable=False)  # 'YYYY-MM'
    avg_aqi = Column(Numeric(6, 2), nullable=False)
    avg_rent_1bhk = Column(Numeric(10, 2), nullable=False)
    avg_rent_2bhk = Column(Numeric(10, 2), nullable=False)
    job_postings_index = Column(Numeric(8, 2), nullable=False)
    avg_salary_offered = Column(Numeric(10, 2), nullable=False)
    cost_of_living_index = Column(Numeric(6, 2), nullable=False)
    hospital_utilization_rate = Column(Numeric(5, 2), nullable=False)
    disease_outbreak_flag = Column(Boolean, nullable=False, default=False)
    rainfall_mm = Column(Numeric(7, 2), nullable=False)
    temperature_avg = Column(Numeric(5, 2), nullable=False)

    city = relationship("City", back_populates="monthly_metrics")

    def __repr__(self):
        return f"<MonthlyCityMetric(city_name='{self.city_name}', year_month='{self.year_month}')>"


# ── TABLE 3: city_health_summary ────────────────────────────────────────────

class CityHealthSummary(Base):
    __tablename__ = "city_health_summary"
    __table_args__ = (
        UniqueConstraint("city_name", "year", name="uq_health_summary_city_year"),
        {"schema": SCHEMA},
    )

    bd_id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    total_births = Column(Integer)
    total_deaths = Column(Integer)
    births_male = Column(Integer)
    births_female = Column(Integer)
    deaths_male = Column(Integer)
    deaths_female = Column(Integer)
    deaths_others = Column(Integer)
    bbmp_total_births = Column(Integer)
    bbmp_total_deaths = Column(Integer)
    births_registered = Column(Integer)
    deaths_registered = Column(Integer)
    infant_mortality = Column(Integer)
    crude_death_rate = Column(Numeric(8, 5))
    crude_birth_rate_per_1000 = Column(Numeric(8, 3))
    crude_death_rate_per_1000 = Column(Numeric(8, 3))
    pop_estimate = Column(BigInteger)
    bbmp_birth_coverage_pct = Column(Numeric(6, 4))
    bbmp_death_coverage_pct = Column(Numeric(6, 4))
    registration_completeness_births = Column(Numeric(6, 4))
    registration_completeness_deaths = Column(Numeric(6, 4))
    male_death_share = Column(Numeric(6, 4))
    sex_ratio_births = Column(Numeric(7, 2))
    partial_year = Column(Boolean, nullable=False, default=False)
    data_source = Column(String(20), nullable=False, default="real")

    def __repr__(self):
        return f"<CityHealthSummary(city_name='{self.city_name}', year={self.year})>"


# ── TABLE 4: city_hospital_counts ───────────────────────────────────────────

class CityHospitalCount(Base):
    __tablename__ = "city_hospital_counts"
    __table_args__ = {"schema": SCHEMA}

    hospital_count_id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String(50), nullable=False, unique=True)
    total_facilities = Column(Integer, nullable=False)
    total_beds = Column(Integer, nullable=False)
    has_bed_data = Column(Boolean, nullable=False, default=False)
    public_count = Column(Integer, nullable=False)
    private_count = Column(Integer, nullable=False)
    data_source = Column(String(20), nullable=False, default="real")
    data_confidence = Column(Numeric(3, 2), nullable=False, default=1.00)

    def __repr__(self):
        return f"<CityHospitalCount(city_name='{self.city_name}', total_facilities={self.total_facilities})>"


# ── TABLE 5: user_profiles ──────────────────────────────────────────────────

class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {"schema": SCHEMA}

    user_id = Column(Integer, primary_key=True)
    age = Column(Integer, nullable=False)
    current_city = Column(String(50), nullable=False)
    target_cities = Column(String(300), nullable=False)  # pipe-delimited
    persona = Column(String(20), nullable=False)
    monthly_income = Column(Numeric(10, 2), nullable=False)
    dependents_count = Column(Integer, nullable=False, default=0)
    priority_1 = Column(String(30))
    priority_2 = Column(String(30))
    priority_3 = Column(String(30))
    has_children = Column(Boolean, nullable=False, default=False)
    years_experience = Column(Numeric(4, 1), nullable=False, default=0)

    queries = relationship(
        "RelocationQuery", back_populates="user", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "Recommendation", back_populates="user", cascade="all, delete-orphan"
    )
    salary_equivalences = relationship(
        "SalaryEquivalence", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, persona='{self.persona}')>"


# ── TABLE 6: relocation_queries ─────────────────────────────────────────────

class RelocationQuery(Base):
    __tablename__ = "relocation_queries"
    __table_args__ = {"schema": SCHEMA}

    query_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_profiles.user_id"), nullable=False)
    compared_cities = Column(String(300), nullable=False)  # pipe-delimited
    persona = Column(String(20), nullable=False)
    selected_city = Column(String(50), nullable=False)
    query_date = Column(TIMESTAMP(timezone=True), nullable=False)

    user = relationship("UserProfile", back_populates="queries")
    recommendations = relationship(
        "Recommendation", back_populates="query", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<RelocationQuery(query_id={self.query_id}, selected_city='{self.selected_city}')>"


# ── TABLE 7: city_scores ─────────────────────────────────────────────────────

class CityScore(Base):
    __tablename__ = "city_scores"
    __table_args__ = (
        UniqueConstraint(
            "city_id", "persona", "score_version",
            name="uq_city_scores_city_persona_version",
        ),
        {"schema": SCHEMA},
    )

    score_id = Column(Integer, primary_key=True, autoincrement=True)
    city_id = Column(Integer, ForeignKey(f"{SCHEMA}.cities.city_id"), nullable=False)
    city_name = Column(String(50), nullable=False)
    persona = Column(String(20), nullable=False)
    composite_score = Column(Numeric(5, 2), nullable=False)
    affordability_score = Column(Numeric(5, 2), nullable=False)
    healthcare_score = Column(Numeric(5, 2), nullable=False)
    livability_score = Column(Numeric(5, 2), nullable=False)
    job_market_score = Column(Numeric(5, 2), nullable=False)
    infrastructure_score = Column(Numeric(5, 2), nullable=False)
    growth_score = Column(Numeric(5, 2), nullable=False)
    composite_rank = Column(SmallInteger)
    score_version = Column(String(10), nullable=False, default="v1.0")
    computed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    city = relationship("City", back_populates="scores")

    def __repr__(self):
        return f"<CityScore(city_name='{self.city_name}', persona='{self.persona}', composite_score={self.composite_score})>"


# ── TABLE 8: recommendations ─────────────────────────────────────────────────

class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = {"schema": SCHEMA}

    recommendation_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_profiles.user_id"), nullable=True)
    query_id = Column(Integer, ForeignKey(f"{SCHEMA}.relocation_queries.query_id"), nullable=True)
    persona = Column(String(20), nullable=False)
    recommended_city_id = Column(Integer, ForeignKey(f"{SCHEMA}.cities.city_id"), nullable=False)
    recommended_city_name = Column(String(50), nullable=False)
    confidence_score = Column(Numeric(5, 4), nullable=False)
    composite_score_at_recommendation = Column(Numeric(5, 2), nullable=False)
    top_contributing_dimension = Column(String(30))
    explanation_text = Column(Text)
    model_version = Column(String(10), nullable=False, default="v1.0")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("UserProfile", back_populates="recommendations")
    query = relationship("RelocationQuery", back_populates="recommendations")

    def __repr__(self):
        return f"<Recommendation(recommended_city_name='{self.recommended_city_name}', confidence_score={self.confidence_score})>"


# ── TABLE 9: salary_equivalence ──────────────────────────────────────────────

class SalaryEquivalence(Base):
    __tablename__ = "salary_equivalence"
    __table_args__ = (
        CheckConstraint("source_city_id <> target_city_id", name="chk_salary_equiv_diff_cities"),
        {"schema": SCHEMA},
    )

    equivalence_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(f"{SCHEMA}.user_profiles.user_id"), nullable=True)
    source_city_id = Column(Integer, ForeignKey(f"{SCHEMA}.cities.city_id"), nullable=False)
    source_city_name = Column(String(50), nullable=False)
    target_city_id = Column(Integer, ForeignKey(f"{SCHEMA}.cities.city_id"), nullable=False)
    target_city_name = Column(String(50), nullable=False)
    current_salary = Column(Numeric(12, 2), nullable=False)
    required_salary = Column(Numeric(12, 2), nullable=False)
    col_adjustment_factor = Column(Numeric(6, 4), nullable=False)
    confidence_interval_low = Column(Numeric(12, 2))
    confidence_interval_high = Column(Numeric(12, 2))
    model_version = Column(String(10), nullable=False, default="v1.0")
    computed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("UserProfile", back_populates="salary_equivalences")

    def __repr__(self):
        return (
            f"<SalaryEquivalence(source_city_name='{self.source_city_name}', "
            f"target_city_name='{self.target_city_name}', required_salary={self.required_salary})>"
        )