import pytest
from fastapi.testclient import TestClient
from app import app, load_model

client = TestClient(app)

@pytest.fixture(autouse=True)
def init_model():
    load_model()

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data

def test_predict_endpoint():
    payload = {
        "dur": 0.121478,
        "proto": "tcp",
        "service": "-",
        "state": "FIN",
        "spkts": 6,
        "dpkts": 4,
        "sbytes": 258,
        "dbytes": 172,
        "rate": 74.08,
        "sttl": 252,
        "dttl": 254,
        "sload": 14158.94,
        "dload": 8495.36,
        "sloss": 0,
        "dloss": 0,
        "sinpkt": 24.29,
        "dinpkt": 8.37,
        "sjit": 30.17,
        "djit": 11.83,
        "swin": 255,
        "stcpb": 621772692,
        "dtcpb": 2202533631,
        "dwin": 255,
        "tcprtt": 0.0,
        "synack": 0.0,
        "ackdat": 0.0,
        "smean": 43,
        "dmean": 43,
        "trans_depth": 0,
        "response_body_len": 0,
        "ct_srv_src": 1,
        "ct_state_ttl": 0,
        "ct_dst_ltm": 1,
        "ct_src_dport_ltm": 1,
        "ct_dst_sport_ltm": 1,
        "ct_dst_src_ltm": 1,
        "is_ftp_login": 0,
        "ct_ftp_cmd": 0,
        "ct_flw_http_mthd": 0,
        "ct_src_ltm": 1,
        "ct_srv_dst": 1,
        "is_sm_ips_ports": 0
    }
    
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "label" in data
    assert data["label"] in ["Normal", "Attack"]
    assert "attack_probability" in data
    assert "latency_ms" in data

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "avg_latency_ms" in data
