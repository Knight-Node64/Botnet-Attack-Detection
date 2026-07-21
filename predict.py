import os
import joblib
import pandas as pd
import numpy as np

def engineer_features(df):
    """
    Applies feature engineering on UNSW-NB15 dataframe.
    """
    df = df.copy()
    
    # 1. Total traffic volume aggregations
    df['total_bytes'] = df['sbytes'] + df['dbytes']
    df['total_pkts'] = df['spkts'] + df['dpkts']
    
    # 2. Packet size & symmetry ratios
    df['bytes_per_pkt_src'] = df['sbytes'] / (df['spkts'] + 1e-5)
    df['bytes_per_pkt_dst'] = df['dbytes'] / (df['dpkts'] + 1e-5)
    df['pkt_ratio'] = df['spkts'] / (df['dpkts'] + 1e-5)
    df['byte_ratio'] = df['sbytes'] / (df['dbytes'] + 1e-5)
    
    # 3. Latency & TCP interactions
    df['ttl_diff'] = np.abs(df['sttl'] - df['dttl'])
    df['tcp_handshake_sum'] = df['synack'] + df['ackdat']
    
    # 4. Log transformation for highly skewed features
    skewed_cols = ['dur', 'sbytes', 'dbytes', 'sload', 'dload', 'rate', 'spkts', 'dpkts', 'total_bytes', 'total_pkts']
    for col in skewed_cols:
        if col in df.columns:
            df[f'log_{col}'] = np.log1p(np.maximum(0, df[col]))
            
    return df

def run_predictions():
    model_path = os.path.join("models", "botnet_detector.joblib")
    test_path = os.path.join("dataset", "UNSW_NB15_testing-set.csv")
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}. Please run train_model.py first.")
        return
        
    print(f"Loading trained pipeline from: {model_path}")
    pipeline = joblib.load(model_path)
    
    model = pipeline['model']
    scaler = pipeline['scaler']
    encoders = pipeline['encoders']
    feature_names = pipeline['feature_names']
    
    print(f"Loading sample records from: {test_path}")
    test_df = pd.read_csv(test_path)
    
    # Take 5 samples (some normal, some attack)
    samples = test_df.sample(n=10, random_state=42).copy()
    y_true = samples['label'].values
    
    # Keep track of attack categories for output demonstration
    attack_cats = samples['attack_cat'].values if 'attack_cat' in samples.columns else None
    
    # Drop target columns
    drop_cols = ['id', 'attack_cat', 'label']
    X_samples = samples.drop(columns=[c for c in drop_cols if c in samples.columns])
    
    # Feature engineering
    X_samples = engineer_features(X_samples)
    
    # Encode categorical columns
    for col in ['proto', 'service', 'state']:
        le = encoders[col]
        # Handle unseen values by falling back to the first class or unknown class mapping if necessary
        X_samples[col] = X_samples[col].astype(str).map(
            lambda s: le.transform([s])[0] if s in le.classes_ else le.transform([le.classes_[0]])[0]
        )
        
    # Reorder columns to match the features used in fitting
    X_samples = X_samples[feature_names]
    
    # Scale numerical features
    X_samples_scaled = scaler.transform(X_samples)
    
    # Predict
    preds = model.predict(X_samples_scaled)
    probs = model.predict_proba(X_samples_scaled)[:, 1]
    
    print("\n--- Predictions on Random Test Samples ---")
    for i in range(len(samples)):
        true_label = "Attack" if y_true[i] == 1 else "Normal"
        pred_label = "Attack" if preds[i] == 1 else "Normal"
        cat = attack_cats[i] if attack_cats is not None else "N/A"
        print(f"Sample {i+1}: True={true_label} ({cat}), Predicted={pred_label} (Confidence={probs[i]*100:.2f}%)")

if __name__ == "__main__":
    run_predictions()
