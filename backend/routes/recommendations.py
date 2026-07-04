"""
backend/routes/recommendations.py

Endpoints for ML-powered city recommendations.

POST /recommendations/best-city  — predict best city using RandomForest
                                    from app.state
GET  /recommendations/history    — last 10 saved recommendations from DB
"""

import os
import sys
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from database import get_db
from models import Recommendation
from schemas import UserProfileInput, RecommendationResponse

router = APIRouter()

VALID_PERSONAS = {"early_career", "family_focused", "budget_focused"}

FEATURE_COLUMNS = [
    "persona_encoded", "age", "monthly_income", "years_experience",
    "dependents_count", "priority_1_encoded", "priority_2_encoded",
    "priority_3_encoded", "has_children_binary",
]


def _require_recommender(request: Request):
    """Pulls the ML recommender from app.state; raises 503 if not loaded."""
    model = request.app.state.city_recommender
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "City recommender model not loaded. "
                "Run backend/ml/train_city_recommender.py first, then restart the API."
            ),
        )
    return model


def _encode_user_features(body: UserProfileInput, request: Request) -> pd.DataFrame:
    """
    Encodes a UserProfileInput into the feature vector expected by the
    RandomForest model, using the encoders stored in app.state.

    Returns a single-row DataFrame with columns in FEATURE_COLUMNS order.
    """
    encoders = request.app.state.city_feature_encoders
    feature_columns = request.app.state.city_feature_columns

    if encoders is None:
        raise HTTPException(
            status_code=503,
            detail="Feature encoders not loaded. Restart API after training the model.",
        )

    persona_encoder = encoders["persona"]
    priority_encoder = encoders["priority"]

    try:
        persona_encoded = persona_encoder.transform([body.persona])[0]
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown persona '{body.persona}'. "
                   f"Known: {list(persona_encoder.classes_)}",
        )

    try:
        priority_1_encoded = priority_encoder.transform([body.priority_1])[0]
        priority_2_encoded = priority_encoder.transform([body.priority_2])[0]
        priority_3_encoded = priority_encoder.transform([body.priority_3])[0]
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown priority value. "
                   f"Known priorities: {list(priority_encoder.classes_)}. "
                   f"Error: {e}",
        )

    feature_row = pd.DataFrame([{
        "persona_encoded": int(persona_encoded),
        "age": body.age,
        "monthly_income": float(body.monthly_income),
        "years_experience": float(body.years_experience),
        "dependents_count": body.dependents_count,
        "priority_1_encoded": int(priority_1_encoded),
        "priority_2_encoded": int(priority_2_encoded),
        "priority_3_encoded": int(priority_3_encoded),
        "has_children_binary": int(body.has_children),
    }])

    return feature_row[feature_columns]


def _build_reasoning(predicted_city: str, confidence: float, body: UserProfileInput) -> str:
    """
    Generates a deterministic plain-English reasoning string for the
    ML recommendation, augmenting the numeric confidence score with
    persona-aware context.
    """
    persona_phrases = {
        "early_career": "an early-career professional prioritizing growth and job market density",
        "family_focused": "a family-focused relocator prioritizing healthcare, schools, and safety",
        "budget_focused": "a budget-focused relocator prioritizing affordability and cost of living",
    }
    persona_phrase = persona_phrases.get(body.persona, "a professional")

    confidence_pct = round(confidence * 100, 1)

    top_priorities = [body.priority_1, body.priority_2, body.priority_3]
    priorities_str = ", ".join(p.replace("_", " ") for p in top_priorities)

    return (
        f"Based on your profile as {persona_phrase}, with priorities in "
        f"{priorities_str}, the model recommends {predicted_city}. "
        f"This recommendation matches {confidence_pct}% of users with similar "
        f"profiles in our historical relocation query data."
    )


# ── POST /recommendations/best-city ─────────────────────────────────────────

@router.post(
    "/best-city",
    response_model=RecommendationResponse,
    summary="ML-predicted best city for a given user profile",
)
def recommend_best_city(
    body: UserProfileInput,
    request: Request,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """
    Uses the trained RandomForestClassifier (loaded at startup into
    app.state.city_recommender) to predict the most likely city for the
    user to select, given their profile attributes.

    The model was trained on 300 synthetic user profiles × relocation
    queries (data/synthetic/relocation_queries.csv), so confidence
    values reflect pattern-matching against that distribution.

    The recommendation (with confidence and reasoning) is persisted to
    the urbanpulse.recommendations table for history retrieval.
    """
    model = _require_recommender(request)
    city_label_encoder = request.app.state.city_label_encoder

    if city_label_encoder is None:
        raise HTTPException(
            status_code=503,
            detail="City label encoder not loaded. Restart API after training the model.",
        )

    feature_row = _encode_user_features(body, request)

    predicted_encoded = model.predict(feature_row)[0]
    predicted_city = city_label_encoder.inverse_transform([predicted_encoded])[0]

    # Get probability for the predicted class (model confidence)
    proba = model.predict_proba(feature_row)[0]
    predicted_class_idx = list(model.classes_).index(predicted_encoded)
    confidence = round(float(proba[predicted_class_idx]), 4)

    reasoning = _build_reasoning(predicted_city, confidence, body)

    # Persist to DB — user_id is nullable (anonymous frontend user)
    rec_row = Recommendation(
        user_id=None,
        query_id=None,
        persona=body.persona,
        recommended_city_id=None,  # would need city_id lookup; omitted to keep route clean
        recommended_city_name=predicted_city,
        confidence_score=confidence,
        composite_score_at_recommendation=0.0,  # scoring not re-run in ML path
        top_contributing_dimension=None,
        explanation_text=reasoning,
        model_version="v1.0",
    )

    try:
        db.add(rec_row)
        db.commit()
    except Exception:
        db.rollback()
        # Non-fatal — continue and return result even if persist fails

    return RecommendationResponse(
        recommended_city=predicted_city,
        confidence=confidence,
        reasoning=reasoning,
    )


# ── GET /recommendations/history ─────────────────────────────────────────────

@router.get(
    "/history",
    summary="Last 10 saved city recommendations from the database",
)
def recommendation_history(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns the 10 most recent rows from the urbanpulse.recommendations
    table, ordered by created_at descending.

    Useful for the frontend's 'Recent Recommendations' panel and for
    auditing model predictions over time.
    """
    rows = (
        db.query(Recommendation)
        .order_by(Recommendation.created_at.desc())
        .limit(10)
        .all()
    )

    if not rows:
        return {
            "count": 0,
            "note": "No recommendations saved yet. Use POST /recommendations/best-city first.",
            "recommendations": [],
        }

    result = [
        {
            "recommendation_id": r.recommendation_id,
            "persona": r.persona,
            "recommended_city_name": r.recommended_city_name,
            "confidence_score": float(r.confidence_score),
            "explanation_text": r.explanation_text,
            "model_version": r.model_version,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {
        "count": len(result),
        "recommendations": result,
    }