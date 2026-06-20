from fastapi.testclient import TestClient
from backend.main import app


def test_correlation_id_generated_when_absent():
    with TestClient(app) as client:
        response = client.get("/health")
    assert "x-correlation-id" in response.headers
    cid = response.headers["x-correlation-id"]
    assert len(cid) >= 1


def test_correlation_id_echoed_when_provided():
    with TestClient(app) as client:
        custom_id = "custom-trace-abc-123"
        response = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert response.headers["x-correlation-id"] == custom_id
