"""Unit tests for the Cascading Blast Radius (N-1 Domino Risk) engine and endpoint."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, orchestrator
from backend.autonomy.blast_radius import calculate_blast_radius


@pytest.fixture
def client():
    return TestClient(app)


def test_calculate_blast_radius_coordinator():
    result = calculate_blast_radius(orchestrator, "SAT-07")
    assert result["targetSatelliteId"] == "SAT-07"
    assert result["severity"] == "CRITICAL"
    assert result["riskScore"] >= 90
    assert "blindspot" in result
    assert "autonomousMitigation" in result
    assert "severedLinks" in result


def test_calculate_blast_radius_non_coordinator():
    result = calculate_blast_radius(orchestrator, "SAT-01")
    assert result["targetSatelliteId"] == "SAT-01"
    assert result["severity"] in ["LOW", "MEDIUM", "HIGH"]
    assert 0 <= result["riskScore"] <= 100
    assert "affectedPeers" in result


def test_calculate_blast_radius_invalid_id():
    with pytest.raises(KeyError):
        calculate_blast_radius(orchestrator, "INVALID-99")


def test_blast_radius_api_endpoint(client):
    response = client.get("/api/autonomy/blast-radius/SAT-07")
    assert response.status_code == 200
    data = response.json()
    assert data["targetSatelliteId"] == "SAT-07"
    assert data["severity"] == "CRITICAL"
    assert data["blindspot"]["radiusKm"] > 0


def test_blast_radius_api_not_found(client):
    response = client.get("/api/autonomy/blast-radius/SAT-999")
    assert response.status_code == 404
