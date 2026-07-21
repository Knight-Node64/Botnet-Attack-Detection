import pytest
import pandas as pd
import numpy as np
from train_model import engineer_features

def test_engineer_features_total_bytes_and_pkts():
    df_sample = pd.DataFrame([{
        'sbytes': 100, 'dbytes': 200,
        'spkts': 5, 'dpkts': 10,
        'sttl': 64, 'dttl': 60,
        'synack': 0.1, 'ackdat': 0.2,
        'dur': 1.0, 'sload': 1000.0, 'dload': 2000.0, 'rate': 15.0
    }])
    
    df_out = engineer_features(df_sample)
    
    assert 'total_bytes' in df_out.columns
    assert df_out['total_bytes'].iloc[0] == 300
    
    assert 'total_pkts' in df_out.columns
    assert df_out['total_pkts'].iloc[0] == 15

def test_engineer_features_ratios_and_ttl():
    df_sample = pd.DataFrame([{
        'sbytes': 100, 'dbytes': 200,
        'spkts': 5, 'dpkts': 10,
        'sttl': 252, 'dttl': 254,
        'synack': 0.05, 'ackdat': 0.05,
        'dur': 0.5, 'sload': 500.0, 'dload': 1000.0, 'rate': 20.0
    }])
    
    df_out = engineer_features(df_sample)
    
    assert 'ttl_diff' in df_out.columns
    assert df_out['ttl_diff'].iloc[0] == 2
    
    assert 'tcp_handshake_sum' in df_out.columns
    assert pytest.approx(df_out['tcp_handshake_sum'].iloc[0], 0.001) == 0.10

def test_log_transformations():
    df_sample = pd.DataFrame([{
        'sbytes': 100, 'dbytes': 200,
        'spkts': 5, 'dpkts': 10,
        'sttl': 64, 'dttl': 64,
        'synack': 0, 'ackdat': 0,
        'dur': 1.0, 'sload': 100.0, 'dload': 200.0, 'rate': 10.0
    }])
    
    df_out = engineer_features(df_sample)
    
    assert 'log_sbytes' in df_out.columns
    assert pytest.approx(df_out['log_sbytes'].iloc[0], 0.01) == np.log1p(100)
