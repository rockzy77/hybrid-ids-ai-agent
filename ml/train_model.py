import glob
import os
import random
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_OUT = os.path.join(os.path.dirname(__file__), "rf_model.joblib")
LABEL_ENCODER_OUT = os.path.join(os.path.dirname(__file__), "label_encoder.joblib")
FLAGGED_SAMPLE_OUT = os.path.join(os.path.dirname(__file__), "flagged_alerts_sample.csv")
LIVE_TRAFFIC_SAMPLE_OUT = os.path.join(os.path.dirname(__file__), "live_traffic_sample.csv")
FEATURE_COLUMNS_OUT = os.path.join(os.path.dirname(__file__), "feature_columns.json")
METRICS_OUT = os.path.join(os.path.dirname(__file__), "metrics.json")

RANDOM_STATE = 42
FLAGGED_SAMPLE_SIZE = 40  

PROTOCOL_NAMES = {0: "HOPOPT", 1: "ICMP", 6: "TCP", 17: "UDP"}


def protocol_display(value):
    try:
        return PROTOCOL_NAMES.get(int(value), str(value))
    except (TypeError, ValueError):
        return str(value)

TARGET_SAMPLES_PER_CLASS = 50_000


def load_dataset(data_dir: str) -> pd.DataFrame:
    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {data_dir}. Download the CICIDS2017 "
            "'MachineLearningCVE' CSVs (8 daily files) and place them there."
        )

    print(f"Found {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"  - {os.path.basename(f)}")

    frames = [pd.read_csv(f, low_memory=False) for f in csv_files]
    df = pd.concat(frames, ignore_index=True)

    df.columns = [c.strip() for c in df.columns]
    return df


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    initial_len = len(df)

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()

    df = df.drop_duplicates()

    print(f"Cleaned dataset: {initial_len} -> {len(df)} rows "
          f"({initial_len - len(df)} removed for NaN/inf/duplicates)")
    return df


def prepare_features_and_labels(df: pd.DataFrame):
    if "Label" not in df.columns:
        raise KeyError("Expected a 'Label' column in the dataset after stripping whitespace.")

    y_raw = df["Label"]
    X_full = df.drop(columns=["Label"])
    identifier_cols = [c for c in ["Source IP", "Destination IP", "Protocol"] if c in X_full.columns]
    identifiers = X_full[identifier_cols].copy() if identifier_cols else pd.DataFrame(index=X_full.index)
    X = X_full.select_dtypes(include=[np.number])

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    print(f"Label classes ({len(label_encoder.classes_)}): {list(label_encoder.classes_)}")
    return X, y, label_encoder, identifiers


def compute_binary_false_positive_rate(y_true, y_pred, label_encoder):
  
    benign_idx = list(label_encoder.classes_).index("BENIGN")

    y_true_binary = (y_true != benign_idx).astype(int)  
    y_pred_binary = (y_pred != benign_idx).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true_binary, y_pred_binary).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return fpr, (tn, fp, fn, tp)


def export_live_traffic_sample(X_test, y_test, label_encoder, id_test,
                                benign_sample_size=5000, attack_sample_size=500):
    
    rng = random.Random(RANDOM_STATE)
    true_labels = label_encoder.inverse_transform(y_test)

    benign_positions = [i for i, lbl in enumerate(true_labels) if lbl == "BENIGN"]
    attack_positions = [i for i, lbl in enumerate(true_labels) if lbl != "BENIGN"]

    benign_sample_size = min(benign_sample_size, len(benign_positions))
    attack_sample_size = min(attack_sample_size, len(attack_positions))

    sampled_positions = (
        rng.sample(benign_positions, benign_sample_size)
        + rng.sample(attack_positions, attack_sample_size)
    )
    rng.shuffle(sampled_positions) 

    base_time = datetime.now() - timedelta(hours=1)

    rows = []
    for i, pos in enumerate(sampled_positions):
        feature_row = X_test.iloc[pos].to_dict()
        id_row = id_test.iloc[pos]
        src_ip = id_row.get("Source IP") if "Source IP" in id_test.columns else None
        protocol = id_row.get("Protocol") if "Protocol" in id_test.columns else feature_row.get("Protocol")

        row = {
            "src_ip": src_ip if pd.notna(src_ip) else f"10.0.{rng.randint(0,20)}.{rng.randint(2,254)}",
            "dst_port": int(feature_row.get("Destination Port", rng.choice([22, 80, 443, 3389, 8080]))),
            "protocol_display": protocol_display(protocol) if pd.notna(protocol) else rng.choice(["TCP", "UDP"]),
            "timestamp": (base_time + timedelta(seconds=i * 20)).strftime("%Y-%m-%d %H:%M:%S"),
            "ground_truth_label": true_labels[pos],
        }
        row.update(feature_row)
        rows.append(row)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(LIVE_TRAFFIC_SAMPLE_OUT, index=False)
    n_benign = sum(1 for r in rows if r["ground_truth_label"] == "BENIGN")
    n_attack = len(rows) - n_benign
    print(f"Exported {len(out_df)} mixed live-traffic rows ({n_benign} benign, {n_attack} attack, "
          f"real feature vectors) to {LIVE_TRAFFIC_SAMPLE_OUT}")


