import csv
import json
import os
import random
import threading
from datetime import datetime

import joblib
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import triage_alert  # noqa: E402

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hybrid_ids"),
}

ML_DIR = os.path.join(os.path.dirname(__file__), "..", "ml")
LIVE_TRAFFIC_SAMPLE_PATH = os.getenv(
    "LIVE_TRAFFIC_SAMPLE_PATH", os.path.join(ML_DIR, "live_traffic_sample.csv")
)
MODEL_PATH = os.path.join(ML_DIR, "rf_model.joblib")
LABEL_ENCODER_PATH = os.path.join(ML_DIR, "label_encoder.joblib")
FEATURE_COLUMNS_PATH = os.path.join(ML_DIR, "feature_columns.json")


EMPLOYEE_IP_REMAP_PROBABILITY = float(os.getenv("EMPLOYEE_IP_REMAP_PROBABILITY", "0.75"))

app = Flask(__name__)
CORS(app)


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def load_employee_ips():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ip_address FROM employees")
        ips = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        print(f"Loaded {len(ips)} employee IPs for traffic remapping.")
        return ips
    except Exception as exc:
        print(f"WARNING: could not load employee IPs ({exc}). "
              "Traffic will not be remapped -- alerts will likely show 'no employee record'.")
        return []


EMPLOYEE_IPS = load_employee_ips()


print("Loading trained RF model, label encoder, and feature column order...")
rf_model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(LABEL_ENCODER_PATH)
with open(FEATURE_COLUMNS_PATH) as f:
    FEATURE_COLUMNS = json.load(f)
print(f"Loaded model expecting {len(FEATURE_COLUMNS)} features.")



_queue_lock = threading.Lock()
_traffic_queue = []
_queue_index = 0
_total_traffic_processed = 0 


def load_traffic_queue():
    global _traffic_queue
    if not os.path.exists(LIVE_TRAFFIC_SAMPLE_PATH):
        print(f"WARNING: {LIVE_TRAFFIC_SAMPLE_PATH} not found. /api/traffic/next will return empty.")
        _traffic_queue = []
        return

    with open(LIVE_TRAFFIC_SAMPLE_PATH, newline="") as f:
        reader = csv.DictReader(f)
        _traffic_queue = list(reader)
    print(f"Loaded {len(_traffic_queue)} rows of simulated live traffic into the queue.")


load_traffic_queue()


