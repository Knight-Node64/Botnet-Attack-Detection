"""
M1 – Train & save the best botnet-detection model.
Dataset: UNSW-NB15  (place CSVs in dataset/)
Output : models/botnet_detector.joblib
"""
import os, time
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import xgboost as xgb

# ── Feature engineering ────────────────────────────────────────────────────────
def engineer_features(df):
    df = df.copy()
    df['total_bytes']      = df['sbytes'] + df['dbytes']
    df['total_pkts']       = df['spkts']  + df['dpkts']
    df['bytes_per_pkt_src']= df['sbytes'] / (df['spkts'] + 1e-5)
    df['bytes_per_pkt_dst']= df['dbytes'] / (df['dpkts'] + 1e-5)
    df['pkt_ratio']        = df['spkts']  / (df['dpkts'] + 1e-5)
    df['byte_ratio']       = df['sbytes'] / (df['dbytes'] + 1e-5)
    df['ttl_diff']         = np.abs(df['sttl'] - df['dttl'])
    df['tcp_handshake_sum']    = df['synack'] + df['ackdat']
    for col in ['dur','sbytes','dbytes','sload','dload','rate','spkts','dpkts','total_bytes','total_pkts']:
        if col in df.columns:
            df[f'log_{col}'] = np.log1p(np.maximum(0, df[col]))
    return df

# ── Main ───────────────────────────────────────────────────────────────────────
def train():
    train_df = pd.read_csv("dataset/UNSW_NB15_training-set.csv")
    test_df  = pd.read_csv("dataset/UNSW_NB15_testing-set.csv")

    for df in [train_df, test_df]:
        df.drop(columns=[c for c in ['id','attack_cat'] if c in df.columns], inplace=True)

    train_df = engineer_features(train_df)
    test_df  = engineer_features(test_df)

    encoders = {}
    for col in ['proto', 'service', 'state']:
        le = LabelEncoder()
        le.fit(pd.concat([train_df[col], test_df[col]]).astype(str))
        train_df[col] = le.transform(train_df[col].astype(str))
        test_df[col]  = le.transform(test_df[col].astype(str))
        encoders[col] = le

    X_train, y_train = train_df.drop(columns=['label']), train_df['label']
    X_test,  y_test  = test_df.drop(columns=['label']),  test_df['label']
    feature_names = list(X_train.columns)

    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train)
    X_te = scaler.transform(X_test)

    candidates = {
        'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1),
        'XGBoost':      xgb.XGBClassifier(n_estimators=150, max_depth=8, learning_rate=0.1,
                                           subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1),
    }

    best_f1, best_name, best_model = -1, '', None
    for name, clf in candidates.items():
        t0 = time.time()
        clf.fit(X_tr, y_train)
        yp = clf.predict(X_te)
        ya = clf.predict_proba(X_te)[:, 1]
        f1 = f1_score(y_test, yp)
        print(f"{name}: acc={accuracy_score(y_test,yp):.4f}  prec={precision_score(y_test,yp):.4f}"
              f"  rec={recall_score(y_test,yp):.4f}  f1={f1:.4f}  auc={roc_auc_score(y_test,ya):.4f}"
              f"  time={time.time()-t0:.1f}s")
        if f1 > best_f1:
            best_f1, best_name, best_model = f1, name, clf

    print(f"\nBest → {best_name}  F1={best_f1:.4f}")
    os.makedirs("models", exist_ok=True)
    joblib.dump({'model_name': best_name, 'model': best_model,
                 'scaler': scaler, 'encoders': encoders, 'feature_names': feature_names},
                "models/botnet_detector.joblib")
    print("Saved → models/botnet_detector.joblib")

if __name__ == "__main__":
    train()
