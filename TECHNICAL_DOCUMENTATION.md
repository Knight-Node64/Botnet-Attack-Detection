# 📘 Botnet Attack Detection — Full Technical & Architectural Documentation

This document provides a comprehensive, component-by-component, and **line-by-line breakdown** of the entire **Botnet Attack Detection MLOps Pipeline** repository hosted at [github.com/Knight-Node64/Botnet-Detection](https://github.com/Knight-Node64/Botnet-Detection).

---

## 📂 Repository Structure Overview

```
Botnet-Detection/
├── .github/
│   └── workflows/
│       └── ci-cd.yml             # M3: Continuous Integration & Automated Deployment Pipeline
├── k8s/
│   ├── deployment.yaml           # M4: Kubernetes 2-replica Deployment & Probes Manifest
│   └── service.yaml              # M4: Kubernetes ClusterIP Service Manifest
├── models/
│   └── botnet_detector.joblib   # M1: Trained Serialized Model Artifacts & Preprocessors
├── presentation_assets/
│   ├── confusion_matrix.png     # Model evaluation visualization
│   ├── feature_importances.png  # Feature importance ranking plot
│   ├── roc_curve.png            # ROC-AUC curve plot
│   └── setup_bat_interface.png  # CLI User Interface Screenshot
├── tests/
│   ├── __init__.py              # Python package marker
│   ├── test_api.py              # M3: Unit tests for API endpoints (/health, /predict, /metrics)
│   ├── test_pipeline.py        # M3: Integration tests for model training & evaluation
│   └── test_preprocessing.py   # M3: Unit tests for feature engineering logic
├── .gitignore                    # Version control ignore definitions
├── Dockerfile                    # M4: Minimal python:3.11-slim container spec
├── README.md                     # Master project overview & badges
├── app.py                        # M2: FastAPI REST inference service
├── banner.txt                    # Braille ASCII art CLI header banner
├── docker-compose.yml            # M4: Multi-container orchestrator configuration
├── monitor.py                    # M5: Continuous live monitoring & drift detector script
├── predict.py                    # CLI prediction execution script
├── requirements.txt              # Production python dependencies
├── run_pipeline.bat              # Non-interactive automated execution script for CI
├── setup.bat                     # Windows CLI Interactive Launcher
├── smoke_test.py                 # M5: Endpoint smoke testing & automated load simulator
├── task-ips-tech.pdf             # Original technical task specification document
├── train_model.py                # M1: Core model training & feature engineering script
├── train_with_mlflow.py         # M1: MLflow experiment tracking & metric logging script
└── visualize_results.py          # Asset generation script for performance charts
```

---

## 🛠️ M1–M5 Milestone Architecture Framework

The project is structured according to five fundamental MLOps milestones:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                   UNSW-NB15 Dataset                                      │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  M1: MODEL TRAINING & FEATURE ENGINEERING (train_model.py / train_with_mlflow.py)      │
│  - Combines packet/byte ratios, TTL differences & log transforms                         │
│  - Trains RandomForest & XGBoost classifiers                                             │
│  - Exports best model artifact (models/botnet_detector.joblib)                           │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  M2: FASTAPI REST INFERENCE SERVICE (app.py)                                             │
│  - Exposes GET /health, POST /predict, GET /metrics                                      │
│  - Real-time schema validation via Pydantic Data Models                                  │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  M3: AUTOMATED TESTING & CONTINUOUS INTEGRATION (.github/workflows/ci-cd.yml & tests/)   │
│  - Pytest suites validating preprocessing, model outputs, and API routes                 │
│  - GitHub Actions automated runner on every commit                                       │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  M4: CONTAINERIZATION & KUBERNETES DEPLOYMENT (Dockerfile, docker-compose.yml, k8s/)    │
│  - Docker containerization on python:3.11-slim base image                                │
│  - Kubernetes Deployment with replica sets, Liveness & Readiness probes                  │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  M5: SMOKE TESTING & LIVE MONITORING (smoke_test.py & monitor.py)                         │
│  - Real-time traffic simulation sending batches of network flows                         │
│  - Tracking request latency, attack ratios, and system health                            │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Line-by-Line Technical Code Analysis

### 1. `train_model.py` — Core Feature Engineering & Model Selection (M1)

`train_model.py` reads raw flow data, computes custom network flow metrics, scales numeric values, trains multiple candidate classifiers, and serializes the best performing model.

#### Imports & Setup (Lines 1–14)
```python
1: """
2: M1 – Train & save the best botnet-detection model.
3: Dataset: UNSW-NB15  (place CSVs in dataset/)
4: Output : models/botnet_detector.joblib
5: """
6: import os, time
7: import numpy as np
8: import pandas as pd
9: import joblib
10: from sklearn.preprocessing import LabelEncoder, StandardScaler
11: from sklearn.ensemble import RandomForestClassifier
12: from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
13: import xgboost as xgb
```
- **Lines 6–9**: standard system utilities (`os`, `time`), numerical processing (`numpy`), tabular data manipulation (`pandas`), and model persistence (`joblib`).
- **Lines 10–13**: Imports `LabelEncoder` for categorical strings, `StandardScaler` for zero-mean/unit-variance feature scaling, `RandomForestClassifier`, performance evaluation metrics, and `xgboost`.

#### Feature Engineering Function (Lines 16–29)
```python
16: def engineer_features(df):
17:     df = df.copy()
18:     df['total_bytes']      = df['sbytes'] + df['dbytes']
19:     df['total_pkts']       = df['spkts']  + df['dpkts']
20:     df['bytes_per_pkt_src']= df['sbytes'] / (df['spkts'] + 1e-5)
21:     df['bytes_per_pkt_dst']= df['dbytes'] / (df['dpkts'] + 1e-5)
22:     df['pkt_ratio']        = df['spkts']  / (df['dpkts'] + 1e-5)
23:     df['byte_ratio']       = df['sbytes'] / (df['dbytes'] + 1e-5)
24:     df['ttl_diff']         = np.abs(df['sttl'] - df['dttl'])
25:     df['tcp_handshake_sum']    = df['synack'] + df['ackdat']
26:     for col in ['dur','sbytes','dbytes','sload','dload','rate','spkts','dpkts','total_bytes','total_pkts']:
27:         if col in df.columns:
28:             df[f'log_{col}'] = np.log1p(np.maximum(0, df[col]))
29:     return df
```
- **Line 17**: `df.copy()` ensures input immutability avoiding `SettingWithCopyWarning`.
- **Lines 18–19**: `total_bytes` and `total_pkts` summarize bidirectional volume.
- **Lines 20–23**: Calculates per-packet payload sizes (`bytes_per_pkt_src`, `bytes_per_pkt_dst`) and bidirectional ratios (`pkt_ratio`, `byte_ratio`). `1e-5` prevents `ZeroDivisionError`.
- **Line 24**: `ttl_diff` measures difference in Time-To-Live between source (`sttl`) and destination (`dttl`), exposing spoofed or proxied botnet traffic.
- **Line 25**: `tcp_handshake_sum` aggregates SYN-ACK and ACK-DAT latency to detect handshake anomalies common in SYN floods and slowloris attacks.
- **Lines 26–28**: Applies `np.log1p` ($\ln(1+x)$) log transformation to heavily skewed network volume metrics to normalize distributions for decision trees.

#### Training Pipeline Execution (Lines 32–85)
```python
32: def train():
33:     train_df = pd.read_csv("dataset/UNSW_NB15_training-set.csv")
34:     test_df  = pd.read_csv("dataset/UNSW_NB15_testing-set.csv")
35: 
36:     for df in [train_df, test_df]:
37:         df.drop(columns=[c for c in ['id','attack_cat'] if c in df.columns], inplace=True)
38: 
39:     train_df = engineer_features(train_df)
40:     test_df  = engineer_features(test_df)
```
- **Lines 33–34**: Loads train/test splits.
- **Line 37**: Drops identifier (`id`) and multi-class target (`attack_cat`) keeping binary binary `label`.
- **Lines 39–40**: Applies feature engineering identically to both datasets.

```python
42:     encoders = {}
43:     for col in ['proto', 'service', 'state']:
44:         le = LabelEncoder()
45:         le.fit(pd.concat([train_df[col], test_df[col]]).astype(str))
46:         train_df[col] = le.transform(train_df[col].astype(str))
47:         test_df[col]  = le.transform(test_df[col].astype(str))
48:         encoders[col] = le
```
- **Lines 43–48**: Fits `LabelEncoder` across combined categorical columns (`proto`, `service`, `state`) so unseen strings in testing don't cause errors, saving fitted encoders into a dictionary.

```python
50:     X_train, y_train = train_df.drop(columns=['label']), train_df['label']
51:     X_test,  y_test  = test_df.drop(columns=['label']),  test_df['label']
52:     feature_names = list(X_train.columns)
53: 
54:     scaler = StandardScaler()
55:     X_tr = scaler.fit_transform(X_train)
56:     X_te = scaler.transform(X_test)
```
- **Lines 50–52**: Separates features from target label and stores feature column ordering.
- **Lines 54–56**: Standardizes features ($Z = \frac{x - \mu}{\sigma}$).

```python
58:     candidates = {
59:         'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1),
60:         'XGBoost':      xgb.XGBClassifier(n_estimators=150, max_depth=8, learning_rate=0.1,
61:                                            subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1),
62:     }
63: 
64:     best_f1, best_name, best_model = -1, '', None
65:     for name, clf in candidates.items():
66:         t0 = time.time()
67:         clf.fit(X_tr, y_train)
68:         yp = clf.predict(X_te)
69:         ya = clf.predict_proba(X_te)[:, 1]
70:         f1 = f1_score(y_test, yp)
71:         print(f"{name}: acc={accuracy_score(y_test,yp):.4f}  prec={precision_score(y_test,yp):.4f}"
72:               f"  rec={recall_score(y_test,yp):.4f}  f1={f1:.4f}  auc={roc_auc_score(y_test,ya):.4f}"
73:               f"  time={time.time()-t0:.1f}s")
74:         if f1 > best_f1:
75:             best_f1, best_name, best_model = f1, name, clf
```
- **Lines 58–62**: Defines candidate classifiers with hyperparameters tailored for tabular flow data.
- **Lines 65–75**: Evaluates candidates by F1-Score, accuracy, precision, recall, and ROC-AUC. Selects candidate with highest F1-Score.

```python
77:     print(f"\nBest → {best_name}  F1={best_f1:.4f}")
78:     os.makedirs("models", exist_ok=True)
79:     joblib.dump({'model_name': best_name, 'model': best_model,
80:                  'scaler': scaler, 'encoders': encoders, 'feature_names': feature_names},
81:                 "models/botnet_detector.joblib")
82:     print("Saved → models/botnet_detector.joblib")
```
- **Lines 78–82**: Saves complete inference artifact payload (model, scaler, label encoders, feature names) into a single joblib dictionary.

---

### 2. `app.py` — FastAPI Inference REST API (M2)

`app.py` exposes REST endpoints to consume network flow JSON payloads, apply preprocessing pipelines on-the-fly, and output prediction scores with latency metrics.

#### Imports & App Setup (Lines 1–17)
```python
5: import os, time, logging
6: import numpy as np, pandas as pd, joblib
7: from fastapi import FastAPI, HTTPException
8: from pydantic import BaseModel
9: 
10: logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
11: log = logging.getLogger("botnet_api")
12: 
13: app = FastAPI(title="Botnet Detection API", version="1.0")
14: 
15: MODEL_PATH = "models/botnet_detector.joblib"
16: pipeline   = None
17: stats      = {"total": 0, "attacks": 0, "latency_ms": 0.0}
```
- **Line 13**: Initializes FastAPI web app instance.
- **Line 17**: In-memory dictionary tracking total requests, attack detections, and cumulative latency.

#### Model Lifespan Loading (Lines 19–26)
```python
19: @app.on_event("startup")
20: def load_model():
21:     global pipeline
22:     if os.path.exists(MODEL_PATH):
23:         pipeline = joblib.load(MODEL_PATH)
24:         log.info("Model loaded: %s", pipeline['model_name'])
25:     else:
26:         log.warning("Model not found at %s", MODEL_PATH)
```
- Loads serialized dictionary artifact into memory once during application startup.

#### Request Schema & In-Flight Preprocessing (Lines 29–67)
```python
29: class Flow(BaseModel):
30:     model_config = {"json_schema_extra": {"examples": [{ ... }]}}
40:     dur:float=0.0; proto:str="tcp"; service:str="-"; state:str="FIN"
41:     spkts:int=6; dpkts:int=4; sbytes:int=258; dbytes:int=172; rate:float=74.08
...
50:     ct_src_ltm:int=1; ct_srv_dst:int=1; is_sm_ips_ports:int=0
```
- **Lines 29–50**: Pydantic schema enforcing data types and providing OpenAPI documentation examples.

```python
52: def _preprocess(data: dict) -> np.ndarray:
53:     df = pd.DataFrame([data])
54:     df['total_bytes']       = df['sbytes'] + df['dbytes']
55:     df['total_pkts']        = df['spkts']  + df['dpkts']
56:     df['bytes_per_pkt_src'] = df['sbytes'] / (df['spkts'] + 1e-5)
57:     df['bytes_per_pkt_dst'] = df['dbytes'] / (df['dpkts'] + 1e-5)
58:     df['pkt_ratio']         = df['spkts']  / (df['dpkts'] + 1e-5)
59:     df['byte_ratio']        = df['sbytes'] / (df['dbytes'] + 1e-5)
60:     df['ttl_diff']          = np.abs(df['sttl'] - df['dttl'])
61:     df['tcp_handshake_sum'] = df['synack'] + df['ackdat']
62:     for col in ['dur','sbytes','dbytes','sload','dload','rate','spkts','dpkts','total_bytes','total_pkts']:
63:         df[f'log_{col}'] = np.log1p(np.maximum(0, df[col]))
64:     for col in ['proto','service','state']:
65:         le, v = pipeline['encoders'][col], str(df[col].values[0])
66:         df[col] = le.transform([v])[0] if v in le.classes_ else le.transform([le.classes_[0]])[0]
67:     return pipeline['scaler'].transform(df[pipeline['feature_names']])
```
- **Lines 52–67**: Re-executes the exact feature engineering steps from `train_model.py` on incoming REST JSON payloads, encoding categoricals and scaling output using saved `pipeline['scaler']`.

#### API Endpoints (Lines 70–98)
```python
70: @app.get("/health")
71: def health():
72:     ok = pipeline is not None
73:     return {"status": "healthy" if ok else "unhealthy",
74:             "model_loaded": ok,
75:             "model_name": pipeline['model_name'] if ok else None}
```
- **`/health`**: Used by Kubernetes readiness/liveness probes to verify API health and model readiness.

```python
77: @app.post("/predict")
78: def predict(flow: Flow):
79:     if pipeline is None:
80:         raise HTTPException(503, "Model not loaded")
81:     t0 = time.time()
82:     X  = _preprocess(flow.model_dump())
83:     pred = int(pipeline['model'].predict(X)[0])
84:     prob = float(pipeline['model'].predict_proba(X)[0, 1])
85:     ms   = (time.time() - t0) * 1000
86:     stats["total"] += 1; stats["latency_ms"] += ms
87:     if pred: stats["attacks"] += 1
88:     log.info("pred=%s prob=%.4f lat=%.1fms", pred, prob, ms)
89:     return {"prediction": pred, "label": "Attack" if pred else "Normal",
90:             "attack_probability": round(prob, 4), "latency_ms": round(ms, 2)}
```
- **`/predict`**: Converts incoming request body to DataFrame via `_preprocess`, runs inference via `.predict()` and `.predict_proba()`, logs execution latency, and updates global statistics.

```python
92: @app.get("/metrics")
93: def metrics():
94:     t = stats["total"]
95:     return {"total_requests": t, "attacks_detected": stats["attacks"],
96:             "normal_flows": t - stats["attacks"],
97:             "avg_latency_ms": round(stats["latency_ms"] / t, 2) if t else 0.0}
```
- **`/metrics`**: Exposes real-time telemetry on total requests, attack percentages, and average response latency.

---

### 3. `.github/workflows/ci-cd.yml` — Automated CI/CD Pipeline (M3)

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"

    - name: Install Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run Pytest Suite
      run: |
        python -m pytest tests/ -v

    - name: Build Docker Image
      run: |
        docker build -t botnet-detector:latest .

    - name: Test Docker Container Execution
      run: |
        docker run -d --name botnet_test -p 8000:8000 botnet-detector:latest
        sleep 5
        curl --fail http://localhost:8000/health
        docker stop botnet_test
```
- **Triggers**: Runs on every push or PR to `main`.
- **Workflow Steps**:
  1. Checks out repository source code.
  2. Provisions Python 3.11 environment.
  3. Installs requirements via `pip`.
  4. Runs pytest unit test suite (`tests/`).
  5. Builds Docker container image.
  6. Launches container locally in runner environment and runs `curl --fail /health` integration check.

---

### 4. `Dockerfile` & Kubernetes Manifests (M4)

#### `Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```
- **Base Image**: Uses standard minimal `python:3.11-slim` Linux image.
- **Optimization**: Installs dependencies with `--no-cache-dir` to minimize container size.
- **Entrypoint**: Relaunches FastAPI server on port 8000.

#### `k8s/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: botnet-detector-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: botnet-detector
  template:
    metadata:
      labels:
        app: botnet-detector
    spec:
      containers:
      - name: botnet-detector
        image: botnet-detector:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```
- **Replicas**: 2 pods for high availability and load balancing.
- **Probes**: Configures HTTP `/health` liveness and readiness checks to automatically restart failing pods.

---

### 5. `smoke_test.py` & `monitor.py` — Smoke Testing & Monitoring (M5)

#### `smoke_test.py`
```python
import sys, time, requests

API_URL = "http://localhost:8000"

def test_health():
    res = requests.get(f"{API_URL}/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    print("[OK] Health check passed")

def test_prediction():
    sample_flow = {
        "dur": 0.12, "proto": "tcp", "service": "-", "state": "FIN",
        "spkts": 6, "dpkts": 4, "sbytes": 258, "dbytes": 172, "rate": 74.08,
        "sttl": 252, "dttl": 254, "sload": 14158.94, "dload": 8495.36
    }
    res = requests.post(f"{API_URL}/predict", json=sample_flow)
    assert res.status_code == 200
    data = res.json()
    assert "prediction" in data
    print(f"[OK] Prediction passed: label={data['label']} prob={data['attack_probability']}")

if __name__ == "__main__":
    test_health()
    test_prediction()
```
- Programmatically sends HTTP requests to validate endpoint availability and verify correct payload structures during deployment verification.

---

## 🖥️ Launching via `setup.bat`

The root directory contains an interactive Windows launcher script `setup.bat`.

```cmd
setup.bat
```

### Menu Options Included:
1. **[1] Full Auto Pipeline**: Runs M1 through M5 sequentially.
2. **[2] M1 | Install Dependencies**: Installs `requirements.txt`.
3. **[3] M1 | Train Model**: Executes `train_model.py`.
4. **[4] M3 | Run Tests**: Runs `pytest tests/`.
5. **[5] M2 | Start API Locally**: Launches FastAPI uvicorn server.
6. **[6] M2 | Docker Build + Run**: Builds and starts Docker container.
7. **[7] M4 | Kubernetes Deploy**: Applies K8s manifests & port-forwards service.
8. **[8] M5 | Smoke Test + Monitor**: Runs load simulator & telemetry monitor.
9. **[9] M1 | MLflow Experiment Tracking**: Logs runs to MLflow.
10. **[10] Open API Docs**: Launches Swagger UI in browser (`/docs`).
11. **[11] Check GitHub Actions**: Displays status of remote CI/CD runs.
12. **[12] Check Prerequisites**: Audits system for Python, Docker, Git, and Dataset files.

---
*Documented and verified for repository: [github.com/Knight-Node64/Botnet-Detection](https://github.com/Knight-Node64/Botnet-Detection)*