def export_flagged_sample(X_test, y_pred, y_test_raw_labels, label_encoder, model, id_test):
  
    predicted_labels = label_encoder.inverse_transform(y_pred)
    probabilities = model.predict_proba(X_test)

    flagged_mask = predicted_labels != "BENIGN"
    flagged_indices = np.where(flagged_mask)[0]

    if len(flagged_indices) == 0:
        print("No attack predictions found in test set — nothing to export.")
        return

    sample_size = min(FLAGGED_SAMPLE_SIZE, len(flagged_indices))
    rng = random.Random(RANDOM_STATE)
    sampled_indices = rng.sample(list(flagged_indices), sample_size)

    rows = []
    base_time = datetime.now() - timedelta(hours=2)

    for i, idx in enumerate(sampled_indices):
        row = X_test.iloc[idx]
        predicted_label = predicted_labels[idx]
        confidence = float(np.max(probabilities[idx]))

        src_ip = id_test.iloc[idx].get("Source IP") if "Source IP" in id_test.columns else None
        dst_port = row.get("Destination Port", None)
        protocol = row.get("Protocol", None)

        rows.append({
            "src_ip": src_ip if pd.notna(src_ip) else f"10.0.{rng.randint(0,20)}.{rng.randint(2,254)}",
            "dst_port": int(dst_port) if pd.notna(dst_port) else rng.choice([22, 80, 443, 3389, 8080]),
            "protocol": protocol_display(protocol) if pd.notna(protocol) else rng.choice(["TCP", "UDP"]),
            "label": predicted_label,
            "confidence": round(confidence, 4),
            "timestamp": (base_time + timedelta(seconds=i * 20)).strftime("%Y-%m-%d %H:%M:%S"),
        })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(FLAGGED_SAMPLE_OUT, index=False)
    print(f"Exported {len(out_df)} flagged alerts to {FLAGGED_SAMPLE_OUT}")


def main():
    df = load_dataset(DATA_DIR)
    df = clean_dataset(df)

    X, y, label_encoder, identifiers = prepare_features_and_labels(df)

    X_train, X_test, y_train, y_test, id_train, id_test = train_test_split(
        X, y, identifiers, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )

    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")

    class_counts = pd.Series(y_train).value_counts()
    print("\nClass counts before balancing (training set only):")
    for cls_idx, count in class_counts.items():
        print(f"  {label_encoder.classes_[cls_idx]}: {count}")

    under_strategy = {
        cls: TARGET_SAMPLES_PER_CLASS
        for cls, count in class_counts.items()
        if count > TARGET_SAMPLES_PER_CLASS
    }
    over_strategy = {
        cls: TARGET_SAMPLES_PER_CLASS
        for cls, count in class_counts.items()
        if count < TARGET_SAMPLES_PER_CLASS
    }

    smallest_minority_count = min(
        (class_counts[cls] for cls in over_strategy), default=6
    )
    safe_k_neighbors = max(1, min(5, smallest_minority_count - 1))
    if safe_k_neighbors < 5:
        print(f"NOTE: smallest minority class has only {smallest_minority_count} "
              f"training rows — reducing SMOTE k_neighbors to {safe_k_neighbors} "
              "for that class to avoid an error.")

    print(f"\nBalancing all classes to {TARGET_SAMPLES_PER_CLASS} rows each "
          f"({len(under_strategy)} classes undersampled, {len(over_strategy)} oversampled)...")

    steps = []
    if under_strategy:
        steps.append(("under", RandomUnderSampler(sampling_strategy=under_strategy, random_state=RANDOM_STATE)))
    if over_strategy:
        steps.append(("over", SMOTE(sampling_strategy=over_strategy, k_neighbors=safe_k_neighbors, random_state=RANDOM_STATE)))

    if steps:
        balancer = ImbPipeline(steps)
        X_train_resampled, y_train_resampled = balancer.fit_resample(X_train, y_train)
    else:
        X_train_resampled, y_train_resampled = X_train, y_train

    print(f"Training set after balancing: {len(X_train_resampled)} rows")

    print("Training Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        n_jobs=-1,
        random_state=RANDOM_STATE,
        class_weight=None,  
    )
    model.fit(X_train_resampled, y_train_resampled)

    print("Evaluating on held-out test set...")
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    fpr, confusion_counts = compute_binary_false_positive_rate(y_test, y_pred, label_encoder)

    print("\n=== Evaluation Results ===")
    print(f"Accuracy:            {accuracy:.4f}")
    print(f"Precision (weighted): {precision:.4f}")
    print(f"Recall (weighted):    {recall:.4f}")
    print(f"F1-score (weighted):  {f1:.4f}")
    print(f"False Positive Rate (binary attack-vs-benign): {fpr:.4f}")
    tn, fp, fn, tp = confusion_counts
    print(f"  TN={tn}  FP={fp}  FN={fn}  TP={tp}")

    joblib.dump(model, MODEL_OUT)
    joblib.dump(label_encoder, LABEL_ENCODER_OUT)
    print(f"\nSaved model to {MODEL_OUT}")
    print(f"Saved label encoder to {LABEL_ENCODER_OUT}")

    import json
    with open(METRICS_OUT, "w") as f:
        json.dump({
            "accuracy": round(float(accuracy), 4),
            "precision_weighted": round(float(precision), 4),
            "recall_weighted": round(float(recall), 4),
            "f1_weighted": round(float(f1), 4),
            "false_positive_rate": round(float(fpr), 4),
            "confusion_binary": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        }, f, indent=2)
    print(f"Saved metrics to {METRICS_OUT}")

    with open(FEATURE_COLUMNS_OUT, "w") as f:
        json.dump(list(X.columns), f, indent=2)
    print(f"Saved feature column order to {FEATURE_COLUMNS_OUT}")

    export_flagged_sample(X_test, y_pred, y_test, label_encoder, model, id_test)
    export_live_traffic_sample(X_test, y_test, label_encoder, id_test,
                                benign_sample_size=3000, attack_sample_size=40)


if __name__ == "__main__":
    main()