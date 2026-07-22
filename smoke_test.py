"""
M4/M5 – Post-deployment smoke test & monitoring simulation.
Usage:
  python smoke_test.py               # smoke test (needs API running)
  python smoke_test.py --monitor     # live monitoring batch
"""
import sys, time
import numpy as np
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"

SAMPLE = {
    "dur":0.12,"proto":"tcp","service":"-","state":"FIN","spkts":6,"dpkts":4,
    "sbytes":258,"dbytes":172,"rate":74.08,"sttl":252,"dttl":254,"sload":14158.94,
    "dload":8495.36,"sloss":0,"dloss":0,"sinpkt":24.29,"dinpkt":8.37,"sjit":30.17,
    "djit":11.83,"swin":255,"stcpb":621772692,"dtcpb":2202533631,"dwin":255,
    "tcprtt":0.0,"synack":0.0,"ackdat":0.0,"smean":43,"dmean":43,"trans_depth":0,
    "response_body_len":0,"ct_srv_src":1,"ct_state_ttl":0,"ct_dst_ltm":1,
    "ct_src_dport_ltm":1,"ct_dst_sport_ltm":1,"ct_dst_src_ltm":1,"is_ftp_login":0,
    "ct_ftp_cmd":0,"ct_flw_http_mthd":0,"ct_src_ltm":1,"ct_srv_dst":1,"is_sm_ips_ports":0,
}

def check_server():
    try:
        r = requests.get(f"{BASE}/health", timeout=3)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False

def smoke_test():
    if not check_server():
        print(f"[ERROR] API server is not running on {BASE}")
        print("        Start the API first via setup.bat (Option [5] or [6]) or run:")
        print("        python -m uvicorn app:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    print(f"Smoke test -> {BASE}")
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200 and r.json()["model_loaded"], "Health check failed"
    print("[OK] /health")
    r = requests.post(f"{BASE}/predict", json=SAMPLE, timeout=5)
    assert r.status_code == 200, "Predict failed"
    d = r.json()
    print(f"[OK] /predict  label={d['label']}  prob={d['attack_probability']}")
    r = requests.get(f"{BASE}/metrics", timeout=5)
    assert r.status_code == 200, "Metrics failed"
    print("[OK] /metrics")
    print("All smoke tests passed!")

def monitor(n=50):
    if not check_server():
        print(f"[ERROR] API server is not running on {BASE}")
        print("        Start the API first via setup.bat (Option [5] or [6]) or run:")
        print("        python -m uvicorn app:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    import pandas as pd
    df   = pd.read_csv("dataset/UNSW_NB15_testing-set.csv").sample(n, random_state=42)
    lats, correct = [], 0
    for _, row in df.iterrows():
        payload = {k: (float(v) if isinstance(v, float) else
                      (int(v) if isinstance(v, (int, np.integer)) else str(v)))
                   for k, v in row.items() if k not in ['id','attack_cat','label']}
        t0 = time.time()
        resp = requests.post(f"{BASE}/predict", json=payload).json()
        lats.append((time.time()-t0)*1000)
        if resp['prediction'] == int(row['label']): correct += 1
    m = requests.get(f"{BASE}/metrics").json()
    print(f"\n{'='*48}")
    print(f"Batch size : {n}")
    print(f"Accuracy   : {correct/n*100:.1f}%")
    print(f"Avg latency: {np.mean(lats):.1f}ms   P95: {np.percentile(lats,95):.1f}ms")
    print(f"API totals : {m['total_requests']} req | {m['attacks_detected']} attacks")
    print(f"{'='*48}")

if __name__ == "__main__":
    if "--monitor" in sys.argv:
        monitor()
    else:
        smoke_test()
