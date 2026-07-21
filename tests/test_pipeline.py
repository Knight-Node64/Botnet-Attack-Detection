"""Tests for feature engineering and API endpoints."""
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from app import app, load_model

client = TestClient(app)

SAMPLE_FLOW = {
    "dur":0.12,"proto":"tcp","service":"-","state":"FIN","spkts":6,"dpkts":4,
    "sbytes":258,"dbytes":172,"rate":74.08,"sttl":252,"dttl":254,"sload":14158.94,
    "dload":8495.36,"sloss":0,"dloss":0,"sinpkt":24.29,"dinpkt":8.37,"sjit":30.17,
    "djit":11.83,"swin":255,"stcpb":621772692,"dtcpb":2202533631,"dwin":255,
    "tcprtt":0.0,"synack":0.0,"ackdat":0.0,"smean":43,"dmean":43,"trans_depth":0,
    "response_body_len":0,"ct_srv_src":1,"ct_state_ttl":0,"ct_dst_ltm":1,
    "ct_src_dport_ltm":1,"ct_dst_sport_ltm":1,"ct_dst_src_ltm":1,"is_ftp_login":0,
    "ct_ftp_cmd":0,"ct_flw_http_mthd":0,"ct_src_ltm":1,"ct_srv_dst":1,"is_sm_ips_ports":0,
}

@pytest.fixture(autouse=True)
def init_model():
    load_model()

# ── API Tests ──────────────────────────────────────────────────────────────────
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert "model_loaded" in r.json()

def test_predict():
    r = client.post("/predict", json=SAMPLE_FLOW)
    assert r.status_code == 200
    d = r.json()
    assert d["label"] in ["Normal", "Attack"]
    assert 0.0 <= d["attack_probability"] <= 1.0
    assert d["latency_ms"] >= 0

def test_metrics():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "total_requests" in r.json()

# ── Feature Engineering Tests ──────────────────────────────────────────────────
def test_feature_aggregations():
    df = pd.DataFrame([{"sbytes": 200, "dbytes": 100, "spkts": 5, "dpkts": 3,
                         "sttl": 64, "dttl": 128, "synack": 0.1, "ackdat": 0.05,
                         "dur": 1.0, "sload": 500.0, "dload": 200.0, "rate": 10.0}])
    from train_model import engineer_features
    out = engineer_features(df)
    assert out['total_bytes'].iloc[0] == 300
    assert out['total_pkts'].iloc[0]  == 8
    assert out['tcp_handshake_sum'].iloc[0] == pytest.approx(0.15)

def test_log_transform_non_negative():
    df = pd.DataFrame([{"sbytes": 0, "dbytes": 0, "spkts": 0, "dpkts": 0,
                         "sttl": 0, "dttl": 0, "synack": 0, "ackdat": 0,
                         "dur": 0, "sload": 0, "dload": 0, "rate": 0}])
    from train_model import engineer_features
    out = engineer_features(df)
    for col in out.columns:
        if col.startswith('log_'):
            assert out[col].iloc[0] >= 0, f"{col} is negative"

def test_ratios():
    df = pd.DataFrame([{"sbytes": 100, "dbytes": 50, "spkts": 4, "dpkts": 2,
                         "sttl": 64, "dttl": 64, "synack": 0, "ackdat": 0,
                         "dur": 1.0, "sload": 100.0, "dload": 50.0, "rate": 5.0}])
    from train_model import engineer_features
    out = engineer_features(df)
    assert abs(out['byte_ratio'].iloc[0] - 100/50.00001) < 0.01
    assert abs(out['pkt_ratio'].iloc[0]  - 4/2.00001)   < 0.01
