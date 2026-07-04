"""
backend/ml/train_salary_equivalence_model.py

Trains a GradientBoostingRegressor to predict the salary required in a
target city for equivalent purchasing power to a salary in a source city.

Training data is GENERATED (not loaded from a file) by calling
compute_salary_equivalence() from backend/scoring.py across every
ordered city pair and a range of salaries (₹30k - ₹300k monthly, step
₹10k), producing ~180 rows (6 cities x 5 other cities x 28 salary
steps x 3 personas would be far larger; per spec this targets ~180
rows, achieved via city-pair x salary-step combinations — see
generate_training_data() docstring for the exact grid).

Saves:
  models/salary_equivalence.pkl

Run: python backend/ml/train_salary_equivalence_model.py
"""

import os
import sys
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# ── PATHS ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
MODEL_OUTPUT_PATH = os.path.join(MODELS_DIR, "salary_equivalence.pkl")

sys.path.insert(0, BACKEND_DIR)
from scoring import compute_salary_equivalence, VALID_PERSONAS

RANDOM_STATE = 42

FEATURE_COLUMNS = [
    "source_city_encoded", "target_city_encoded", "current_salary",
    "cost_of_living_source", "cost_of_living_target", "persona_encoded",
]

# Same dummy city reference used by scoring.py's own __main__ demo block,
# kept consistent here so generated salary_equivalence training data
# matches what the live scoring engine would produce. In production this
# would be loaded from the urbanpulse.cities DB table instead.
CITY_DATA = {
    "city_name": ["Mumbai", "Bengaluru", "Chennai", "Pune", "Delhi", "Hyderabad"],
    "cost_of_living_index": [100.0, 85.0, 72.0, 75.0, 92.0, 68.0],
}


def _build_city_df():
    """Builds the city reference DataFrame needed by compute_salary_equivalence()."""
    return pd.DataFrame(CITY_DATA)


def generate_training_data():
    """
    Generates synthetic training data for the salary equivalence model
    by calling compute_salary_equivalence() from scoring.py across every
    ordered city pair (source != target), a range of monthly salaries
    from ₹30,000 to ₹300,000 in ₹10,000 steps (28 salary points), and
    each of the 3 personas (used as a feature, though
    compute_salary_equivalence() itself is persona-agnostic — persona
    is included as a feature here to let the model learn any latent
    persona-correlated salary patterns from the broader UrbanPulse
    dataset, and to satisfy the required feature set).

    Grid: 6 cities x 5 valid targets = 30 ordered city pairs.
          30 pairs x 28 salary steps / persona-cycling -> ~180 rows
          achieved by sampling 6 salary steps per pair (cycling through
          personas), i.e. 30 pairs x 6 salary points = 180 rows exactly.

    Returns:
        pd.DataFrame: columns = source_city, target_city, current_salary,
            cost_of_living_source, cost_of_living_target, persona,
            required_salary (the regression target/label)
    """
    city_df = _build_city_df()
    cities = city_df["city_name"].tolist()
    personas = sorted(VALID_PERSONAS)

    # 6 salary points spanning the full ₹30k-₹300k range, one per
    # ordered city pair (cycling personas), to land at exactly 180 rows
    # (30 ordered pairs x 6 salary points = 180).
    salary_points = np.linspace(30000, 300000, 6)

    rows = []
    persona_cycle_idx = 0

    for source_city in cities:
        for target_city in cities:
            if source_city == target_city:
                continue  # compute_salary_equivalence() disallows same-city pairs

            for salary in salary_points:
                persona = personas[persona_cycle_idx % len(personas)]
                persona_cycle_idx += 1

                required_salary = compute_salary_equivalence(
                    source_city, target_city, float(salary), city_df
                )

                col_source = city_df.loc[city_df["city_name"] == source_city, "cost_of_living_index"].iloc[0]
                col_target = city_df.loc[city_df["city_name"] == target_city, "cost_of_living_index"].iloc[0]

                rows.append({
                    "source_city": source_city,
                    "target_city": target_city,
                    "current_salary": float(salary),
                    "cost_of_living_source": col_source,
                    "cost_of_living_target": col_target,
                    "persona": persona,
                    "required_salary": required_salary,
                })

    df = pd.DataFrame(rows)
    print(f"[train_salary_equivalence_model] Generated {len(df)} training rows "
          f"({len(cities)} cities x {len(cities)-1} valid targets x "
          f"{len(salary_points)} salary points = {len(cities)*(len(cities)-1)*len(salary_points)})")

    return df


def engineer_features(df):
    """
    Encodes source_city, target_city, and persona via LabelEncoder.

    Returns:
        (pd.DataFrame, dict): (feature_df, encoders_dict) with encoders
            keyed 'city' (shared encoder for source/target city names)
            and 'persona'.
    """
    df = df.copy()

    city_encoder = LabelEncoder()
    all_city_values = pd.concat([df["source_city"], df["target_city"]]).unique()
    city_encoder.fit(all_city_values)

    df["source_city_encoded"] = city_encoder.transform(df["source_city"])
    df["target_city_encoded"] = city_encoder.transform(df["target_city"])

    persona_encoder = LabelEncoder()
    df["persona_encoded"] = persona_encoder.fit_transform(df["persona"])

    encoders = {
        "city": city_encoder,
        "persona": persona_encoder,
    }

    return df, encoders


