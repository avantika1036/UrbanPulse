"""
backend/ml/feature_importance.py

Loads both trained UrbanPulse ML models (city recommender and salary
equivalence) and extracts their feature importances. Prints a formatted
top-10 table for each and exports the combined results to
data/exports/feature_importances.csv.

Run: python backend/ml/feature_importance.py
Requires: models/city_recommender.pkl and models/salary_equivalence.pkl
  to already exist (run train_city_recommender.py and
  train_salary_equivalence_model.py first).
"""

import os
import sys
import pickle

import pandas as pd

# ── PATHS ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
EXPORTS_DIR = os.path.join(PROJECT_ROOT, "data", "exports")

CITY_RECOMMENDER_PATH = os.path.join(MODELS_DIR, "city_recommender.pkl")
SALARY_EQUIVALENCE_PATH = os.path.join(MODELS_DIR, "salary_equivalence.pkl")
OUTPUT_CSV_PATH = os.path.join(EXPORTS_DIR, "feature_importances.csv")

# Human-readable labels for raw feature column names
FEATURE_LABELS = {
    "persona_encoded": "Persona",
    "age": "Age",
    "monthly_income": "Monthly Income",
    "years_experience": "Years of Experience",
    "dependents_count": "Dependents Count",
    "priority_1_encoded": "Priority 1",
    "priority_2_encoded": "Priority 2",
    "priority_3_encoded": "Priority 3",
    "has_children_binary": "Has Children",
    "source_city_encoded": "Source City",
    "target_city_encoded": "Target City",
    "current_salary": "Current Salary",
    "cost_of_living_source": "Cost of Living (Source)",
    "cost_of_living_target": "Cost of Living (Target)",
}


def load_model_payload(path, model_label):
    """
    Loads a pickled model payload dict from disk.

    Args:
        path (str): path to the .pkl file.
        model_label (str): human-readable label for error messages.

    Returns:
        dict: the unpickled payload, expected to contain at least
            'model' and 'feature_columns' keys.

    Raises:
        FileNotFoundError: if the model file doesn't exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{model_label} model not found at {path}. "
            f"Train it first before running feature_importance.py."
        )

    with open(path, "rb") as f:
        payload = pickle.load(f)

    print(f"[feature_importance] Loaded {model_label} from {path}")
    return payload


def extract_feature_importances(payload, model_label):
    """
    Extracts feature importances from a model payload's underlying
    scikit-learn model (works for both RandomForestClassifier and
    GradientBoostingRegressor, since both expose .feature_importances_).

    Args:
        payload (dict): output of load_model_payload().
        model_label (str): human-readable label, included in output rows.

    Returns:
        pd.DataFrame: columns = model, feature, feature_label, importance,
            sorted descending by importance.
    """
    model = payload["model"]
    feature_columns = payload["feature_columns"]

    if not hasattr(model, "feature_importances_"):
        raise ValueError(
            f"{model_label} model of type {type(model).__name__} does not "
            f"expose feature_importances_. This function expects a "
            f"tree-based scikit-learn model (RandomForest / "
            f"GradientBoosting)."
        )

    importances = model.feature_importances_

    rows = []
    for feature_col, importance in zip(feature_columns, importances):
        rows.append({
            "model": model_label,
            "feature": feature_col,
            "feature_label": FEATURE_LABELS.get(feature_col, feature_col),
            "importance": round(float(importance), 6),
        })

    df = pd.DataFrame(rows).sort_values("importance", ascending=False).reset_index(drop=True)
    return df


def print_top_n_table(df, model_label, n=10):
    """
    Prints a formatted top-N feature importance table to stdout.

    Args:
        df (pd.DataFrame): output of extract_feature_importances().
        model_label (str): label for the table header.
        n (int): number of top features to display.
    """
    top_n = df.head(n)

    feature_w = max(len("Feature"), top_n["feature_label"].str.len().max()) + 2
    importance_w = max(len("Importance"), 12)
    rank_w = 6

    def sep_line():
        return "+" + "-" * rank_w + "+" + "-" * feature_w + "+" + "-" * importance_w + "+"

    print(f"\n{model_label} — Top {len(top_n)} Feature Importances")
    print(sep_line())
    print(f"|{'Rank'.center(rank_w)}|{'Feature'.center(feature_w)}|{'Importance'.center(importance_w)}|")
    print(sep_line())

    for idx, row in top_n.iterrows():
        rank = idx + 1
        print(
            f"|{str(rank).center(rank_w)}"
            f"|{row['feature_label'].center(feature_w)}"
            f"|{format(row['importance'], '.4f').center(importance_w)}|"
        )
        
    print(sep_line())


def main():
    print("=" * 70)
    print("FEATURE IMPORTANCE — UrbanPulse ML Models")
    print("=" * 70)

    os.makedirs(EXPORTS_DIR, exist_ok=True)

    all_importances = []

    # ── City Recommender ─────────────────────────────────────────────────
    try:
        recommender_payload = load_model_payload(CITY_RECOMMENDER_PATH, "City Recommender")
        recommender_importances = extract_feature_importances(recommender_payload, "City Recommender")
        print_top_n_table(recommender_importances, "City Recommender", n=10)
        all_importances.append(recommender_importances)
    except FileNotFoundError as e:
        print(f"\n[feature_importance] SKIPPED City Recommender: {e}")

    # ── Salary Equivalence Model ─────────────────────────────────────────
    try:
        salary_payload = load_model_payload(SALARY_EQUIVALENCE_PATH, "Salary Equivalence")
        salary_importances = extract_feature_importances(salary_payload, "Salary Equivalence")
        print_top_n_table(salary_importances, "Salary Equivalence", n=10)
        all_importances.append(salary_importances)
    except FileNotFoundError as e:
        print(f"\n[feature_importance] SKIPPED Salary Equivalence: {e}")

    if not all_importances:
        print(
            "\n[feature_importance] ERROR: No models could be loaded. "
            "Train at least one model before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Combined Export ──────────────────────────────────────────────────
    combined_df = pd.concat(all_importances, ignore_index=True)
    combined_df.to_csv(OUTPUT_CSV_PATH, index=False)

    print(f"\n[feature_importance] Saved combined feature importances -> {OUTPUT_CSV_PATH}")
    print(f"[feature_importance] Total rows exported: {len(combined_df)}")

    print("\n[feature_importance] Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[feature_importance] ERROR: {e}", file=sys.stderr)
        sys.exit(1)