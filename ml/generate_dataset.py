from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.simulator import generate_transactions

OUT = ROOT / "data" / "sample_transactions.csv"

if __name__ == "__main__":
    df = generate_transactions(minutes=180, transactions_per_minute=40, incident_type="issuer_degradation", seed=42)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df):,} transactions to {OUT}")