def run_agent_in_background(alert_id: int, alert_for_agent: dict):
    def _worker():
        try:
            result = triage_alert(alert_for_agent)
        except Exception as exc:  
            result = {
                "verdict": "true_positive",
                "reasoning": f"Agent call failed ({exc}); defaulting to true_positive for safety.",
            }

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE alerts
            SET reasoning_status = 'complete',
                agent_verdict = %s,
                agent_reasoning = %s,
                reasoning_completed_at = %s
            WHERE id = %s
            """,
            (result["verdict"], result["reasoning"], datetime.now(), alert_id),
        )
        conn.commit()
        cursor.close()
        conn.close()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC")
    alerts = cursor.fetchall()
    cursor.close()
    conn.close()

    for a in alerts:
        for key, value in a.items():
            if hasattr(value, "isoformat"):
                a[key] = value.isoformat()

    return jsonify(alerts)


@app.route("/api/traffic/next", methods=["GET"])
def get_next_traffic():
    
    global _queue_index

    with _queue_lock:
        if _queue_index >= len(_traffic_queue):
            return jsonify({"message": "No more traffic in queue."}), 204

        row = _traffic_queue[_queue_index]
        _queue_index += 1

    try:
        feature_values = [float(row[col]) for col in FEATURE_COLUMNS]
    except (KeyError, ValueError) as exc:
        return jsonify({"error": f"Traffic row missing/invalid feature data: {exc}"}), 500

    predicted_idx = rf_model.predict([feature_values])[0]
    predicted_label = label_encoder.inverse_transform([predicted_idx])[0]
    confidence = float(max(rf_model.predict_proba([feature_values])[0]))

    global _total_traffic_processed
    with _queue_lock:
        _total_traffic_processed += 1

    src_ip = row.get("src_ip")
    dst_port = int(float(row.get("dst_port", 0)))
    protocol = row.get("protocol_display", "UNKNOWN")
    timestamp = row.get("timestamp")
    ground_truth_label = row.get("ground_truth_label")  

    if EMPLOYEE_IPS and random.random() < EMPLOYEE_IP_REMAP_PROBABILITY:
        src_ip = random.choice(EMPLOYEE_IPS)

    base_response = {
        "src_ip": src_ip,
        "dst_port": dst_port,
        "protocol": protocol,
        "predicted_label": predicted_label,
        "confidence": round(confidence, 4),
        "timestamp": timestamp,
    }

    if predicted_label == "BENIGN":
        return jsonify({**base_response, "is_attack": False})
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute(
        """
        INSERT INTO alerts (src_ip, dst_port, protocol, label, ground_truth_label,
                             confidence, timestamp, reasoning_status, reasoning_started_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'reasoning', %s)
        """,
        (src_ip, dst_port, protocol, predicted_label, ground_truth_label,
         confidence, timestamp, now),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()

    alert_for_agent = {
        "src_ip": src_ip,
        "dst_port": dst_port,
        "protocol": protocol,
        "label": predicted_label,
        "confidence": confidence,
        "timestamp": timestamp,
    }
    run_agent_in_background(new_id, alert_for_agent)

    return jsonify({
        **base_response,
        "is_attack": True,
        "id": new_id,
        "reasoning_status": "reasoning",
    })


@app.route("/api/alerts/analyse", methods=["POST"])
def analyse_alert():
    payload = request.get_json(force=True)
    required = ["src_ip", "dst_port", "protocol", "label", "confidence", "timestamp"]
    missing = [f for f in required if f not in payload]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute(
        """
        INSERT INTO alerts (src_ip, dst_port, protocol, label, confidence, timestamp,
                             reasoning_status, reasoning_started_at)
        VALUES (%s, %s, %s, %s, %s, %s, 'reasoning', %s)
        """,
        (
            payload["src_ip"],
            int(payload["dst_port"]),
            payload["protocol"],
            payload["label"],
            float(payload["confidence"]),
            payload["timestamp"],
            now,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid

    result = triage_alert(payload)

    cursor.execute(
        """
        UPDATE alerts
        SET reasoning_status = 'complete',
            agent_verdict = %s,
            agent_reasoning = %s,
            reasoning_completed_at = %s
        WHERE id = %s
        """,
        (result["verdict"], result["reasoning"], datetime.now(), new_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"id": new_id, **result})


@app.route("/api/employees", methods=["GET"])
def get_employees():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM employees ORDER BY name")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()

    for e in employees:
        for key, value in e.items():
            if hasattr(value, "isoformat"):
                e[key] = value.isoformat()
            elif hasattr(value, "total_seconds"):
                e[key] = str(value)

    return jsonify(employees)


@app.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM alerts")
    total_alerts = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS c FROM alerts WHERE reasoning_status = 'complete'")
    total_completed = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM alerts WHERE agent_verdict = 'true_positive'")
    true_positives = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) AS c FROM alerts WHERE agent_verdict = 'false_positive'")
    false_positives = cursor.fetchone()["c"]

    cursor.close()
    conn.close()
    
    alert_reduction_rate = (false_positives / total_completed) if total_completed else 0.0

    rf_test_fpr = None
    metrics_path = os.path.join(os.path.dirname(__file__), "..", "ml", "metrics.json")
    if os.path.exists(metrics_path):
        import json
        with open(metrics_path) as f:
            rf_test_fpr = json.load(f).get("false_positive_rate")

    return jsonify({
        "total_traffic_processed": _total_traffic_processed,
        "total_alerts": total_alerts,
        "total_completed": total_completed,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "alert_reduction_rate": round(alert_reduction_rate, 4),
        "rf_test_fpr": rf_test_fpr,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)