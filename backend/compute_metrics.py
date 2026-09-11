import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", ".env"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hybrid_ids"),
}


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT ground_truth_label, agent_verdict, label AS rf_predicted_label
        FROM alerts
        WHERE reasoning_status = 'complete'
          AND ground_truth_label IS NOT NULL
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    n = len(rows)
    if n == 0:
        print("No completed alerts with ground truth yet. Let the Live Feed run for a "
              "while (or hit /api/traffic/next repeatedly) so RF flags some traffic and "
              "the agent finishes triaging it, then re-run this script.")
        return

    tp = fp = fn = tn = 0
    for r in rows:
        is_benign = r["ground_truth_label"] == "BENIGN"
        escalated = r["agent_verdict"] == "true_positive"
        if not is_benign and escalated:
            tp += 1
        elif is_benign and escalated:
            fp += 1
        elif not is_benign and not escalated:
            fn += 1
        else:
            tn += 1

    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print(f"n = {n} completed alerts with ground truth")
    print()
    print(f"{'':18s}{'Escalated (TP-ish)':22s}{'Dismissed (FP-ish)':22s}")
    print(f"{'Actual Attack':18s}{tp:<22d}{fn:<22d}")
    print(f"{'Actual Benign':18s}{fp:<22d}{tn:<22d}")
    print()
    print(f"Accuracy:            {accuracy:.2%}")
    print(f"Precision:            {precision:.2%}")
    print(f"Recall:               {recall:.2%}")
    print(f"F1-score:             {f1:.2%}")
    print(f"False Positive Rate:  {fpr:.2%}   <- compare against Table 1's 0.32% (RF-only)")
    if (tp + fp):
        print(f"\nOf {tp + fp} RF-flagged alerts, the agent correctly cleared "
              f"{tn} genuine false positives ({tn / (tp + fp):.1%} workload reduction).")
    if fn:
        print(f"WARNING: the agent wrongly dismissed {fn} genuine attack(s) out of "
              f"{tp + fn} - report this as the risk/limitation metric.")


if __name__ == "__main__":
    main()