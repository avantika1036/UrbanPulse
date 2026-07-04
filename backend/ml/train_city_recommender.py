"""
backend/ml/train_city_recommender.py

Trains a RandomForestClassifier to predict which city a user is most
likely to select for relocation, based on their profile attributes.

Data:
  data/synthetic/user_profiles.csv     — user attributes
  data/synthetic/relocation_queries.csv — selected_city labels, joined on user_id

Features:
  persona (label-encoded), age, monthly_income, years_experience,
  dependents_count, priority_1/2/3 (label-encoded), has_children (binary)

Target:
  selected_city (label-encoded via models/city_label_encoder.pkl)

Saves:
  models/city_recommender.pkl       — trained RandomForestClassifier
  models/city_label_encoder.pkl     — LabelEncoder for the target city names

Run: python backend/ml/train_city_recommender.py
"""

import os
import sys
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# ── PATHS ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

SYNTHETIC_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

USER_PROFILES_PATH = os.path.join(SYNTHETIC_DIR, "user_profiles.csv")
RELOCATION_QUERIES_PATH = os.path.join(SYNTHETIC_DIR, "relocation_queries.csv")

MODEL_OUTPUT_PATH = os.path.join(MODELS_DIR, "city_recommender.pkl")
LABEL_ENCODER_OUTPUT_PATH = os.path.join(MODELS_DIR, "city_label_encoder.pkl")

RANDOM_STATE = 42

FEATURE_COLUMNS = [
    "persona_encoded", "age", "monthly_income", "years_experience",
    "dependents_count", "priority_1_encoded", "priority_2_encoded",
    "priority_3_encoded", "has_children_binary",
]


def load_and_join_data():
    user_profiles = pd.read_csv(USER_PROFILES_PATH, encoding="utf-8-sig")
    relocation_queries = pd.read_csv(RELOCATION_QUERIES_PATH, encoding="utf-8-sig")

    print(f"[train_city_recommender] Loaded user_profiles.csv: {user_profiles.shape}")
    print(f"[train_city_recommender] Loaded relocation_queries.csv: {relocation_queries.shape}")

    joined = relocation_queries.merge(
        user_profiles, on="user_id", how="inner", suffixes=("_query", "_user")
    )

    # Ensure persona column is consistent
    if "persona_user" in joined.columns:
        joined = joined.rename(columns={"persona_user": "persona"})
    elif "persona_query" in joined.columns:
        joined = joined.rename(columns={"persona_query": "persona"})

    print(f"[train_city_recommender] Joined dataset shape: {joined.shape}")
    print(f"[train_city_recommender] Columns after join: {list(joined.columns)}")

    return joined


def engineer_features(df):
    """
    Engineers the model feature matrix from the joined DataFrame.

    Encodes:
      - persona -> persona_encoded (LabelEncoder)
      - priority_1, priority_2, priority_3 -> *_encoded (single shared
        LabelEncoder across all three priority columns, since they draw
        from the same value space)
      - has_children -> has_children_binary (0/1)

    Returns:
        (pd.DataFrame, dict): (feature_df, encoders_dict) where
            encoders_dict contains the fitted LabelEncoders used, keyed
            by 'persona' and 'priority'.
    """
    df = df.copy()

    persona_encoder = LabelEncoder()
    df["persona_encoded"] = persona_encoder.fit_transform(df["persona"])

    # Priority columns share a single encoder since values overlap
    # (e.g. 'affordability' can appear in priority_1, priority_2, or priority_3)
    all_priority_values = pd.concat([
        df["priority_1"], df["priority_2"], df["priority_3"]
    ]).dropna().unique()

    priority_encoder = LabelEncoder()
    priority_encoder.fit(all_priority_values)

    df["priority_1_encoded"] = priority_encoder.transform(df["priority_1"])
    df["priority_2_encoded"] = priority_encoder.transform(df["priority_2"])
    df["priority_3_encoded"] = priority_encoder.transform(df["priority_3"])

    df["has_children_binary"] = df["has_children"].astype(bool).astype(int)

    encoders = {
        "persona": persona_encoder,
        "priority": priority_encoder,
    }

    return df, encoders


def train_model(df, encoders):
    """
    Trains a RandomForestClassifier on the engineered feature matrix.

    Args:
        df (pd.DataFrame): output of engineer_features() — must contain
            FEATURE_COLUMNS and 'selected_city'.
        encoders (dict): persona/priority encoders from engineer_features().

    Returns:
        dict: {
            'model': fitted RandomForestClassifier,
            'city_label_encoder': fitted LabelEncoder for selected_city,
            'feature_encoders': encoders dict,
            'feature_columns': list of feature column names,
            'accuracy': float,
            'X_test': test features (for downstream feature_importance.py use),
            'y_test': test labels,
        }
    """
    X = df[FEATURE_COLUMNS]
    city_encoder = LabelEncoder()
    y = city_encoder.fit_transform(df["selected_city"])

    print(f"\n[train_city_recommender] Feature matrix shape: {X.shape}")
    print(f"[train_city_recommender] Target classes ({len(city_encoder.classes_)}): "
          f"{list(city_encoder.classes_)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )

    print(f"[train_city_recommender] Train set: {X_train.shape[0]} rows | "
          f"Test set: {X_test.shape[0]} rows")

    model = RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n[train_city_recommender] === MODEL PERFORMANCE ===")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"\nClassification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=city_encoder.classes_,
        zero_division=0,
    ))

    return {
        "model": model,
        "city_label_encoder": city_encoder,
        "feature_encoders": encoders,
        "feature_columns": FEATURE_COLUMNS,
        "accuracy": accuracy,
        "X_test": X_test,
        "y_test": y_test,
    }


