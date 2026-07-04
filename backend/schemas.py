"""
backend/schemas.py

Pydantic v2 models for UrbanPulse FastAPI request/response validation.

Input schemas validate incoming request bodies for the API routes.
Output schemas define the shape of data returned to the frontend.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

VALID_PERSONAS = {"early_career", "family_focused", "budget_focused"}


# ══════════════════════════════════════════════════════════════════════════
# INPUT SCHEMAS
# ══════════════════════════════════════════════════════════════════════════

class CityCompareRequest(BaseModel):
    """
    Request body for POST /compare/ — compares 2-3 cities for a given
    persona and user financial profile, returning the full scoring
    breakdown and recommendation.
    """
    cities: list[str] = Field(
        ...,
        min_length=2,
        max_length=3,
        description="List of 2-3 city names to compare (e.g. ['Bengaluru', 'Pune']).",
    )
    persona: str = Field(
        ...,
        description="One of: early_career, family_focused, budget_focused",
    )
    user_monthly_income: float = Field(
        ...,
        gt=0,
        description="User's current monthly income in INR.",
    )
    years_experience: int = Field(
        ...,
        ge=0,
        le=50,
        description="User's years of professional experience.",
    )
    has_children: bool = Field(
        default=False,
        description="Whether the user has children (applies family_fit_score modifier).",
    )

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, v):
        if v not in VALID_PERSONAS:
            raise ValueError(f"persona must be one of {sorted(VALID_PERSONAS)}, got '{v}'")
        return v

    @field_validator("cities")
    @classmethod
    def validate_unique_cities(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("cities list must not contain duplicates")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "cities": ["Bengaluru", "Pune", "Hyderabad"],
                "persona": "early_career",
                "user_monthly_income": 65000,
                "years_experience": 3,
                "has_children": False,
            }
        }
    }


class UserProfileInput(BaseModel):
    """
    Request body for creating/submitting a user profile (e.g. when a
    user fills out the onboarding form on the frontend before getting
    a recommendation).
    """
    age: int = Field(..., ge=18, le=80)
    current_city: str = Field(..., min_length=1)
    target_cities: list[str] = Field(
        ...,
        min_length=1,
        description="Cities the user is considering relocating to.",
    )
    persona: str
    monthly_income: float = Field(..., gt=0)
    dependents_count: int = Field(default=0, ge=0, le=10)
    priority_1: str
    priority_2: str
    priority_3: str
    has_children: bool = Field(default=False)
    years_experience: float = Field(..., ge=0, le=50)

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, v):
        if v not in VALID_PERSONAS:
            raise ValueError(f"persona must be one of {sorted(VALID_PERSONAS)}, got '{v}'")
        return v

    @field_validator("priority_1", "priority_2", "priority_3")
    @classmethod
    def validate_priorities_nonempty(cls, v):
        if not v or not v.strip():
            raise ValueError("priority values must not be empty")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "age": 27,
                "current_city": "Mumbai",
                "target_cities": ["Pune", "Bengaluru"],
                "persona": "early_career",
                "monthly_income": 70000,
                "dependents_count": 0,
                "priority_1": "job_market",
                "priority_2": "affordability",
                "priority_3": "livability",
                "has_children": False,
                "years_experience": 4.5,
            }
        }
    }


class NarrateRequest(BaseModel):
    """
    Request body for POST /narrate/ — generates a Gemini-powered plain-
    English narrative explanation for a city recommendation, using the
    same inputs the scoring engine and recommender already computed.
    """
    persona: str
    best_city: str = Field(..., description="The top-recommended city name.")
    monthly_income: float = Field(..., gt=0)
    cities_compared: list[str] = Field(..., min_length=2)
    composite_score: float = Field(..., ge=0, le=100)
    top_positive_dimension: str = Field(
        ..., description="Human-readable label, e.g. 'Career Growth'"
    )
    top_positive_score: float = Field(..., ge=0, le=100)
    top_negative_dimension: str = Field(
        ..., description="Human-readable label, e.g. 'Affordability'"
    )
    top_negative_score: float = Field(..., ge=0, le=100)
    has_children: bool = Field(default=False)
    required_salary_equivalent: Optional[float] = Field(
        default=None,
        description="Optional: salary equivalence figure to weave into the narrative, if available.",
    )

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, v):
        if v not in VALID_PERSONAS:
            raise ValueError(f"persona must be one of {sorted(VALID_PERSONAS)}, got '{v}'")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "persona": "family_focused",
                "best_city": "Pune",
                "monthly_income": 180000,
                "cities_compared": ["Pune", "Chennai", "Mumbai"],
                "composite_score": 78.4,
                "top_positive_dimension": "Family Fit",
                "top_positive_score": 84.2,
                "top_negative_dimension": "Career Growth",
                "top_negative_score": 41.7,
                "has_children": True,
                "required_salary_equivalent": 245000,
            }
        }
    }


class SalaryEquivalenceRequest(BaseModel):
    """
    Request body for POST /recommendations/salary — computes the salary
    required in target_city for equivalent purchasing power to
    current_salary in source_city.
    """
    source_city: str
    target_city: str
    current_salary: float = Field(..., gt=0)
    persona: str

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, v):
        if v not in VALID_PERSONAS:
            raise ValueError(f"persona must be one of {sorted(VALID_PERSONAS)}, got '{v}'")
        return v

    @field_validator("target_city")
    @classmethod
    def validate_cities_differ(cls, v, info):
        source = info.data.get("source_city")
        if source is not None and v == source:
            raise ValueError("target_city must be different from source_city")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_city": "Mumbai",
                "target_city": "Pune",
                "current_salary": 150000,
                "persona": "family_focused",
            }
        }
    }


# ══════════════════════════════════════════════════════════════════════════
# OUTPUT SCHEMAS
# ══════════════════════════════════════════════════════════════════════════

class CityScoreDetail(BaseModel):
    """A single city's full score breakdown, as returned by the scoring engine."""
    city_name: str
    income_score: float
    affordability_score: float
    healthcare_score: float
    environment_score: float
    career_growth_score: float
    family_fit_score: float
    adjusted_life_score: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "city_name": "Bengaluru",
                "income_score": 72.5,
                "affordability_score": 58.3,
                "healthcare_score": 64.1,
                "environment_score": 70.8,
                "career_growth_score": 91.2,
                "family_fit_score": 66.0,
                "adjusted_life_score": 74.6,
            }
        }
    }


