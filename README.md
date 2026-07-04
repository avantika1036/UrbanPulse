<div align="center">

# 🏙️ UrbanPulse

### City Comparison & Relocation Intelligence for Indian Professionals

*Because a ₹20 LPA offer in Mumbai and ₹20 LPA in Pune are not the same thing.*

---

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Gemini](https://img.shields.io/badge/Gemini-1.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)

</div>

---

## What Is This?

UrbanPulse is a full-stack data platform that helps Indian professionals make smarter city relocation decisions. Instead of comparing raw salary numbers, it scores cities across **7 weighted dimensions** — affordability, healthcare, environment, career growth, income vs cost of living, family fit, and overall lifestyle — adjusted for your specific life stage and priorities.

It uses **real government data** from BBMP, BMC, GCC, PMC, and the Delhi State Health Department for healthcare metrics, combined with realistic synthetic data for cost of living trends, job market signals, and user profiles. Where data is real, it says so. Where it is estimated, that is labelled clearly too.

---

## Key Features

| Feature | Description |
|---|---|
| 🎯 **Persona-Driven Scoring** | Weights shift based on who you are — early career, family-focused, or budget-first |
| 💰 **Salary Equivalence** | See what you need to earn in City B to match your lifestyle in City A |
| 🤖 **ML Recommendation** | RandomForest model predicts your best-fit city from your profile |
| 🧠 **AI Narrative** | Google Gemini writes a plain-English explanation of the recommendation |
| 📊 **Real Health Data** | Actual hospital records and birth/death statistics from 5 cities |
| 📈 **Trend Charts** | 24 months of AQI, rent, salary, and hospital utilization data |
| 📋 **PDF Reports** | Downloadable 7-section comparison report with scores and AI analysis |
| 📤 **Tableau Exports** | 6 analytics-ready CSVs + auto-generated data insights |

---

## Cities Covered

| City | Real Health Data | Real Hospital Data |
|---|---|---|
| 🔴 Mumbai | ⚠️ Synthetic (Estimated) | ✅ Yes (288 BMC hospitals with bed counts) |
| 🔵 Bengaluru | ✅ Yes (2001–2024 BBMP) | ✅ Yes (32 BBMP health centres) |
| 🟢 Chennai | ✅ Yes (2018–2025 GCC) | ✅ Yes (16 UCHCs) |
| 🟡 Pune | ✅ Yes (1975–2018 PMC) | ⚠️ Synthetic (Estimated) |
| 🟠 Delhi | ✅ Yes (2017–2024 State Health Dept) | ⚠️ Synthetic (Estimated) |
| ⬛ Hyderabad | ⚠️ Synthetic (Estimated) | ⚠️ Synthetic (Estimated) |

---

## How Scoring Works

Each city is scored 0–100 on 6 dimensions. The composite score is a weighted average where the weights depend on your persona.

```text
Dimension              Early Career    Family      Budget
─────────────────────────────────────────────────────────
Income vs Cost of Living    30%          10%         25%
Affordability               20%          20%         35%
Healthcare                  10%          25%         10%
Environment & Pollution     10%          15%         20%
Career Growth               25%           0%          5%
Family Fit                   5%          30%          5%
─────────────────────────────────────────────────────────
Total                      100%         100%        100%
```

All scores are normalised relative to the cities you are comparing — not against a fixed global scale.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  REAL DATA (8 government CSVs)  +  SYNTHETIC DATA (seed=42) │
└────────────────────────┬────────────────────────────────────┘
                         │
              ETL Scripts (load_real_data.py
              parse_pune_kra.py + generate_synthetic_data.py)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL  (9 tables, ~61k rows)              │
└───────────────┬─────────────────────────┬───────────────────┘
                │                         │
         scoring.py                  ML Training
         (7 dimensions,          RandomForest → city_recommender.pkl
          3 personas)            GBR → salary_equivalence.pkl
                │                         │
                └──────────┬──────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend  (port 8000)                   │
│    /cities  /compare  /analytics  /recommendations  /narrate│
│              + Gemini 1.5-flash narrative layer             │
└──────────────────┬──────────────────────┬───────────────────┘
                   │                      │
            React Frontend          Exports & Reports
            (port 5173)        Tableau CSVs · PDF · Insights
```

---

## Project Structure

```text
UrbanPulse/
│
├── 📁 data/
│   ├── real/               ← 8 government CSVs (committed to git)
│   ├── synthetic/          ← generated data (reproducible, seed=42)
│   ├── processed/          ← cleaned ETL outputs
│   └── exports/            ← Tableau CSVs + auto_insights.txt
│
├── 📁 sql/
│   └── schema.sql          ← creates all 9 PostgreSQL tables
│
├── 📁 scripts/
│   ├── load_real_data.py       ← cleans and processes government CSVs
│   ├── parse_pune_kra.py       ← parses Pune KRA disease report
│   ├── generate_synthetic_data.py  ← generates all synthetic data
│   ├── load_database.py        ← loads everything into PostgreSQL
│   ├── verify_db.py            ← checks all tables have correct rows
│   ├── export_tableau_files.py ← generates 6 analytics export CSVs
│   └── create_insights.py      ← generates 10 data-driven insights
│
├── 📁 backend/
│   ├── main.py             ← FastAPI app entry point
│   ├── database.py         ← SQLAlchemy engine + session
│   ├── models.py           ← ORM models for all 9 tables
│   ├── schemas.py          ← Pydantic request/response schemas
│   ├── scoring.py          ← core scoring engine (pandas only)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routes/
│   │   ├── cities.py           ← GET /cities/*
│   │   ├── compare.py          ← POST /compare/*
│   │   ├── analytics.py        ← GET /analytics/*
│   │   ├── recommendations.py  ← POST /recommendations/*
│   │   └── narrate.py          ← POST /narrate/*
│   ├── ml/
│   │   ├── train_city_recommender.py
│   │   ├── train_salary_equivalence_model.py
│   │   └── feature_importance.py
│   └── genai/
│       └── gemini_narrator.py  ← Gemini integration with caching + fallback
│
├── 📁 models/              ← trained .pkl files (committed to git)
│   ├── city_recommender.pkl
│   ├── city_label_encoder.pkl
│   └── salary_equivalence.pkl
│
├── 📁 frontend/
│   ├── src/
│   │   ├── pages/          ← HeroPage, ComparePage, AnalyticsPage, HealthDataPage
│   │   ├── components/     ← ScoreCard, TrendChart, NarrativeBox, CompareForm...
│   │   ├── api/client.js   ← all API calls in one place
│   │   └── styles/theme.js ← central design tokens
│   ├── package.json
│   └── vite.config.js
│
├── 📁 reports/
│   ├── generate_pdf_report.py  ← 7-section branded PDF generator
│   └── output/                 ← generated PDFs land here
│
└── 📁 docs/
    └── EXECUTION_ORDER.md  ← detailed step-by-step run guide
```

---

## Running the Project

Follow these steps to run the project.

### 1. Configure Python Environment

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 2. Configure Database

Ensure PostgreSQL is running locally, then create the database and tables:

```bash
createdb -U postgres urbanpulse
psql -U postgres -d urbanpulse -f sql/schema.sql
```

### 3. Setup Environment Variables

Copy the example configuration file:

```bash
cp .env.example .env
```
Edit `.env` and insert your PostgreSQL password (`DATABASE_URL`). Add a Gemini API key if you wish to use the AI narrative feature.

### 4. Load Data

The synthetic data and ML models are pre-generated. Simply load the data into your local database:

```bash
# Ensure DATABASE_URL is exported in your terminal session, e.g.:
# export DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/urbanpulse"

python scripts/load_database.py
```

### 5. Start the Application

You need two terminal sessions.

**Terminal 1 — Backend API**
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm install
npm run dev
```

The web app is now accessible at `http://localhost:5173`.

---

## API Endpoints

Full interactive docs at `http://localhost:8000/docs`

| Method | Endpoint | What It Does |
|---|---|---|
| GET | `/` | Health check |
| GET | `/cities/` | All 6 cities with key stats |
| GET | `/cities/{name}` | Full city profile + scores for all 3 personas |
| GET | `/cities/{name}/monthly-trends` | 12 months of AQI, rent, salary data |
| GET | `/cities/{name}/health` | Real births/deaths + hospital counts |
| POST | `/compare/` | Compare 2–3 cities and get full score breakdown |
| POST | `/compare/salary-equivalence` | Salary equivalence calculator |
| GET | `/analytics/overview` | All cities ranked across all personas |
| GET | `/analytics/persona-rankings/{persona}` | Rankings for one persona |
| POST | `/recommendations/best-city` | ML-predicted best city for your profile |
| POST | `/narrate/relocation` | Gemini AI narrative for a comparison |

---

## Troubleshooting

- **`(venv)` not showing in terminal:** Run `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux).
- **`ModuleNotFoundError`:** Navigate to the `UrbanPulse/` root and activate the venv.
- **Password authentication failed for PostgreSQL:** Use individual variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`) in your `.env` instead of `DATABASE_URL` if your password contains special characters.
- **Port 8000 already in use:** Kill the existing process (`lsof -ti:8000 | xargs kill -9` on Mac/Linux).

---

## A Few Honest Notes

- **Hyderabad** has no real government data in this project. Every Hyderabad metric is a synthetic estimate. This is flagged with a `~` in the UI and labelled clearly on the health data page.
- **Bengaluru hospitals** — the BBMP source file has `beds = 0` for all facilities. Bed counts are not published. That figure is estimated and the confidence rating reflects it.
- **Pune 2018** data only covers January to April. It is loaded with a `partial_year` flag and excluded from rate calculations.
- **Scores are relative.** A city scored in a 2-city comparison will get different numbers than in a 6-city comparison. Both are correct for their context.

---

## License

MIT