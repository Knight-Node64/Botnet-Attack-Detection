"""
M1 - Train & save the best botnet-detection model.
Dataset: UNSW-NB15  (place CSVs in dataset/)
Output : models/botnet_detector.joblib  (unified sklearn Pipeline + metadata)

The saved artifact contains:
  * model      - sklearn Pipeline [features -> scaler -> classifier]
  * metadata   - train timestamp, test metrics, data file hashes
  * feature_names - engineered feature column order
"""
import hashlib
import os
import time
from datetime import UTC, datetime

import joblib
import pandas as pd
import xgboost as xgb
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from preprocessing import FeatureEngineer, engineer_features

TRAIN_PATH = "dataset/UNSW_NB15_training-set.csv"
TEST_PATH = "dataset/UNSW_NB15_testing-set.csv"
OUTPUT_PATH = "models/botnet_detector.joblib"

CANDIDATES = {
    "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1),
    "XGBoost": xgb.XGBClassifier(
        n_estimators=150, max_depth=8, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1,
    ),
    "LightGBM": LGBMClassifier(
        n_estimators=150, max_depth=8, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1,
        verbose=-1,
    ),
}

SEARCH_SPACES = {
    "RandomForest": {"clf__n_estimators": [100, 200], "clf__max_depth": [10, 15, 20]},
    "XGBoost": {
        "clf__n_estimators": [100, 150],
        "clf__max_depth": [6, 8, 10],
        "clf__learning_rate": [0.05, 0.1],
    },
    "LightGBM": {
        "clf__n_estimators": [100, 150],
        "clf__max_depth": [6, 8, 10],
        "clf__learning_rate": [0.05, 0.1],
    },
}


def file_sha256(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def load_data() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    train_df = pd.read_csv(TRAIN_PATH)
    test_df = pd.read_csv(TEST_PATH)
    for df in (train_df, test_df):
        df.drop(columns=[c for c in ("id", "attack_cat") if c in df.columns], inplace=True)
    return (
        train_df.drop(columns=["label"]), train_df["label"],
        test_df.drop(columns=["label"]), test_df["label"],
    )


def tune_candidate(name: str, pipe: Pipeline, X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Hyperparameter tuning via RandomizedSearchCV. Set SKIP_TUNE=1 to skip."""
    if os.environ.get("SKIP_TUNE") == "1":
        return pipe
    print(f"  Tuning {name} ...")
    t0 = time.time()
    search = RandomizedSearchCV(
        pipe,
        SEARCH_SPACES[name],
        n_iter=5,
        cv=3,
        scoring="f1",
        n_jobs=-1,
        random_state=42,
        verbose=0,
    )
    search.fit(X, y)
    print(f"    best params: {search.best_params_}  (took {time.time() - t0:.1f}s)")
    return search.best_estimator_


def evaluate(model: Pipeline, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
    yp = model.predict(X)
    ya = model.predict_proba(X)[:, 1]
    return {
        "accuracy": float(accuracy_score(y, yp)),
        "precision": float(precision_score(y, yp)),
        "recall": float(recall_score(y, yp)),
        "f1": float(f1_score(y, yp)),
        "roc_auc": float(roc_auc_score(y, ya)),
    }


def train() -> None:
    X_train, y_train, X_test, y_test = load_data()
    feature_names = list(engineer_features(X_train).columns)

    best_f1, best_name, best_model = -1.0, "", None
    for name, clf in CANDIDATES.items():
        t0 = time.time()
        pipe = Pipeline([
            ("features", FeatureEngineer()),
            ("scaler", StandardScaler()),
            ("clf", clf),
        ])
        if os.environ.get("SKIP_TUNE") == "1":
            pipe.fit(X_train, y_train)
            fitted = pipe
        else:
            fitted = tune_candidate(name, pipe, X_train, y_train)
        metrics = evaluate(fitted, X_test, y_test)
        print(
            f"{name}: acc={metrics['accuracy']:.4f}  prec={metrics['precision']:.4f}"
            f"  rec={metrics['recall']:.4f}  f1={metrics['f1']:.4f}"
            f"  auc={metrics['roc_auc']:.4f}  time={time.time() - t0:.1f}s"
        )
        if metrics["f1"] > best_f1:
            best_f1, best_name, best_model = metrics["f1"], name, fitted

    print(f"\nBest -> {best_name}  F1={best_f1:.4f}")
    metadata = {
        "model_name": best_name,
        "trained_at": datetime.now(UTC).isoformat(),
        "test_metrics": evaluate(best_model, X_test, y_test),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "train_sha256": file_sha256(TRAIN_PATH),
        "test_sha256": file_sha256(TEST_PATH),
    }

    os.makedirs("models", exist_ok=True)
    joblib.dump(
        {"model": best_model, "feature_names": feature_names, "metadata": metadata},
        OUTPUT_PATH,
    )
    print(f"Saved -> {OUTPUT_PATH}")
    print(f"  model_name = {best_name}, f1 = {best_f1:.4f}, trained_at = {metadata['trained_at']}")


if __name__ == "__main__":
    train()
