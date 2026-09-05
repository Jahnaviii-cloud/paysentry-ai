from __future__ import annotations

from pathlib import Path
import joblib
import pandas as pd
from .features import extract_root_cause_features, FEATURE_NAMES

ROOT_CAUSE_LABELS = {
    "issuer_degradation": "Issuer-side degradation",
    "rail_degradation": "Payment rail degradation",
    "regional_network": "Regional network degradation",
    "merchant_integration": "Merchant integration issue",
}

MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "root_cause_model.joblib"
_MODEL_BUNDLE = None


def _predict_root_cause(df: pd.DataFrame):
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is None and MODEL_PATH.exists():
        _MODEL_BUNDLE = joblib.load(MODEL_PATH)
    if _MODEL_BUNDLE is None:
        return None
    features = extract_root_cause_features(df)
    X = pd.DataFrame([[features[name] for name in FEATURE_NAMES]], columns=FEATURE_NAMES)
    model = _MODEL_BUNDLE["model"]
    probs = model.predict_proba(X)[0]
    best_idx = int(probs.argmax())
    return str(model.classes_[best_idx]), float(probs[best_idx])


def _rate(frame: pd.DataFrame) -> float:
    return float(frame["success"].mean()) if len(frame) else 0.0


def _best_segment(current: pd.DataFrame, baseline: pd.DataFrame, column: str):
    rows = []
    for value, cgroup in current.groupby(column):
        bgroup = baseline[baseline[column] == value]
        if len(cgroup) < 12 or len(bgroup) < 20:
            continue
        c_rate = _rate(cgroup)
        b_rate = _rate(bgroup)
        rows.append((value, b_rate - c_rate, len(cgroup), c_rate, b_rate))
    if not rows:
        return None
    return max(rows, key=lambda x: (x[1], x[2]))


