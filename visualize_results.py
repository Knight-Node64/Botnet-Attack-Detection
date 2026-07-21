import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, roc_curve, auc, accuracy_score, precision_score, recall_score, f1_score

def generate_plots():
    model_path = os.path.join("models", "botnet_detector.joblib")
    test_path = os.path.join("dataset", "UNSW_NB15_testing-set.csv")
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}.")
        return
        
    print("Loading model and dataset...")
    pipeline = joblib.load(model_path)
    model = pipeline['model']
    scaler = pipeline['scaler']
    encoders = pipeline['encoders']
    feature_names = pipeline['feature_names']
    
    test_df = pd.read_csv(test_path)
    y_test = test_df['label']
    
    # Preprocess test set to get features matching fitted model
    df_temp = test_df.drop(columns=[c for c in ['id', 'attack_cat', 'label'] if c in test_df.columns])
    
    # Feature engineering (must match train_model.py exactly)
    df_temp['total_bytes'] = df_temp['sbytes'] + df_temp['dbytes']
    df_temp['total_pkts'] = df_temp['spkts'] + df_temp['dpkts']
    df_temp['bytes_per_pkt_src'] = df_temp['sbytes'] / (df_temp['spkts'] + 1e-5)
    df_temp['bytes_per_pkt_dst'] = df_temp['dbytes'] / (df_temp['dpkts'] + 1e-5)
    df_temp['pkt_ratio'] = df_temp['spkts'] / (df_temp['dpkts'] + 1e-5)
    df_temp['byte_ratio'] = df_temp['sbytes'] / (df_temp['dbytes'] + 1e-5)
    df_temp['ttl_diff'] = np.abs(df_temp['sttl'] - df_temp['dttl'])
    df_temp['tcp_handshake_sum'] = df_temp['synack'] + df_temp['ackdat']
    
    skewed_cols = ['dur', 'sbytes', 'dbytes', 'sload', 'dload', 'rate', 'spkts', 'dpkts', 'total_bytes', 'total_pkts']
    for col in skewed_cols:
        df_temp[f'log_{col}'] = np.log1p(np.maximum(0, df_temp[col]))
        
    for col in ['proto', 'service', 'state']:
        le = encoders[col]
        df_temp[col] = df_temp[col].astype(str).map(
            lambda s: le.transform([s])[0] if s in le.classes_ else le.transform([le.classes_[0]])[0]
        )
        
    X_test = df_temp[feature_names]
    X_test_scaled = scaler.transform(X_test)
    
    print("Generating predictions...")
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    # Calculate performance metrics
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    print("\n--- Model Performance Metrics ---")
    print(f"Accuracy:  {acc:.4f} ({acc*100:.2f}%)")
    print(f"Precision: {prec:.4f} ({prec*100:.2f}%)")
    print(f"Recall:    {rec:.4f} ({rec*100:.2f}%)")
    print(f"F1-Score:  {f1:.4f} ({f1*100:.2f}%)")
    
    # Create directory for plots
    os.makedirs("presentation_assets", exist_ok=True)
    
    # 1. Confusion Matrix Plot
    print("\nGenerating Confusion Matrix Plot...")
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Normal', 'Attack'], yticklabels=['Normal', 'Attack'])
    
    # Overlay the metrics on the confusion matrix plot
    stats_text = f"Accuracy: {acc*100:.2f}%\nPrecision: {prec*100:.2f}%\nRecall: {rec*100:.2f}%\nF1-Score: {f1*100:.2f}%"
    plt.text(0.5, -0.15, stats_text, ha='center', va='center', transform=plt.gca().transAxes,
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', alpha=0.9),
             fontsize=10, family='sans-serif')
             
    plt.title('Confusion Matrix - Botnet Detection', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Predicted Label', fontsize=12)
    plt.ylabel('True Label', fontsize=12)
    plt.tight_layout()
    cm_path = os.path.join("presentation_assets", "confusion_matrix.png")
    plt.savefig(cm_path, dpi=300)
    plt.close()
    
    # 2. ROC Curve Plot
    print("Generating ROC Curve Plot...")
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    roc_auc = auc(fpr, tpr)
    plt.figure(figsize=(7, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2.5, label=f'ROC Curve (AUC = {roc_auc:.4f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=1.5, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.title('Receiver Operating Characteristic (ROC)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('False Positive Rate', fontsize=12)
    plt.ylabel('True Positive Rate', fontsize=12)
    plt.legend(loc="lower right", fontsize=11)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    roc_path = os.path.join("presentation_assets", "roc_curve.png")
    plt.savefig(roc_path, dpi=300)
    plt.close()
    
    # 3. Feature Importance Plot
    print("Generating Feature Importance Plot...")
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    top_n = 15
    
    plt.figure(figsize=(10, 6))
    sns.barplot(
        x=importances[indices[:top_n]], 
        y=[feature_names[i] for i in indices[:top_n]], 
        palette="viridis",
        hue=[feature_names[i] for i in indices[:top_n]],
        legend=False
    )
    plt.title(f'Top {top_n} Feature Importances', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Relative Importance Value', fontsize=12)
    plt.ylabel('Features', fontsize=12)
    plt.grid(True, axis='x', linestyle=':', alpha=0.6)
    plt.tight_layout()
    importance_path = os.path.join("presentation_assets", "feature_importances.png")
    plt.savefig(importance_path, dpi=300)
    plt.close()
    
    print("\nAll presentation assets successfully saved to the 'presentation_assets/' directory:")
    print(f"  - Confusion Matrix: {cm_path}")
    print(f"  - ROC Curve: {roc_path}")
    print(f"  - Feature Importances: {importance_path}")

if __name__ == "__main__":
    generate_plots()
