"""Shared preprocessing for training and serving parity.

Single source of truth for UNSW-NB15 feature engineering and categorical
encoding. Used by ``train_model.py`` (fit), ``predict.py`` / ``app.py`` (serve).
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import LabelEncoder

CATEGORICAL_COLS: list[str] = ["proto", "service", "state"]

SKEWED_COLS: list[str] = [
    "dur", "sbytes", "dbytes", "sload", "dload", "rate",
    "spkts", "dpkts", "total_bytes", "total_pkts",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Applies engineered features (aggregations, ratios, log transforms)."""
    df = df.copy()
    df["total_bytes"] = df["sbytes"] + df["dbytes"]
    df["total_pkts"] = df["spkts"] + df["dpkts"]
    df["bytes_per_pkt_src"] = df["sbytes"] / (df["spkts"] + 1e-5)
    df["bytes_per_pkt_dst"] = df["dbytes"] / (df["dpkts"] + 1e-5)
    df["pkt_ratio"] = df["spkts"] / (df["dpkts"] + 1e-5)
    df["byte_ratio"] = df["sbytes"] / (df["dbytes"] + 1e-5)
    df["ttl_diff"] = np.abs(df["sttl"] - df["dttl"])
    df["tcp_handshake_sum"] = df["synack"] + df["ackdat"]
    for col in SKEWED_COLS:
        if col in df.columns:
            df[f"log_{col}"] = np.log1p(np.maximum(0, df[col]))
    return df


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """sklearn-compatible transformer: feature engineering + categorical encoding.

    Fits one ``LabelEncoder`` per categorical column and records the exact
    feature column order. Unknown categories seen at inference time fall back
    to the first training class, mirroring the previous serve-time behavior.
    """

    def __init__(self) -> None:
        self.encoders_: dict[str, LabelEncoder] = {}
        self.feature_names_: list[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "FeatureEngineer":
        X = X.copy()
        self.feature_names_ = list(engineer_features(X).columns)
        for col in CATEGORICAL_COLS:
            le = LabelEncoder()
            le.fit(X[col].astype(str))
            self.encoders_[col] = le
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = engineer_features(X)

        def _encode(col: str, le: LabelEncoder) -> pd.Series:
            return X[col].astype(str).map(
                lambda s: le.transform([s])[0]
                if s in le.classes_
                else le.transform([le.classes_[0]])[0]
            )

        for col, le in self.encoders_.items():
            X[col] = _encode(col, le)
        return X[self.feature_names_]

    def get_feature_names_out(self, input_features: list[str] | None = None) -> list[str]:
        return self.feature_names_
