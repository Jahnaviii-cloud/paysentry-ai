from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_all_incident_root_causes():
    expected = {
        "issuer_degradation": "Issuer-side degradation",
        "rail_degradation": "Payment rail degradation",
        "regional_network": "Regional network degradation",
        "merchant_integration": "Merchant integration issue",
    }
    for scenario, root_cause in expected.items():
        response = client.post("/api/v1/simulate", json={"incident_type": scenario, "seed": 42})
        assert response.status_code == 200
        body = response.json()
        assert body["incident_detected"] is True
        assert body["likely_root_cause"] == root_cause
        assert body["confidence"] >= 60
        assert body["transactions_impacted"] >= 0


def test_healthy_stream_not_material_incident():
    response = client.post("/api/v1/simulate", json={"incident_type": "none", "seed": 91})
    assert response.status_code == 200
    body = response.json()
    assert body["incident_detected"] is False
    assert body["severity"] == "NONE"


def test_validation_rejects_invalid_minutes():
    response = client.post("/api/v1/simulate", json={"incident_type": "issuer_degradation", "minutes": 2})
    assert response.status_code == 422
