from __future__ import annotations
import pandas as pd

FEATURE_NAMES = [
    "overall_drop",
    "upi_drop",
    "card_drop",
    "netbanking_drop",
    "wallet_drop",
    "worst_bank_drop",
    "worst_region_drop",
    "worst_merchant_drop",
    "issuer_timeout_share",
    "rail_error_share",
    "network_timeout_share",
    "merchant_callback_share",
]


def _rate(frame: pd.DataFrame) -> float:
    return float(frame["success"].mean()) if len(frame) else 0.0


def _drop_for_value(current: pd.DataFrame, baseline: pd.DataFrame, column: str, value: str) -> float:
    c = current[current[column] == value]
    b = baseline[baseline[column] == value]
    if len(c) < 8 or len(b) < 12:
        return 0.0
    return max(0.0, _rate(b) - _rate(c))


def _worst_drop(current: pd.DataFrame, baseline: pd.DataFrame, column: str) -> float:
    values = current[column].dropna().unique().tolist()
    return max([_drop_for_value(current, baseline, column, str(v)) for v in values] or [0.0])


def incident_windows(df: pd.DataFrame):
    max_minute = int(df["minute_offset"].max())
    split = max(1, int(max_minute * 0.76))
    return df[df["minute_offset"] < split], df[df["minute_offset"] >= split]


def extract_root_cause_features(df: pd.DataFrame) -> dict[str, float]:
    baseline, current = incident_windows(df)
    failures = current[current["success"] == 0]
    reason_share = failures["failure_reason"].value_counts(normalize=True).to_dict() if len(failures) else {}
    return {
        "overall_drop": max(0.0, _rate(baseline) - _rate(current)),
        "upi_drop": _drop_for_value(current, baseline, "payment_method", "UPI"),
        "card_drop": _drop_for_value(current, baseline, "payment_method", "CARD"),
        "netbanking_drop": _drop_for_value(current, baseline, "payment_method", "NETBANKING"),
        "wallet_drop": _drop_for_value(current, baseline, "payment_method", "WALLET"),
        "worst_bank_drop": _worst_drop(current, baseline, "bank"),
        "worst_region_drop": _worst_drop(current, baseline, "region"),
        "worst_merchant_drop": _worst_drop(current, baseline, "merchant_id"),
        "issuer_timeout_share": float(reason_share.get("ISSUER_TIMEOUT", 0.0)),
        "rail_error_share": float(reason_share.get("UPI_RAIL_ERROR", 0.0)),
        "network_timeout_share": float(reason_share.get("NETWORK_TIMEOUT", 0.0)),
        "merchant_callback_share": float(reason_share.get("MERCHANT_CALLBACK_ERROR", 0.0)),
    }