def save_model(training_result):
    """
    Saves the trained model and city label encoder to models/.

    Saves two separate pickle files as specified:
      - models/city_recommender.pkl   : dict containing the model,
        feature encoders, and feature column order (everything needed
        for inference except the city label encoder, which is saved
        separately per the spec).
      - models/city_label_encoder.pkl : the fitted LabelEncoder for
        selected_city, saved standalone for direct reuse.
    """
    os.makedirs(MODELS_DIR, exist_ok=True)

    recommender_payload = {
        "model": training_result["model"],
        "feature_encoders": training_result["feature_encoders"],
        "feature_columns": training_result["feature_columns"],
    }

    with open(MODEL_OUTPUT_PATH, "wb") as f:
        pickle.dump(recommender_payload, f)
    print(f"\n[train_city_recommender] Saved model -> {MODEL_OUTPUT_PATH}")

    with open(LABEL_ENCODER_OUTPUT_PATH, "wb") as f:
        pickle.dump(training_result["city_label_encoder"], f)
    print(f"[train_city_recommender] Saved city label encoder -> {LABEL_ENCODER_OUTPUT_PATH}")


def predict_city(user_dict):
    """
    Loads the trained model and predicts the most likely city for a
    given user profile dict.

    Args:
        user_dict (dict): Must contain the keys:
            persona (str), age (int), monthly_income (float),
            years_experience (float), dependents_count (int),
            priority_1 (str), priority_2 (str), priority_3 (str),
            has_children (bool)

    Returns:
        str: predicted city name.

    Raises:
        FileNotFoundError: if the model files haven't been trained/saved yet.
        ValueError: if user_dict is missing required keys, or contains
            persona/priority values not seen during training.
    """
    required_keys = [
        "persona", "age", "monthly_income", "years_experience",
        "dependents_count", "priority_1", "priority_2", "priority_3",
        "has_children",
    ]
    missing = set(required_keys) - set(user_dict.keys())
    if missing:
        raise ValueError(f"user_dict is missing required keys: {missing}")

    if not os.path.exists(MODEL_OUTPUT_PATH) or not os.path.exists(LABEL_ENCODER_OUTPUT_PATH):
        raise FileNotFoundError(
            f"Model files not found. Run train_city_recommender.py first to "
            f"generate {MODEL_OUTPUT_PATH} and {LABEL_ENCODER_OUTPUT_PATH}."
        )

    with open(MODEL_OUTPUT_PATH, "rb") as f:
        recommender_payload = pickle.load(f)
    with open(LABEL_ENCODER_OUTPUT_PATH, "rb") as f:
        city_encoder = pickle.load(f)

    model = recommender_payload["model"]
    encoders = recommender_payload["feature_encoders"]
    feature_columns = recommender_payload["feature_columns"]

    persona_encoder = encoders["persona"]
    priority_encoder = encoders["priority"]

    try:
        persona_encoded = persona_encoder.transform([user_dict["persona"]])[0]
    except ValueError:
        raise ValueError(
            f"Unknown persona '{user_dict['persona']}'. "
            f"Known personas: {list(persona_encoder.classes_)}"
        )

    try:
        priority_1_encoded = priority_encoder.transform([user_dict["priority_1"]])[0]
        priority_2_encoded = priority_encoder.transform([user_dict["priority_2"]])[0]
        priority_3_encoded = priority_encoder.transform([user_dict["priority_3"]])[0]
    except ValueError as e:
        raise ValueError(
            f"Unknown priority value encountered. "
            f"Known priorities: {list(priority_encoder.classes_)}. "
            f"Underlying error: {e}"
        )

    has_children_binary = int(bool(user_dict["has_children"]))

    feature_row = pd.DataFrame([{
        "persona_encoded": persona_encoded,
        "age": user_dict["age"],
        "monthly_income": user_dict["monthly_income"],
        "years_experience": user_dict["years_experience"],
        "dependents_count": user_dict["dependents_count"],
        "priority_1_encoded": priority_1_encoded,
        "priority_2_encoded": priority_2_encoded,
        "priority_3_encoded": priority_3_encoded,
        "has_children_binary": has_children_binary,
    }])[feature_columns]

    predicted_encoded = model.predict(feature_row)[0]
    predicted_city = city_encoder.inverse_transform([predicted_encoded])[0]

    return predicted_city


def main():
    print("=" * 70)
    print("TRAIN CITY RECOMMENDER — UrbanPulse")
    print("=" * 70)

    joined_df = load_and_join_data()
    feature_df, encoders = engineer_features(joined_df)
    training_result = train_model(feature_df, encoders)
    save_model(training_result)

    print("\n" + "-" * 70)
    print("TEST CALL — predict_city()")
    print("-" * 70)

    test_user = {
        "persona": "early_career",
        "age": 26,
        "monthly_income": 65000,
        "years_experience": 3.0,
        "dependents_count": 0,
        "priority_1": "job_market",
        "priority_2": "growth",
        "priority_3": "affordability",
        "has_children": False,
    }

    print(f"\nTest user profile:\n  {test_user}")
    predicted_city = predict_city(test_user)
    print(f"\nPredicted city: {predicted_city}")

    print("\n[train_city_recommender] Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[train_city_recommender] ERROR: {e}", file=sys.stderr)
        sys.exit(1)