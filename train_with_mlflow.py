"""
M1 (variant) – Train with MLflow experiment tracking.
Run:  python train_with_mlflow.py
"""
import os, time
import numpy as np, pandas as pd, joblib, mlflow, mlflow.sklearn
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

def engineer_features(df):
    df = df.copy()
    df['total_bytes']       = df['sbytes'] + df['dbytes']
    df['total_pkts']        = df['spkts']  + df['dpkts']
    df['bytes_per_pkt_src'] = df['sbytes'] / (df['spkts'] + 1e-5)
    df['bytes_per_pkt_dst'] = df['dbytes'] / (df['dpkts'] + 1e-5)
    df['pkt_ratio']         = df['spkts']  / (df['dpkts'] + 1e-5)
    df['byte_ratio']        = df['sbytes'] / (df['dbytes'] + 1e-5)
    df['ttl_diff']          = np.abs(df['sttl'] - df['dttl'])
    df['tcp_handshake_sum']     = df['synack'] + df['ackdat']
    for col in ['dur','sbytes','dbytes','sload','dload','rate','spkts','dpkts','total_bytes','total_pkts']:
        if col in df.columns:
            df[f'log_{col}'] = np.log1p(np.maximum(0, df[col]))
    return df

def run():
    mlflow.set_experiment("Botnet_Detection_MLOps")
    train_df = pd.read_csv("dataset/UNSW_NB15_training-set.csv")
    test_df  = pd.read_csv("dataset/UNSW_NB15_testing-set.csv")
    for df in [train_df, test_df]:
        df.drop(columns=[c for c in ['id','attack_cat'] if c in df.columns], inplace=True)
    train_df, test_df = engineer_features(train_df), engineer_features(test_df)

    encoders = {}
    for col in ['proto','service','state']:
        le = LabelEncoder()
        le.fit(pd.concat([train_df[col], test_df[col]]).astype(str))
        train_df[col] = le.transform(train_df[col].astype(str))
        test_df[col]  = le.transform(test_df[col].astype(str))
        encoders[col] = le

    X_tr, y_tr = train_df.drop(columns=['label']), train_df['label']
    X_te, y_te = test_df.drop(columns=['label']),  test_df['label']
    features   = list(X_tr.columns)
    scaler     = StandardScaler()
    Xtr, Xte   = scaler.fit_transform(X_tr), scaler.transform(X_te)

    params = {'n_estimators': 100, 'max_depth': 15, 'random_state': 42}
    with mlflow.start_run(run_name="RF_botnet"):
        mlflow.log_params(params)
        clf = RandomForestClassifier(**params, n_jobs=-1)
        t0 = time.time()
        clf.fit(Xtr, y_tr)
        yp = clf.predict(Xte);  ya = clf.predict_proba(Xte)[:, 1]
        mlflow.log_metrics({
            "accuracy":  accuracy_score(y_te, yp),
            "precision": precision_score(y_te, yp),
            "recall":    recall_score(y_te, yp),
            "f1":        f1_score(y_te, yp),
            "roc_auc":   roc_auc_score(y_te, ya),
            "train_sec": time.time() - t0,
        })
        os.makedirs("models", exist_ok=True)
        pkg_path = "models/botnet_detector.joblib"
        joblib.dump({'model_name':'RandomForest','model':clf,'scaler':scaler,
                     'encoders':encoders,'feature_names':features}, pkg_path)
        mlflow.log_artifact(pkg_path, "model_package")
        print(f"Done — F1={f1_score(y_te,yp):.4f}")

if __name__ == "__main__":
    run()
