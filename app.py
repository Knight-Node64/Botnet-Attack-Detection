"""
M2 - FastAPI inference service for botnet detection.
Endpoints: GET /health  POST /predict  GET /metrics  GET /metrics/prometheus
"""
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

MODEL_PATH = "models/botnet_detector.joblib"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("botnet_api")
    root.handlers[:] = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


setup_logging()
log = logging.getLogger("botnet_api")

pipeline: dict[str, Any] | None = None
stats: dict[str, float] = {"total": 0, "attacks": 0, "latency_ms": 0.0}


def load_model() -> None:
    global pipeline
    if os.path.exists(MODEL_PATH):
        pipeline = joblib.load(MODEL_PATH)
        meta = pipeline.get("metadata", {})
        log.info("Model loaded: %s (trained_at=%s)", meta.get("model_name"), meta.get("trained_at"))
    else:
        log.warning("Model not found at %s", MODEL_PATH)


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_model()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Botnet Attack Detection API",
    description="""
## Advanced Botnet Detection & MLOps Inference Service

This FastAPI service serves real-time botnet attack detection predictions trained on the **UNSW-NB15 dataset**.

### Core Functionality:
* **`/health`**: Verifies API service status and confirms whether the machine learning model (`botnet_detector.joblib`) is successfully loaded.
* **`/predict`**: Accepts raw network traffic flow features, applies feature engineering (ratios, aggregations, log transforms), and returns botnet attack classification with confidence probability.
* **`/metrics`**: Provides operational health telemetry including total requests processed, detected attack counts, and average inference latency.
* **`/metrics/prometheus`**: Prometheus-format metrics for scraping by monitoring stacks.
""",
    version="2.0.0",
    docs_url=None,
    redoc_url="/docs",
    redoc_options={
        "title": "Botnet Attack Detection API",
        "theme": {
            "colors": {
                "primary": {"main": "#3b82f6"},
                "success": {"main": "#10b981"},
                "error": {"main": "#f43f5e"},
                "text": {"primary": "#e2e8f0", "secondary": "#94a3b8"},
                "http": {
                    "get": "#3b82f6",
                    "post": "#10b981",
                    "put": "#f59e0b",
                    "delete": "#f43f5e",
                },
                "codeSample": {"backgroundColor": "#0b0f19"},
            },
            "typography": {
                "fontFamily": "'Plus Jakarta Sans', sans-serif",
                "fontSize": "14px",
                "headings": {"fontWeight": "700", "color": "#ffffff"},
                "code": {"fontFamily": "'Courier New', monospace", "fontSize": "13px"},
                "links": {"color": "#60a5fa"},
            },
            "sidebar": {
                "backgroundColor": "#111827",
                "textColor": "#94a3b8",
                "activeTextColor": "#3b82f6",
            },
            "rightPanel": {
                "backgroundColor": "#0b0f19",
                "textColor": "#e2e8f0",
            },
        },
    },
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics/prometheus", include_in_schema=False)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Request schema ─────────────────────────────────────────────────────────────
class Flow(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "dur":0.12,"proto":"tcp","service":"-","state":"FIN","spkts":6,"dpkts":4,
        "sbytes":258,"dbytes":172,"rate":74.08,"sttl":252,"dttl":254,"sload":14158.94,
        "dload":8495.36,"sloss":0,"dloss":0,"sinpkt":24.29,"dinpkt":8.37,"sjit":30.17,
        "djit":11.83,"swin":255,"stcpb":621772692,"dtcpb":2202533631,"dwin":255,
        "tcprtt":0.0,"synack":0.0,"ackdat":0.0,"smean":43,"dmean":43,"trans_depth":0,
        "response_body_len":0,"ct_srv_src":1,"ct_state_ttl":0,"ct_dst_ltm":1,
        "ct_src_dport_ltm":1,"ct_dst_sport_ltm":1,"ct_dst_src_ltm":1,"is_ftp_login":0,
        "ct_ftp_cmd":0,"ct_flw_http_mthd":0,"ct_src_ltm":1,"ct_srv_dst":1,"is_sm_ips_ports":0
    }]}}
    dur: float = Field(default=0.0, ge=0)
    proto: str = "tcp"
    service: str = "-"
    state: str = "FIN"
    spkts: int = Field(default=6, ge=0)
    dpkts: int = Field(default=4, ge=0)
    sbytes: int = Field(default=258, ge=0)
    dbytes: int = Field(default=172, ge=0)
    rate: float = Field(default=74.08, ge=0)
    sttl: int = Field(default=252, ge=0)
    dttl: int = Field(default=254, ge=0)
    sload: float = Field(default=14158.94, ge=0)
    dload: float = Field(default=8495.36, ge=0)
    sloss: int = Field(default=0, ge=0)
    dloss: int = Field(default=0, ge=0)
    sinpkt: float = Field(default=24.29, ge=0)
    dinpkt: float = Field(default=8.37, ge=0)
    sjit: float = Field(default=30.17, ge=0)
    djit: float = Field(default=11.83, ge=0)
    swin: int = Field(default=255, ge=0)
    stcpb: int = Field(default=621772692, ge=0)
    dtcpb: int = Field(default=2202533631, ge=0)
    dwin: int = Field(default=255, ge=0)
    tcprtt: float = Field(default=0.0, ge=0)
    synack: float = Field(default=0.0, ge=0)
    ackdat: float = Field(default=0.0, ge=0)
    smean: int = Field(default=43, ge=0)
    dmean: int = Field(default=43, ge=0)
    trans_depth: int = Field(default=0, ge=0)
    response_body_len: int = Field(default=0, ge=0)
    ct_srv_src: int = Field(default=1, ge=0)
    ct_state_ttl: int = Field(default=0, ge=0)
    ct_dst_ltm: int = Field(default=1, ge=0)
    ct_src_dport_ltm: int = Field(default=1, ge=0)
    ct_dst_sport_ltm: int = Field(default=1, ge=0)
    ct_dst_src_ltm: int = Field(default=1, ge=0)
    is_ftp_login: int = Field(default=0, ge=0)
    ct_ftp_cmd: int = Field(default=0, ge=0)
    ct_flw_http_mthd: int = Field(default=0, ge=0)
    ct_src_ltm: int = Field(default=1, ge=0)
    ct_srv_dst: int = Field(default=1, ge=0)
    is_sm_ips_ports: int = Field(default=0, ge=0)


# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get(
    "/health",
    tags=["System Status & Telemetry"],
    summary="Service & Model Health Status Check",
    description="""
Checks API operational status and model readiness.

**Returns:**
* `status`: `"healthy"` if model is loaded and API is operational, `"unhealthy"` otherwise.
* `model_loaded`: Boolean flag indicating if the model file is loaded into memory.
* `model_name`: Name of the active trained classifier (e.g. `RandomForestClassifier` or `XGBClassifier`).
"""
)
def health() -> dict[str, Any]:
    ok = pipeline is not None
    meta = pipeline.get("metadata", {}) if pipeline else {}
    return {
        "status": "healthy" if ok else "unhealthy",
        "model_loaded": ok,
        "model_name": meta.get("model_name") if ok else None,
    }


@app.post(
    "/predict",
    tags=["Model Inference"],
    summary="Predict Network Flow Botnet Attack",
    description="""
Performs real-time botnet classification on a network traffic flow payload.

**Preprocessing Pipeline:**
1. Derives packet/byte totals, packet ratios, TTL differences, and TCP handshake statistics.
2. Applies `log1p` transformations to skewed traffic features.
3. Encodes categorical variables (`proto`, `service`, `state`) and scales input using the trained `StandardScaler`.

**Returns:**
* `prediction`: `1` for Botnet Attack flow, `0` for Normal flow.
* `label`: String representation (`"Attack"` or `"Normal"`).
* `attack_probability`: Model confidence score between `0.0` and `1.0`.
* `latency_ms`: Feature engineering and inference runtime in milliseconds.
"""
)
def predict(flow: Flow) -> dict[str, Any]:
    if pipeline is None:
        raise HTTPException(503, "Model not loaded")
    t0 = time.time()
    df = pd.DataFrame([flow.model_dump()])
    model = pipeline["model"]
    pred = int(model.predict(df)[0])
    prob = float(model.predict_proba(df)[:, 1][0])
    ms = (time.time() - t0) * 1000
    stats["total"] += 1
    stats["latency_ms"] += ms
    if pred:
        stats["attacks"] += 1
    log.info("pred=%s prob=%.4f lat=%.1fms", pred, prob, ms)
    return {
        "prediction": pred,
        "label": "Attack" if pred else "Normal",
        "attack_probability": round(prob, 4),
        "latency_ms": round(ms, 2),
    }


@app.get(
    "/metrics",
    tags=["System Status & Telemetry"],
    summary="Operational Telemetry Summary",
    description="""
Returns operational monitoring metrics aggregated since API server startup.

**Returns:**
* `total_requests`: Total count of inference requests processed.
* `attacks_detected`: Count of traffic flows classified as botnet attacks.
* `normal_flows`: Count of legitimate network traffic flows.
* `avg_latency_ms`: Rolling average inference latency in milliseconds.
"""
)
def metrics() -> dict[str, Any]:
    t = stats["total"]
    return {
        "total_requests": int(t),
        "attacks_detected": int(stats["attacks"]),
        "normal_flows": int(t - stats["attacks"]),
        "avg_latency_ms": round(stats["latency_ms"] / t, 2) if t else 0.0,
    }