def analyze_transactions(df: pd.DataFrame) -> dict:
    if df.empty:
        raise ValueError("No transactions supplied")

    max_minute = int(df["minute_offset"].max())
    split = max(1, int(max_minute * 0.76))
    baseline = df[df["minute_offset"] < split]
    current = df[df["minute_offset"] >= split]

    baseline_rate = _rate(baseline)
    current_rate = _rate(current)
    drop = max(0.0, baseline_rate - current_rate)

    method = _best_segment(current, baseline, "payment_method")
    bank = _best_segment(current, baseline, "bank")
    region = _best_segment(current, baseline, "region")
    merchant = _best_segment(current, baseline, "merchant_id")

    detected = drop >= 0.055 or any(seg and seg[1] >= 0.15 for seg in [method, bank, region, merchant])

    if not detected:
        return {
            "incident_detected": False,
            "severity": "NONE",
            "baseline_success_rate": round(baseline_rate * 100, 2),
            "current_success_rate": round(current_rate * 100, 2),
            "drop_percentage_points": round(drop * 100, 2),
            "affected_method": None,
            "affected_bank": None,
            "affected_region": None,
            "likely_root_cause": None,
            "confidence": 0.0,
            "transactions_impacted": 0,
            "revenue_at_risk": 0.0,
            "recommendation": ["Continue monitoring payment success rates."],
            "explanation": "Payment performance is within expected operating ranges; no material incident was detected.",
        }

    scores = {
        "issuer_degradation": 0.0,
        "rail_degradation": 0.0,
        "regional_network": 0.0,
        "merchant_integration": 0.0,
    }

    method_drop = method[1] if method else 0.0
    bank_drop = bank[1] if bank else 0.0
    region_drop = region[1] if region else 0.0
    merchant_drop = merchant[1] if merchant else 0.0

    # Explainable scoring rules emulate the root-cause layer used after anomaly detection.
    if method and method[0] == "UPI":
        scores["rail_degradation"] += method_drop * 1.6
        scores["issuer_degradation"] += method_drop * 0.6
    if bank:
        scores["issuer_degradation"] += bank_drop * 1.5
    if region:
        scores["regional_network"] += region_drop * 1.7
    if merchant:
        scores["merchant_integration"] += merchant_drop * 1.8

    # Failure-reason evidence.
    failures = current[current["success"] == 0]
    reason_share = failures["failure_reason"].value_counts(normalize=True).to_dict() if len(failures) else {}
    scores["issuer_degradation"] += reason_share.get("ISSUER_TIMEOUT", 0) * 0.9
    scores["rail_degradation"] += reason_share.get("UPI_RAIL_ERROR", 0) * 0.9
    scores["regional_network"] += reason_share.get("NETWORK_TIMEOUT", 0) * 0.9
    scores["merchant_integration"] += reason_share.get("MERCHANT_CALLBACK_ERROR", 0) * 0.9

    ml_prediction = _predict_root_cause(df)
    if ml_prediction:
        cause_key, ml_confidence = ml_prediction
        # Keep confidence bounded for a synthetic demo; production confidence must be calibrated.
        confidence = min(0.98, max(0.60, ml_confidence))
    else:
        cause_key = max(scores, key=scores.get)
        sorted_scores = sorted(scores.values(), reverse=True)
        gap = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]
        confidence = min(0.98, 0.62 + scores[cause_key] * 0.45 + gap * 0.25)

    # Impact = excess failures vs baseline expectation in current window.
    expected_failures = len(current) * (1 - baseline_rate)
    actual_failures = int((current["success"] == 0).sum())
    impacted = max(0, int(round(actual_failures - expected_failures)))
    avg_amount = float(current["amount"].mean()) if len(current) else 0.0
    revenue_at_risk = impacted * avg_amount

    drop_pp = drop * 100
    if drop_pp >= 25:
        severity = "CRITICAL"
    elif drop_pp >= 15:
        severity = "HIGH"
    elif drop_pp >= 8:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    cause_label = ROOT_CAUSE_LABELS[cause_key]
    recommendations = {
        "issuer_degradation": [
            "Reduce routing exposure to the affected issuer/bank where alternatives are available.",
            "Surface alternate payment methods to impacted customers.",
            "Track issuer-specific recovery before restoring normal routing weights.",
        ],
        "rail_degradation": [
            "Shift eligible traffic to alternate payment methods while the rail is degraded.",
            "Increase monitoring frequency for rail-level success rate and latency.",
            "Restore normal traffic gradually after sustained recovery.",
        ],
        "regional_network": [
            "Promote resilient alternate payment methods in the affected region.",
            "Correlate failures with network/ISP telemetry before escalation.",
            "Monitor regional recovery and customer retry behavior.",
        ],
        "merchant_integration": [
            "Inspect merchant callback/webhook and integration error logs.",
            "Temporarily isolate the affected integration path if safe to do so.",
            "Validate a successful end-to-end payment before closing the incident.",
        ],
    }[cause_key]

    affected_method = str(method[0]) if method and method[1] >= 0.06 else None
    affected_bank = str(bank[0]) if bank and bank[1] >= 0.06 else None
    affected_region = str(region[0]) if region and region[1] >= 0.06 else None

    explanation_parts = [
        f"Payment success fell from {baseline_rate * 100:.1f}% to {current_rate * 100:.1f}%.",
        f"The strongest evidence points to {cause_label.lower()} with {confidence * 100:.0f}% confidence.",
    ]
    if affected_method:
        explanation_parts.append(f"The largest payment-method degradation is concentrated in {affected_method}.")
    if affected_bank:
        explanation_parts.append(f"Bank-level analysis highlights {affected_bank} as the most affected issuer segment.")
    if affected_region:
        explanation_parts.append(f"Regional analysis shows the greatest deterioration in the {affected_region} region.")

    return {
        "incident_detected": True,
        "severity": severity,
        "baseline_success_rate": round(baseline_rate * 100, 2),
        "current_success_rate": round(current_rate * 100, 2),
        "drop_percentage_points": round(drop * 100, 2),
        "affected_method": affected_method,
        "affected_bank": affected_bank,
        "affected_region": affected_region,
        "likely_root_cause": cause_label,
        "confidence": round(confidence * 100, 1),
        "transactions_impacted": impacted,
        "revenue_at_risk": round(revenue_at_risk, 2),
        "recommendation": recommendations,
        "explanation": " ".join(explanation_parts),
    }
