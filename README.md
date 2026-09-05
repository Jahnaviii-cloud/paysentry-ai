# PaySentry AI

**AI-powered payment failure root-cause and incident intelligence platform.**

PaySentry AI simulates a high-volume digital-payment stream, detects abnormal success-rate degradation, identifies the most affected payment method/bank/region, estimates business impact, and produces explainable remediation recommendations.

> This repository uses synthetic data only. It contains no real payment credentials, card data, customer PII, or banking secrets.

## Why this project

Payment systems can fail in many places: issuer banks, payment rails, regional networks, merchant integrations, or customer-side conditions. A raw alert like "success rate dropped" is not enough. Operations teams need to know **what changed, where it changed, how severe it is, and what to do next**.

## MVP capabilities

- Synthetic payment-stream generator
- Incident injection: issuer, rail, region, merchant integration, or healthy traffic
- Rolling-baseline success-rate anomaly detection
- Segment-level root-cause analysis across payment method, bank, region, and merchant
- Random Forest root-cause classifier trained on synthetic incident scenarios
- Explainable confidence score using model probability plus observable degradation/failure evidence
- Excess-failure and revenue-at-risk estimation
- FastAPI endpoints with OpenAPI docs
- Dependency-free responsive incident dashboard (HTML/CSS/JavaScript)
- Automated API tests
- Docker setup

## Architecture

```text
Synthetic payment stream
        |
        v
Feature aggregation / baseline
        |
        v
Anomaly detector
        |
        v
Segment degradation analysis
(method / bank / region / merchant)
        |
        v
Root-cause evidence scorer
        |
        +--> Impact estimator
        |
        +--> Explainable recommendations
        |
        v
FastAPI --> Web dashboard
```

## Incident scenarios

1. `issuer_degradation` - ICICI UPI success drops sharply late in the stream.
2. `rail_degradation` - broad UPI degradation across banks.
3. `regional_network` - South-region UPI/netbanking failures increase.
4. `merchant_integration` - one merchant experiences callback/integration failures.
5. `none` - normal healthy traffic.

## Local setup

### Backend

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
python -m http.server 5173
```

Dashboard: `http://127.0.0.1:5173`

### Tests

```bash
pytest -q
node --check frontend/app.js
```

The repository also includes a GitHub Actions workflow that repeats syntax and API validation on every push/pull request.

### Generate a sample CSV

```bash
python ml/generate_dataset.py
```

### Docker

```bash
docker compose up --build
```

## API examples

### Health

`GET /health`

### Simulate and analyze

`POST /api/v1/simulate`

```json
{
  "incident_type": "issuer_degradation",
  "minutes": 120,
  "transactions_per_minute": 35,
  "seed": 42
}
```

Representative output:

```json
{
  "incident_detected": true,
  "severity": "HIGH",
  "baseline_success_rate": 94.1,
  "current_success_rate": 87.0,
  "affected_method": "UPI",
  "affected_bank": "ICICI",
  "likely_root_cause": "Issuer-side degradation",
  "confidence": 90.0,
  "transactions_impacted": 80,
  "revenue_at_risk": 210000
}
```

## Evaluation philosophy

This is an incident-intelligence MVP, not a claim that synthetic behavior exactly reproduces a production payment network. Evaluation should focus on:

- incident detection rate by scenario
- false-alert rate on healthy streams
- root-cause classification accuracy
- detection delay
- impact-estimation error

A production version would learn dynamic baselines per merchant/issuer/payment rail, consume real observability telemetry, persist events, and add model/feature monitoring.

## Production hardening roadmap

- Kafka/PubSub ingestion instead of in-memory simulation
- Redis/stream processor for rolling features
- PostgreSQL/ClickHouse for incident and payment aggregates
- Isolation Forest/change-point model alongside statistical rules
- supervised root-cause classifier trained on labeled incidents
- model registry and drift monitoring
- authenticated APIs and RBAC
- audit logging and incident acknowledgements
- OpenTelemetry metrics/traces
- Kubernetes deployment and autoscaling

## Interview talking points

- Why accuracy alone is not a useful operational metric
- How baseline choice changes false positives
- How to separate issuer degradation from payment-rail degradation
- Why root-cause evidence should be explainable
- How to avoid leaking sensitive payment data
- How to scale from a synthetic MVP to millions of events per minute

## License

For interview/demo use. Add an OSI-approved license before public reuse if desired.
