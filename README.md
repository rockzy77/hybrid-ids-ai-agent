# Hybrid Intrusion Detection System Using AI Agents

A two-stage hybrid IDS: a Random Forest classifier (trained on CICIDS2017) flags suspicious network traffic, then a Claude-API-powered LLM triage agent re-evaluates each flagged alert against synthetic organisational context (employees, IT tickets, leave records) stored in MySQL, to decide whether it's a genuine attack or an explainable false positive.

## Project structure

```
├── database/       MySQL schema + synthetic data seeding
│   ├── schema.sql
│   ├── seed_data.py
│   ├── reset_alerts.py
│   └── .env
├── mls/            Random Forest training (Stage 1)
│   ├── train_model.py
│   ├── data/               ← put CICIDS2017 CSVs here (not included)
│   └── .env
├── agent/          Claude API triage agent (Stage 2)
│   ├── agent.py
│   └── .env
├── backend/        Flask API tying it all together
│   ├── app.py
│   └── .env
└── frontends/       React + Vite SOC dashboard
    └── src/
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- MySQL 8.x running locally (or reachable)
- An Anthropic API key (console.anthropic.com — note this is billed separately from a Claude Pro/Max subscription)
- The CICIDS2017 dataset CSVs (download separately, not included in this repo)

## 1. Database setup

```bash
cd database
pip install -r requirements.txt
```

Create the database and tables:

```bash
mysql -u root -p < schema.sql
```

Set `database/.env`:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=hybrid_ids
```

Seed synthetic employees, tickets, and leave records:

```bash
python seed_data.py
```

`reset_alerts.py` clears just the `alerts` table (keeps employees/tickets/leave_records) if you want to re-run a batch without a full reseed.

## 2. Train the Random Forest model (Stage 1)

```bash
cd ../mls
pip install pandas numpy scikit-learn imbalanced-learn joblib
```

Download the CICIDS2017 CSVs and place them in `mls/data/`, then:

```bash
python train_model.py
```

This trains the classifier and writes `rf_model.joblib`, `label_encoder.joblib`, `feature_columns.json`, `metrics.json`, and a `live_traffic_sample.csv` (a held-out sample used to simulate live traffic through the dashboard) into `mls/`.

## 3. Configure the triage agent (Stage 2)

```bash
cd ../agent
pip install anthropic mysql-connector-python python-dotenv
```

Set `agent/.env`:

```
ANTHROPIC_API_KEY=your_api_key
CLAUDE_MODEL=claude-sonnet-5
CLAUDE_MAX_TOKENS=500
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=hybrid_ids
```

`CLAUDE_MODEL` defaults to a Haiku model if omitted; set it explicitly to whichever model you're evaluating.

You can sanity-check the agent in isolation before running the full stack:

```bash
python test_false_positive.py
```

This finds an employee with a genuinely qualifying ticket (a vulnerability scan or diagnostic port scan) and fires a synthetic PortScan alert at their IP, expecting a `false_positive` verdict grounded in the real ticket text.

## 4. Run the backend

```bash
cd ../backend
pip install flask flask-cors mysql-connector-python python-dotenv joblib scikit-learn
```

Set `backend/.env` the same way as `agent/.env` (same DB credentials).

```bash
python app.py
```

Runs on `http://localhost:5000`. Key endpoints:

- `GET /api/traffic/next` — pulls the next row from the live traffic sample, runs it through the RF model, and (if flagged) creates an alert and kicks off agent triage in the background
- `GET /api/alerts` — all alerts with their agent verdict/reasoning
- `POST /api/alerts/analyse` — synchronously triage a custom alert payload
- `GET /api/employees`
- `GET /api/dashboard/stats`

To seed a few guaranteed, demo-friendly false positives into the dashboard once the backend is running:

```bash
cd ../agent
python demo_false_positive.py --url http://localhost:5000 --count 3
```

## 5. Run the frontend

```bash
cd ../frontends
npm install
npm run dev
```

Runs on `http://localhost:5173` and talks to the backend at `http://localhost:5000` by default (override with `VITE_API_BASE_URL` in a `.env` file in `frontends/`).

## Typical run order

1. `database/seed_data.py` (once)
2. `mls/train_model.py` (once, or whenever you want a fresh live-traffic sample)
3. `backend/app.py` (keep running)
4. `frontends` (`npm run dev`, keep running)
5. Open the dashboard, use "Next Traffic" to pull rows through the pipeline — or run `agent/demo_false_positive.py` for a quick guaranteed demo

## Notes

- `database/reset_alerts.py` is useful between test runs — it wipes `alerts` without touching the seeded organisational data, so IP-to-employee mappings stay consistent.
- The `EMPLOYEE_IP_REMAP_PROBABILITY` env var in `backend/app.py` (default `0.75`) controls how often live-traffic source IPs get remapped to a real employee IP — this is what allows attacks to occasionally land on an employee with a corroborating ticket.