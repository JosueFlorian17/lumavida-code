"""
Pruebas de Integración de la API FastAPI de LumaVida
Verifica la funcionalidad completa de los endpoints REST.
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_challenge_generation():
    response = client.post("/api/challenge")
    assert response.status_code == 200
    data = response.json()
    assert "challenge_id" in data
    assert "sequence" in data
    assert len(data["sequence"]) >= 4
    assert data["total_duration_ms"] > 1000

def test_api_simulate_attack_scenarios():
    for scenario in ["photo", "screen", "deepfake"]:
        response = client.post(f"/api/simulate-attack?scenario_type={scenario}")
        assert response.status_code == 200
        data = response.json()
        assert data["pad_verdict"] == "ATTACK_INTERCEPTED"
        assert data["simulated_liveness"]["is_bona_fide"] is False
        assert "details" in data["simulated_liveness"]

def test_api_metrics_endpoint():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "iso_iec_30107_3_pad" in data
    assert "iso_iec_19795_1_biometric" in data
    assert "legal_compliance" in data
    assert data["legal_compliance"]["peru_law_29733"].startswith("COMPLIANT")
