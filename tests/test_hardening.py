"""Tests for API hardening: validation, error handling, and Prometheus metrics."""
import pytest
from fastapi.testclient import TestClient

from app import app, load_model

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_model():
    load_model()


VALID_FLOW = {
    "dur": 0.12, "proto": "tcp", "service": "-", "state": "FIN",
    "spkts": 6, "dpkts": 4, "sbytes": 258, "dbytes": 172, "rate": 74.08,
    "sttl": 252, "dttl": 254, "sload": 14158.94, "dload": 8495.36,
    "sloss": 0, "dloss": 0, "sinpkt": 24.29, "dinpkt": 8.37, "sjit": 30.17,
    "djit": 11.83, "swin": 255, "stcpb": 621772692, "dtcpb": 2202533631,
    "dwin": 255, "tcprtt": 0.0, "synack": 0.0, "ackdat": 0.0, "smean": 43,
    "dmean": 43, "trans_depth": 0, "response_body_len": 0, "ct_srv_src": 1,
    "ct_state_ttl": 0, "ct_dst_ltm": 1, "ct_src_dport_ltm": 1,
    "ct_dst_sport_ltm": 1, "ct_dst_src_ltm": 1, "is_ftp_login": 0,
    "ct_ftp_cmd": 0, "ct_flw_http_mthd": 0, "ct_src_ltm": 1,
    "ct_srv_dst": 1, "is_sm_ips_ports": 0,
}


def test_negative_field_rejected():
    payload = dict(VALID_FLOW)
    payload["sbytes"] = -100
    r = client.post("/predict", json=payload)
    assert r.status_code == 422


def test_wrong_type_rejected():
    payload = dict(VALID_FLOW)
    payload["spkts"] = "not_an_int"
    r = client.post("/predict", json=payload)
    assert r.status_code == 422


def test_unknown_category_falls_back_to_first_class():
    payload = dict(VALID_FLOW)
    payload["proto"] = "not_a_real_proto"
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    assert r.json()["label"] in ("Normal", "Attack")


def test_predict_returns_probability_bounds():
    r = client.post("/predict", json=VALID_FLOW)
    assert r.status_code == 200
    prob = r.json()["attack_probability"]
    assert 0.0 <= prob <= 1.0


def test_prometheus_metrics_endpoint():
    r = client.get("/metrics/prometheus")
    assert r.status_code == 200
    text = r.text
    assert "http_requests_total" in text or "http_request_duration_seconds" in text
    assert "text/plain" in r.headers["content-type"]