class DimensionDriver(BaseModel):
    """A single named score dimension and its value, used for top_positive/top_negative drivers."""
    dimension: str
    score: float


class ComparisonTableResponse(BaseModel):
    """
    Response body for POST /compare/ — the full structured comparison
    output, mirroring backend/scoring.py's get_comparison_table().
    """
    persona: str
    has_children: bool
    cities_compared: list[str]
    best_city: str
    scores: list[CityScoreDetail]
    recommendation_text: str
    top_positive: DimensionDriver
    top_negative: DimensionDriver

    model_config = {
        "json_schema_extra": {
            "example": {
                "persona": "early_career",
                "has_children": False,
                "cities_compared": ["Bengaluru", "Pune", "Hyderabad"],
                "best_city": "Bengaluru",
                "scores": [
                    {
                        "city_name": "Bengaluru",
                        "income_score": 72.5,
                        "affordability_score": 58.3,
                        "healthcare_score": 64.1,
                        "environment_score": 70.8,
                        "career_growth_score": 91.2,
                        "family_fit_score": 66.0,
                        "adjusted_life_score": 74.6,
                    }
                ],
                "recommendation_text": (
                    "For an early-career professional, Bengaluru is the top match, "
                    "driven primarily by strong Career Growth (91/100). The main "
                    "trade-off to weigh is its relatively weaker Affordability (58/100)."
                ),
                "top_positive": {"dimension": "Career Growth", "score": 91.2},
                "top_negative": {"dimension": "Affordability", "score": 58.3},
            }
        }
    }


class RecommendationResponse(BaseModel):
    """Response body for POST /recommendations/ — ML-predicted city recommendation."""
    recommended_city: str
    confidence: float = Field(..., ge=0, le=1, description="Model prediction confidence/probability, 0-1.")
    reasoning: str = Field(..., description="Plain-English explanation of the recommendation.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "recommended_city": "Hyderabad",
                "confidence": 0.78,
                "reasoning": (
                    "Based on your profile as an early-career professional prioritizing "
                    "job market and affordability, Hyderabad matches users with similar "
                    "characteristics 78% of the time in our historical query data."
                ),
            }
        }
    }


class SalaryEquivalenceResponse(BaseModel):
    """Response body for POST /recommendations/salary."""
    source_city: str
    target_city: str
    current_salary: float
    required_salary: float
    multiplier: float = Field(
        ..., description="required_salary / current_salary — how much more (or less) is needed."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_city": "Mumbai",
                "target_city": "Pune",
                "current_salary": 150000,
                "required_salary": 112500.0,
                "multiplier": 0.75,
            }
        }
    }


class NarrativeResponse(BaseModel):
    """Response body for POST /narrate/ — GenAI-generated narrative explanation."""
    narrative: str
    cached: bool = Field(
        default=False,
        description="True if this narrative was served from cache rather than freshly generated.",
    )
    model: str = Field(default="gemini-1.5-flash", description="The GenAI model used to generate this narrative.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "narrative": (
                    "For a family relocating with children, Pune stands out as the clear "
                    "choice. Its strong school quality and lower crime rate make it "
                    "especially well-suited to your priorities, even though career growth "
                    "opportunities are somewhat more limited than in Bengaluru or Mumbai. "
                    "At your current income of ₹1,80,000/month, you'd need approximately "
                    "₹2,45,000/month in Mumbai for equivalent purchasing power — Pune's "
                    "lower cost of living works strongly in your favor."
                ),
                "cached": False,
                "model": "gemini-1.5-flash",
            }
        }
    }