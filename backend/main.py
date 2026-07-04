"""
backend/main.py

FastAPI application entry point for UrbanPulse API.

Startup lifecycle:
  1. Loads ML models (city_recommender.pkl, city_label_encoder.pkl,
     salary_equivalence.pkl) into app.state so route handlers can access
     them without reloading from disk on every request.
  2. Loads city_master.csv into app.state.city_df (a pandas DataFrame)
     for use by the scoring engine inside route handlers.

Run locally:
  cd backend
  uvicorn main:app --reload --port 8000

Or via Docker:
  docker build -t urbanpulse-api ./backend
  docker run -p 8000:8000 --env DATABASE_URL=... urbanpulse-api
"""

import os
import sys
import pickle
import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

# Add backend/ directory to path so siblings import cleanly
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

from routes import cities, compare, analytics, recommendations, narrate

app.include_router(cities.router,           prefix="/cities",          tags=["Cities"])
app.include_router(compare.router,          prefix="/compare",         tags=["Compare"])
app.include_router(analytics.router,        prefix="/analytics",       tags=["Analytics"])
app.include_router(recommendations.router,  prefix="/recommendations", tags=["Recommendations"])
app.include_router(narrate.router,          prefix="/narrate",         tags=["GenAI"])

# ── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("urbanpulse")

# ── MODEL / DATA PATHS ───────────────────────────────────────────────────────
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
SYNTHETIC_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")

CITY_RECOMMENDER_PATH = os.path.join(MODELS_DIR, "city_recommender.pkl")
CITY_LABEL_ENCODER_PATH = os.path.join(MODELS_DIR, "city_label_encoder.pkl")
SALARY_EQUIVALENCE_PATH = os.path.join(MODELS_DIR, "salary_equivalence.pkl")
CITY_MASTER_PATH = os.path.join(SYNTHETIC_DIR, "city_master.csv")


# ── LIFESPAN ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle handler.
    Loads all ML models and the city reference DataFrame once at startup
    into app.state, so route handlers can access them via request.app.state
    without disk I/O on every request.
    """
    logger.info("UrbanPulse API starting up...")

    # ── Load city_master.csv ─────────────────────────────────────────────
    if not os.path.exists(CITY_MASTER_PATH):
        logger.warning(
            f"city_master.csv not found at {CITY_MASTER_PATH}. "
            f"Run scripts/generate_synthetic_data.py first. "
            f"City-dependent endpoints will return 503 until this is resolved."
        )
        app.state.city_df = pd.DataFrame()
    else:
        app.state.city_df = pd.read_csv(CITY_MASTER_PATH, encoding="utf-8-sig")
        logger.info(f"Loaded city_master.csv: {len(app.state.city_df)} cities")

    # ── Load city recommender model ──────────────────────────────────────
    if not os.path.exists(CITY_RECOMMENDER_PATH):
        logger.warning(
            f"city_recommender.pkl not found at {CITY_RECOMMENDER_PATH}. "
            f"Run backend/ml/train_city_recommender.py first. "
            f"Recommendation endpoints will return 503 until trained."
        )
        app.state.city_recommender = None
        app.state.city_feature_encoders = None
        app.state.city_feature_columns = None
    else:
        with open(CITY_RECOMMENDER_PATH, "rb") as f:
            recommender_payload = pickle.load(f)
        app.state.city_recommender = recommender_payload["model"]
        app.state.city_feature_encoders = recommender_payload["feature_encoders"]
        app.state.city_feature_columns = recommender_payload["feature_columns"]
        logger.info("Loaded city_recommender.pkl")

    # ── Load city label encoder ──────────────────────────────────────────
    if not os.path.exists(CITY_LABEL_ENCODER_PATH):
        logger.warning(f"city_label_encoder.pkl not found at {CITY_LABEL_ENCODER_PATH}.")
        app.state.city_label_encoder = None
    else:
        with open(CITY_LABEL_ENCODER_PATH, "rb") as f:
            app.state.city_label_encoder = pickle.load(f)
        logger.info("Loaded city_label_encoder.pkl")

    # ── Load salary equivalence model ────────────────────────────────────
    if not os.path.exists(SALARY_EQUIVALENCE_PATH):
        logger.warning(
            f"salary_equivalence.pkl not found at {SALARY_EQUIVALENCE_PATH}. "
            f"Run backend/ml/train_salary_equivalence_model.py first."
        )
        app.state.salary_equivalence_model = None
        app.state.salary_feature_encoders = None
        app.state.salary_feature_columns = None
    else:
        with open(SALARY_EQUIVALENCE_PATH, "rb") as f:
            salary_payload = pickle.load(f)
        app.state.salary_equivalence_model = salary_payload["model"]
        app.state.salary_feature_encoders = salary_payload["feature_encoders"]
        app.state.salary_feature_columns = salary_payload["feature_columns"]
        logger.info("Loaded salary_equivalence.pkl")

    logger.info("UrbanPulse API startup complete.")

    yield

    logger.info("UrbanPulse API shutting down.")


# ── APP FACTORY ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="UrbanPulse API",
    description=(
        "Salary-adjusted city comparison and relocation intelligence platform "
        "for young Indian professionals. Covers Mumbai, Bengaluru, Chennai, "
        "Pune, Delhi, and Hyderabad across 7 scoring dimensions."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTERS ───────────────────────────────────────────────────────────────────

app.include_router(cities.router, prefix="/cities", tags=["Cities"])
app.include_router(compare.router, prefix="/compare", tags=["Compare"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(narrate.router, prefix="/narrate", tags=["GenAI"])

# ── HEALTH CHECK ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """
    Root health check endpoint. Returns API status and version.
    Used by Docker HEALTHCHECK, load balancers, and /docs landing.
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "api": "UrbanPulse API",
        "docs": "/docs",
    }