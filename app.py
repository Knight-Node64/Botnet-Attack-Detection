"""
M2 – FastAPI inference service for botnet detection.
Endpoints: GET /health  POST /predict  GET /metrics
"""
import os, time, logging
import numpy as np, pandas as pd, joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("botnet_api")

app = FastAPI(title="Botnet Detection API", version="1.0")

MODEL_PATH = "models/botnet_detector.joblib"
pipeline   = None
stats      = {"total": 0, "attacks": 0, "latency_ms": 0.0}

@app.on_event("startup")
def load_model():
    global pipeline
    if os.path.exists(MODEL_PATH):
        pipeline = joblib.load(MODEL_PATH)
        log.info("Model loaded: %s", pipeline['model_name'])
    else:
        log.warning("Model not found at %s", MODEL_PATH)

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
@app.get("/health")
def health():
    ok = pipeline is not None
    return {"status": "healthy" if ok else "unhealthy",
            "model_loaded": ok,
            "model_name": pipeline['model_name'] if ok else None}

@app.post("/predict")
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

@app.get("/metrics")
def metrics():
    t = stats["total"]
    return {"total_requests": t, "attacks_detected": stats["attacks"],
            "normal_flows": t - stats["attacks"],
            "avg_latency_ms": round(stats["latency_ms"] / t, 2) if t else 0.0}