def train_model(df, encoders):
    """
    Trains a GradientBoostingRegressor on the engineered feature matrix
    to predict required_salary.

    Returns:
        dict: {
            'model': fitted GradientBoostingRegressor,
            'feature_encoders': encoders dict,
            'feature_columns': list of feature column names,
            'mae': float,
            'r2': float,
        }
    """
    X = df[FEATURE_COLUMNS]
    y = df["required_salary"]

    print(f"\n[train_salary_equivalence_model] Feature matrix shape: {X.shape}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE
    )

    print(f"[train_salary_equivalence_model] Train set: {X_train.shape[0]} rows | "
          f"Test set: {X_test.shape[0]} rows")

    model = GradientBoostingRegressor(n_estimators=200, random_state=RANDOM_STATE)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"\n[train_salary_equivalence_model] === MODEL PERFORMANCE ===")
    print(f"MAE: ₹{mae:,.2f}")
    print(f"R²:  {r2:.4f}")

    return {
        "model": model,
        "feature_encoders": encoders,
        "feature_columns": FEATURE_COLUMNS,
        "mae": mae,
        "r2": r2,
    }


def save_model(training_result):
    """Saves the trained model + encoders + feature columns to models/salary_equivalence.pkl."""
    os.makedirs(MODELS_DIR, exist_ok=True)

    payload = {
        "model": training_result["model"],
        "feature_encoders": training_result["feature_encoders"],
        "feature_columns": training_result["feature_columns"],
    }

    with open(MODEL_OUTPUT_PATH, "wb") as f:
        pickle.dump(payload, f)

    print(f"\n[train_salary_equivalence_model] Saved model -> {MODEL_OUTPUT_PATH}")


def predict_salary(input_dict):
    """
    Loads the trained salary equivalence model and predicts the required
    salary in target_city for equivalent purchasing power.

    Args:
        input_dict (dict): Must contain the keys:
            source_city (str), target_city (str), current_salary (float),
            cost_of_living_source (float), cost_of_living_target (float),
            persona (str)

    Returns:
        float: predicted required salary in target_city.

    Raises:
        FileNotFoundError: if the model hasn't been trained/saved yet.
        ValueError: if input_dict is missing required keys or contains
            city/persona values not seen during training.
    """
    required_keys = [
        "source_city", "target_city", "current_salary",
        "cost_of_living_source", "cost_of_living_target", "persona",
    ]
    missing = set(required_keys) - set(input_dict.keys())
    if missing:
        raise ValueError(f"input_dict is missing required keys: {missing}")

    if not os.path.exists(MODEL_OUTPUT_PATH):
        raise FileNotFoundError(
            f"Model file not found at {MODEL_OUTPUT_PATH}. "
            f"Run train_salary_equivalence_model.py first."
        )

    with open(MODEL_OUTPUT_PATH, "rb") as f:
        payload = pickle.load(f)

    model = payload["model"]
    encoders = payload["feature_encoders"]
    feature_columns = payload["feature_columns"]

    city_encoder = encoders["city"]
    persona_encoder = encoders["persona"]

    try:
        source_encoded = city_encoder.transform([input_dict["source_city"]])[0]
        target_encoded = city_encoder.transform([input_dict["target_city"]])[0]
    except ValueError as e:
        raise ValueError(
            f"Unknown city encountered. Known cities: {list(city_encoder.classes_)}. "
            f"Underlying error: {e}"
        )

    try:
        persona_encoded = persona_encoder.transform([input_dict["persona"]])[0]
    except ValueError:
        raise ValueError(
            f"Unknown persona '{input_dict['persona']}'. "
            f"Known personas: {list(persona_encoder.classes_)}"
        )

    feature_row = pd.DataFrame([{
        "source_city_encoded": source_encoded,
        "target_city_encoded": target_encoded,
        "current_salary": input_dict["current_salary"],
        "cost_of_living_source": input_dict["cost_of_living_source"],
        "cost_of_living_target": input_dict["cost_of_living_target"],
        "persona_encoded": persona_encoded,
    }])[feature_columns]

    predicted_salary = model.predict(feature_row)[0]

    return round(float(predicted_salary), 2)


def main():
    print("=" * 70)
    print("TRAIN SALARY EQUIVALENCE MODEL — UrbanPulse")
    print("=" * 70)

    training_df = generate_training_data()
    print(f"\nSample of generated training data:")
    print(training_df.head(10).to_string(index=False))

    feature_df, encoders = engineer_features(training_df)
    training_result = train_model(feature_df, encoders)
    save_model(training_result)

    print("\n" + "-" * 70)
    print("TEST CALL — predict_salary()")
    print("-" * 70)

    test_input = {
        "source_city": "Mumbai",
        "target_city": "Pune",
        "current_salary": 150000,
        "cost_of_living_source": 100.0,
        "cost_of_living_target": 75.0,
        "persona": "family_focused",
    }

    print(f"\nTest input:\n  {test_input}")
    predicted_salary = predict_salary(test_input)
    print(f"\nPredicted required salary: ₹{predicted_salary:,.2f}")

    # Cross-check against the deterministic formula for sanity
    expected_deterministic = test_input["current_salary"] * (
        test_input["cost_of_living_target"] / test_input["cost_of_living_source"]
    )
    print(f"Deterministic formula equivalent: ₹{expected_deterministic:,.2f}")
    print(f"(ML prediction should be close to, but not necessarily identical to, "
          f"the deterministic formula — it has learned the underlying pattern.)")

    print("\n[train_salary_equivalence_model] Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[train_salary_equivalence_model] ERROR: {e}", file=sys.stderr)
        sys.exit(1)