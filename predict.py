import os

import joblib
import pandas as pd

MODEL_PATH = os.path.join("models", "botnet_detector.joblib")
TEST_PATH = os.path.join("dataset", "UNSW_NB15_testing-set.csv")


def run_predictions() -> None:
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}. Please run train_model.py first.")
        return

    print(f"Loading trained pipeline from: {MODEL_PATH}")
    artifact = joblib.load(MODEL_PATH)
    model = artifact["model"]
    metadata = artifact.get("metadata", {})

    print(f"Loading sample records from: {TEST_PATH}")
    test_df = pd.read_csv(TEST_PATH)

    samples = test_df.sample(n=10, random_state=42).copy()
    y_true = samples["label"].values
    attack_cats = samples["attack_cat"].values if "attack_cat" in samples.columns else None

    drop_cols = ["id", "attack_cat", "label"]
    X_samples = samples.drop(columns=[c for c in drop_cols if c in samples.columns])

    preds = model.predict(X_samples)
    probs = model.predict_proba(X_samples)[:, 1]

    print(f"\nModel: {metadata.get('model_name', 'unknown')}  "
          f"(trained {metadata.get('trained_at', 'n/a')})")
    print("--- Predictions on Random Test Samples ---")
    for i in range(len(samples)):
        true_label = "Attack" if y_true[i] == 1 else "Normal"
        pred_label = "Attack" if preds[i] == 1 else "Normal"
        cat = attack_cats[i] if attack_cats is not None else "N/A"
        print(f"Sample {i + 1}: True={true_label} ({cat}), Predicted={pred_label} "
              f"(Confidence={probs[i] * 100:.2f}%)")


if __name__ == "__main__":
    run_predictions()
