"""
M2 – FastAPI inference service for botnet detection.
Endpoints: GET /health  POST /predict  GET /metrics
"""
import os, time, logging
import numpy as np, pandas as pd, joblib
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("botnet_api")

MODEL_PATH = "models/botnet_detector.joblib"
pipeline   = None
stats      = {"total": 0, "attacks": 0, "latency_ms": 0.0}

def load_model():
    global pipeline
    if os.path.exists(MODEL_PATH):
        pipeline = joblib.load(MODEL_PATH)
        log.info("Model loaded: %s", pipeline['model_name'])
    else:
        log.warning("Model not found at %s", MODEL_PATH)

@asynccontextmanager
async def lifespan(app: FastAPI):
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
""",
    version="1.0.0",
    docs_url=None,
    redoc_url=None
)

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
    dur:float=0.0; proto:str="tcp"; service:str="-"; state:str="FIN"
    spkts:int=6; dpkts:int=4; sbytes:int=258; dbytes:int=172; rate:float=74.08
    sttl:int=252; dttl:int=254; sload:float=14158.94; dload:float=8495.36
    sloss:int=0; dloss:int=0; sinpkt:float=24.29; dinpkt:float=8.37
    sjit:float=30.17; djit:float=11.83; swin:int=255; stcpb:int=621772692
    dtcpb:int=2202533631; dwin:int=255; tcprtt:float=0.0; synack:float=0.0
    ackdat:float=0.0; smean:int=43; dmean:int=43; trans_depth:int=0
    response_body_len:int=0; ct_srv_src:int=1; ct_state_ttl:int=0; ct_dst_ltm:int=1
    ct_src_dport_ltm:int=1; ct_dst_sport_ltm:int=1; ct_dst_src_ltm:int=1
    is_ftp_login:int=0; ct_ftp_cmd:int=0; ct_flw_http_mthd:int=0
    ct_src_ltm:int=1; ct_srv_dst:int=1; is_sm_ips_ports:int=0

def _preprocess(data: dict) -> np.ndarray:
    df = pd.DataFrame([data])
    df['total_bytes']       = df['sbytes'] + df['dbytes']
    df['total_pkts']        = df['spkts']  + df['dpkts']
    df['bytes_per_pkt_src'] = df['sbytes'] / (df['spkts'] + 1e-5)
    df['bytes_per_pkt_dst'] = df['dbytes'] / (df['dpkts'] + 1e-5)
    df['pkt_ratio']         = df['spkts']  / (df['dpkts'] + 1e-5)
    df['byte_ratio']        = df['sbytes'] / (df['dbytes'] + 1e-5)
    df['ttl_diff']          = np.abs(df['sttl'] - df['dttl'])
    df['tcp_handshake_sum'] = df['synack'] + df['ackdat']
    for col in ['dur','sbytes','dbytes','sload','dload','rate','spkts','dpkts','total_bytes','total_pkts']:
        df[f'log_{col}'] = np.log1p(np.maximum(0, df[col]))
    for col in ['proto','service','state']:
        le, v = pipeline['encoders'][col], str(df[col].values[0])
        df[col] = le.transform([v])[0] if v in le.classes_ else le.transform([le.classes_[0]])[0]
    return pipeline['scaler'].transform(df[pipeline['feature_names']])

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
def health():
    ok = pipeline is not None
    return {"status": "healthy" if ok else "unhealthy",
            "model_loaded": ok,
            "model_name": pipeline['model_name'] if ok else None}

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
def predict(flow: Flow):
    if pipeline is None:
        raise HTTPException(503, "Model not loaded")
    t0 = time.time()
    X  = _preprocess(flow.model_dump())
    pred = int(pipeline['model'].predict(X)[0])
    prob = float(pipeline['model'].predict_proba(X)[0, 1])
    ms   = (time.time() - t0) * 1000
    stats["total"] += 1; stats["latency_ms"] += ms
    if pred: stats["attacks"] += 1
    log.info("pred=%s prob=%.4f lat=%.1fms", pred, prob, ms)
    return {"prediction": pred, "label": "Attack" if pred else "Normal",
            "attack_probability": round(prob, 4), "latency_ms": round(ms, 2)}

@app.get(
    "/metrics",
    tags=["System Status & Telemetry"],
    summary="Prometheus & Monitoring Telemetry Metrics",
    description="""
Returns operational monitoring metrics aggregated since API server startup.

