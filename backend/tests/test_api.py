import pytest

def test_health_check_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_list_claims_endpoint(client):
    response = client.get("/api/v1/claims")
    assert response.status_code == 200
    data = response.json()
    assert "claims" in data
    assert isinstance(data["claims"], list)

def test_review_queue_endpoint(client):
    response = client.get("/api/v1/review/queue")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
