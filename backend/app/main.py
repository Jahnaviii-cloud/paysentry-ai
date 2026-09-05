from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .schemas import SimulateRequest, IncidentSummary
from .simulator import generate_transactions
from .analyzer import analyze_transactions

app = FastAPI(
    title="PaySentry AI API",
    description="Payment failure root-cause and incident intelligence demo API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "paysentry-ai"}


@app.post("/api/v1/simulate", response_model=IncidentSummary)
def simulate(payload: SimulateRequest):
    df = generate_transactions(
        minutes=payload.minutes,
        transactions_per_minute=payload.transactions_per_minute,
        incident_type=payload.incident_type,
        seed=payload.seed,
    )
    return analyze_transactions(df)


@app.get("/api/v1/demo")
def demo():
    df = generate_transactions(incident_type="issuer_degradation", seed=42)
    analysis = analyze_transactions(df)
    series = (
        df.assign(bucket=df["timestamp"].dt.floor("5min"))
        .groupby("bucket")
        .agg(success_rate=("success", "mean"), transactions=("success", "size"), volume=("amount", "sum"))
        .reset_index()
    )
    analysis["timeline"] = [
        {
            "time": row.bucket.isoformat(),
            "success_rate": round(float(row.success_rate) * 100, 2),
            "transactions": int(row.transactions),
            "volume": round(float(row.volume), 2),
        }
        for row in series.itertuples(index=False)
    ]
    return analysis
