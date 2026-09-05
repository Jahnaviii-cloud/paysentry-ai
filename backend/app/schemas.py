from pydantic import BaseModel, Field
from typing import Literal

PaymentMethod = Literal["UPI", "CARD", "NETBANKING", "WALLET"]
BankName = Literal["HDFC", "ICICI", "SBI", "AXIS", "KOTAK"]
RegionName = Literal["North", "South", "East", "West", "Central"]


class SimulateRequest(BaseModel):
    incident_type: Literal[
        "none",
        "issuer_degradation",
        "rail_degradation",
        "regional_network",
        "merchant_integration",
    ] = "issuer_degradation"
    minutes: int = Field(default=120, ge=30, le=720)
    transactions_per_minute: int = Field(default=35, ge=5, le=250)
    seed: int = Field(default=42, ge=0, le=1_000_000)


class IncidentSummary(BaseModel):
    incident_detected: bool
    severity: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    baseline_success_rate: float
    current_success_rate: float
    drop_percentage_points: float
    affected_method: str | None = None
    affected_bank: str | None = None
    affected_region: str | None = None
    likely_root_cause: str | None = None
    confidence: float = 0.0
    transactions_impacted: int = 0
    revenue_at_risk: float = 0.0
    recommendation: list[str] = Field(default_factory=list)
    explanation: str
