import time
import requests
import pandas as pd
import numpy as np

def run_monitoring_simulation(api_url="http://127.0.0.1:8000", sample_size=50):
    print(f"=== M5: Live Model Monitoring & Performance Tracking ===")
    print(f"Target Service: {api_url}")
    
    # 1. Fetch current metrics
    try:
        metrics_resp = requests.get(f"{api_url}/metrics", timeout=5).json()
        print(f"Initial API Operational Metrics: {metrics_resp}")
    except Exception as e:
        print(f"Could not connect to service metrics endpoint: {e}")
        return
        
    # 2. Simulate streaming request batch from test set
    test_path = "dataset/UNSW_NB15_testing-set.csv"
    df = pd.read_csv(test_path).sample(n=sample_size, random_state=123)
    
    latencies = []
    correct_predictions = 0
    
    print(f"\nSimulating {sample_size} real-time traffic flow requests...")
    for idx, row in df.iterrows():
        payload = {
            "dur": float(row['dur']), "proto": str(row['proto']), "service": str(row['service']),
            "state": str(row['state']), "spkts": int(row['spkts']), "dpkts": int(row['dpkts']),
            "sbytes": int(row['sbytes']), "dbytes": int(row['dbytes']), "rate": float(row['rate']),
            "sttl": int(row['sttl']), "dttl": int(row['dttl']), "sload": float(row['sload']),
            "dload": float(row['dload']), "sloss": int(row['sloss']), "dloss": int(row['dloss']),
            "sinpkt": float(row['sinpkt']), "dinpkt": float(row['dinpkt']), "sjit": float(row['sjit']),
            "djit": float(row['djit']), "swin": int(row['swin']), "stcpb": int(row['stcpb']),
            "dtcpb": int(row['dtcpb']), "dwin": int(row['dwin']), "tcprtt": float(row['tcprtt']),
            "synack": float(row['synack']), "ackdat": float(row['ackdat']), "smean": int(row['smean']),
            "dmean": int(row['dmean']), "trans_depth": int(row['trans_depth']),
            "response_body_len": int(row['response_body_len']), "ct_srv_src": int(row['ct_srv_src']),
            "ct_state_ttl": int(row['ct_state_ttl']), "ct_dst_ltm": int(row['ct_dst_ltm']),
            "ct_src_dport_ltm": int(row['ct_src_dport_ltm']), "ct_dst_sport_ltm": int(row['ct_dst_sport_ltm']),
            "ct_dst_src_ltm": int(row['ct_dst_src_ltm']), "is_ftp_login": int(row['is_ftp_login']),
            "ct_ftp_cmd": int(row['ct_ftp_cmd']), "ct_flw_http_mthd": int(row['ct_flw_http_mthd']),
            "ct_src_ltm": int(row['ct_src_ltm']), "ct_srv_dst": int(row['ct_srv_dst']),
            "is_sm_ips_ports": int(row['is_sm_ips_ports'])
        }
        
        t0 = time.time()
        resp = requests.post(f"{api_url}/predict", json=payload).json()
        latency = (time.time() - t0) * 1000.0
        latencies.append(latency)
        
        if resp['prediction'] == int(row['label']):
            correct_predictions += 1
            
    # 3. Post-deployment performance summary
    final_metrics = requests.get(f"{api_url}/metrics").json()
    batch_acc = (correct_predictions / sample_size) * 100.0
    avg_lat = np.mean(latencies)
    p95_lat = np.percentile(latencies, 95)
    
    print("\n================ MONITORING REPORT ================")
    print(f"Batch Requests Processed:  {sample_size}")
    print(f"Batch Model Accuracy:       {batch_acc:.2f}%")
    print(f"Average Request Latency:   {avg_lat:.2f} ms")
    print(f"95th Percentile Latency:   {p95_lat:.2f} ms")
    print(f"Cumulative API Total Requests: {final_metrics['total_requests']}")
    print(f"Cumulative Attacks Detected:   {final_metrics['attack_predictions']}")
    print(f"Cumulative Normal Flows:       {final_metrics['normal_predictions']}")
    print("===================================================")

if __name__ == "__main__":
    run_monitoring_simulation()
