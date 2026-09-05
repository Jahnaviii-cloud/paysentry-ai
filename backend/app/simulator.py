from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]
BANKS = ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK"]
REGIONS = ["North", "South", "East", "West", "Central"]
MERCHANTS = ["M001", "M002", "M003", "M004", "M005", "M006"]

BASE_SUCCESS = {
    "UPI": 0.955,
    "CARD": 0.925,
    "NETBANKING": 0.900,
    "WALLET": 0.965,
}


@dataclass
class IncidentWindow:
    start_minute: int
    end_minute: int


def generate_transactions(
    minutes: int = 120,
    transactions_per_minute: int = 35,
    incident_type: str = "issuer_degradation",
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    total = minutes * transactions_per_minute
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now - timedelta(minutes=minutes)

    minute_offsets = np.repeat(np.arange(minutes), transactions_per_minute)
    rng.shuffle(minute_offsets)
    timestamps = [start + timedelta(minutes=int(m), seconds=int(rng.integers(0, 60))) for m in minute_offsets]

    methods = rng.choice(METHODS, total, p=[0.52, 0.28, 0.12, 0.08])
    banks = rng.choice(BANKS, total, p=[0.23, 0.21, 0.26, 0.17, 0.13])
    regions = rng.choice(REGIONS, total, p=[0.22, 0.28, 0.16, 0.22, 0.12])
    merchants = rng.choice(MERCHANTS, total)
    amounts = np.round(np.clip(rng.lognormal(mean=7.3, sigma=0.8, size=total), 50, 60_000), 2)

    base_prob = np.array([BASE_SUCCESS[m] for m in methods], dtype=float)
    # Small realistic variations.
    base_prob -= np.where(banks == "SBI", 0.006, 0.0)
    base_prob -= np.where(regions == "Central", 0.004, 0.0)

    incident = IncidentWindow(start_minute=max(1, int(minutes * 0.78)), end_minute=minutes)
    in_window = minute_offsets >= incident.start_minute

    failure_reason = np.full(total, "NONE", dtype=object)
    degradation_mask = np.zeros(total, dtype=bool)

    if incident_type == "issuer_degradation":
        degradation_mask = in_window & (methods == "UPI") & (banks == "ICICI")
        base_prob[degradation_mask] -= 0.48
        failure_reason[degradation_mask] = "ISSUER_TIMEOUT"
    elif incident_type == "rail_degradation":
        degradation_mask = in_window & (methods == "UPI")
        base_prob[degradation_mask] -= 0.31
        failure_reason[degradation_mask] = "UPI_RAIL_ERROR"
    elif incident_type == "regional_network":
        degradation_mask = in_window & (regions == "South") & np.isin(methods, ["UPI", "NETBANKING"])
        base_prob[degradation_mask] -= 0.36
        failure_reason[degradation_mask] = "NETWORK_TIMEOUT"
    elif incident_type == "merchant_integration":
        degradation_mask = in_window & (merchants == "M003")
        base_prob[degradation_mask] -= 0.52
        failure_reason[degradation_mask] = "MERCHANT_CALLBACK_ERROR"

    probs = np.clip(base_prob, 0.05, 0.995)
    success = rng.random(total) < probs

    ordinary_failures = ~success & ~degradation_mask
    ordinary_reasons = rng.choice(
        ["INSUFFICIENT_FUNDS", "CUSTOMER_CANCELLED", "BANK_DECLINED", "TIMEOUT"],
        ordinary_failures.sum(),
        p=[0.28, 0.24, 0.30, 0.18],
    )
    failure_reason[ordinary_failures] = ordinary_reasons
    failure_reason[success] = "NONE"

    df = pd.DataFrame({
        "transaction_id": [f"TXN{i:07d}" for i in range(total)],
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "minute_offset": minute_offsets,
        "payment_method": methods,
        "bank": banks,
        "region": regions,
        "merchant_id": merchants,
        "amount": amounts,
        "success": success.astype(int),
        "failure_reason": failure_reason,
    })
    return df.sort_values("timestamp").reset_index(drop=True)