**Returns:**
* `total_requests`: Total count of inference requests processed.
* `attacks_detected`: Count of traffic flows classified as botnet attacks.
* `normal_flows`: Count of legitimate network traffic flows.
* `avg_latency_ms`: Rolling average inference latency in milliseconds.
"""
)
def metrics():
    t = stats["total"]
    return {"total_requests": t, "attacks_detected": stats["attacks"],
            "normal_flows": t - stats["attacks"],
            "avg_latency_ms": round(stats["latency_ms"] / t, 2) if t else 0.0}

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Botnet Attack Detection API - Documentation</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" />
        <style>
            /* Base dark theme & typography */
            body {
                background-color: #0b0f19 !important;
                color: #e2e8f0 !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
                margin: 0;
            }
            
            /* Header / Brand block customization */
            .swagger-ui .topbar {
                background-color: #111827 !important;
                border-bottom: 1px solid #1f2937 !important;
                padding: 12px 0;
            }
            .swagger-ui .topbar .download-url-wrapper {
                display: none !important;
            }
            .swagger-ui .topbar-wrapper a span {
                color: #3b82f6 !important;
                font-weight: 700 !important;
            }
            
            /* Info Section */
            .swagger-ui .info {
                margin: 40px 0 20px 0 !important;
            }
            .swagger-ui .info .title {
                color: #ffffff !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
                font-weight: 700 !important;
                font-size: 32px !important;
                background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px !important;
            }
            .swagger-ui .info p, .swagger-ui .info li, .swagger-ui .info td, .swagger-ui .info a {
                color: #94a3b8 !important;
                font-size: 14px !important;
                line-height: 1.6 !important;
            }
            .swagger-ui .info a {
                color: #60a5fa !important;
                text-decoration: none;
            }
            .swagger-ui .info a:hover {
                text-decoration: underline;
            }
            .swagger-ui .info h2 {
                color: #f1f5f9 !important;
                font-size: 20px !important;
                margin-top: 20px !important;
                border-bottom: 1px solid #1f2937;
                padding-bottom: 8px;
            }
            
            /* Schematic container & select boxes */
            .swagger-ui .scheme-container {
                background-color: #111827 !important;
                box-shadow: none !important;
                border: 1px solid #1f2937 !important;
                border-radius: 12px !important;
                padding: 20px !important;
                margin: 20px 0 !important;
            }
            .swagger-ui .schemes-title {
                color: #f1f5f9 !important;
            }
            .swagger-ui select {
                background-color: #1f2937 !important;
                color: #f1f5f9 !important;
                border: 1px solid #374151 !important;
                border-radius: 6px !important;
                padding: 5px 10px !important;
            }
            
            /* Tag / Section headers */
            .swagger-ui .opblock-tag-section {
                background: #111827 !important;
                border: 1px solid #1f2937 !important;
                border-radius: 12px !important;
                margin-bottom: 20px !important;
                overflow: hidden;
            }
            .swagger-ui .opblock-tag {
                background: #1f2937 !important;
                color: #f8fafc !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
                font-weight: 600 !important;
                font-size: 18px !important;
                border-bottom: 1px solid #1f2937 !important;
                padding: 15px 20px !important;
                margin: 0 !important;
            }
            .swagger-ui .opblock-tag small {
                color: #94a3b8 !important;
                font-weight: 400;
            }
            
            /* Operations / Endpoints */
            .swagger-ui .opblock {
                border-radius: 8px !important;
                margin: 10px 15px !important;
                box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
                background-color: #182235 !important;
            }
            
            /* GET block */
            .swagger-ui .opblock.opblock-get {
                background: rgba(59, 130, 246, 0.08) !important;
                border: 1px solid rgba(59, 130, 246, 0.3) !important;
            }
            .swagger-ui .opblock.opblock-get .opblock-summary-method {
                background: #3b82f6 !important;
                border-radius: 6px !important;
                font-weight: 600 !important;
            }
            
            /* POST block */
            .swagger-ui .opblock.opblock-post {
                background: rgba(16, 185, 129, 0.08) !important;
                border: 1px solid rgba(16, 185, 129, 0.3) !important;
            }
            .swagger-ui .opblock.opblock-post .opblock-summary-method {
                background: #10b981 !important;
                border-radius: 6px !important;
                font-weight: 600 !important;
            }
            
            /* Summary Text */
            .swagger-ui .opblock .opblock-summary-path {
                color: #f1f5f9 !important;
                font-weight: 600 !important;
            }
            .swagger-ui .opblock .opblock-summary-description {
                color: #94a3b8 !important;
            }
            .swagger-ui .opblock .opblock-summary-operation-id {
                color: #64748b !important;
            }
            
            /* Section Headers inside block */
            .swagger-ui .opblock .opblock-section-header {
                background: #111827 !important;
                border-bottom: 1px solid #1f2937 !important;
                color: #ffffff !important;
                padding: 10px 20px !important;
            }
            .swagger-ui .opblock .opblock-section-header h4 {
                color: #ffffff !important;
            }
            
            /* Parameters, tables & responses */
            .swagger-ui table thead tr td, .swagger-ui table thead tr th {
                color: #94a3b8 !important;
                border-bottom: 1px solid #1f2937 !important;
            }
            .swagger-ui .parameters-col_name {
                color: #f1f5f9 !important;
            }
            .swagger-ui .parameter__name {
                color: #60a5fa !important;
            }
            .swagger-ui .parameter__type {
                color: #a78bfa !important;
            }
            .swagger-ui .parameter__in {
                color: #f43f5e !important;
            }
            .swagger-ui .response-col_status {
                color: #f1f5f9 !important;
            }
            .swagger-ui .response-col_description {
                color: #e2e8f0 !important;
            }
            
            /* Interactive inputs & buttons */
            .swagger-ui input[type=text] {
                background-color: #111827 !important;
                color: #f1f5f9 !important;
                border: 1px solid #374151 !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
            }
            .swagger-ui textarea {
                background-color: #111827 !important;
                color: #f1f5f9 !important;
                border: 1px solid #374151 !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
            }
            .swagger-ui .btn {
                background: #1f2937 !important;
                color: #f1f5f9 !important;
                border: 1px solid #374151 !important;
                border-radius: 6px !important;
                transition: all 0.2s ease;
            }
            .swagger-ui .btn:hover {
                background: #374151 !important;
            }
            .swagger-ui .btn.execute {
                background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
                border: none !important;
                color: white !important;
                font-weight: 600 !important;
            }
            .swagger-ui .btn.execute:hover {
                background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%) !important;
            }
            
            /* Responses & JSON syntax highlighting */
            .swagger-ui .microsite {
                background-color: #111827 !important;
            }
            .swagger-ui pre {
                background-color: #0b0f19 !important;
                border: 1px solid #1f2937 !important;
                border-radius: 8px !important;
                color: #e2e8f0 !important;
            }
            .swagger-ui code {
                font-family: 'Courier New', Courier, monospace !important;
            }
            .swagger-ui .model-box {
                background-color: #111827 !important;
                border: 1px solid #1f2937 !important;
                border-radius: 8px !important;
                padding: 10px !important;
            }
            .swagger-ui .model-title {
                color: #f1f5f9 !important;
            }
            .swagger-ui .model {
                color: #94a3b8 !important;
            }
            .swagger-ui .prop-name {
                color: #60a5fa !important;
            }
            .swagger-ui .prop-type {
                color: #a78bfa !important;
            }
            
            /* Tab buttons */
            .swagger-ui .tabli button {
                color: #94a3b8 !important;
                font-weight: 500 !important;
            }
            .swagger-ui .tabli.active button {
                color: #3b82f6 !important;
                font-weight: 700 !important;
            }
            
            /* Live response block */
            .swagger-ui .responses-wrapper {
                background: #111827 !important;
                padding: 15px !important;
                border-radius: 8px !important;
            }
            .swagger-ui .live-responses-table {
                background: transparent !important;
            }
            
            /* Copy to clipboard button */
            .swagger-ui .copy-to-clipboard {
                background-color: #1f2937 !important;
                border-radius: 4px !important;
            }
            
            /* Hide unused elements */
            .swagger-ui .info .title .version {
                background-color: #2563eb !important;
                color: white !important;
                font-size: 12px !important;
                border-radius: 9999px !important;
                padding: 4px 10px !important;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js" charset="UTF-8"></script>
        <script>
            window.onload = () => {
                window.ui = SwaggerUIBundle({
                    url: '/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.presets.swaggerUiConfig
                    ],
                    layout: "BaseLayout",
                    deepLinking: true,
                    showExtensions: true,
                    showCommonExtensions: true,
                    defaultModelsExpandDepth: -1
                });
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
