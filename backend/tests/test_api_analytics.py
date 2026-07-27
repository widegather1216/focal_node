import pytest

def test_get_analytics_stats(client):
    response = client.get("/api/analytics/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_photos" in data
    assert "cameras" in data
    assert "lenses" in data
    assert "focal_lengths" in data
    assert "focal_lengths_35mm" in data
    assert "apertures" in data
    assert isinstance(data["cameras"], list)
    assert isinstance(data["lenses"], list)
    assert isinstance(data["focal_lengths"], list)
    assert isinstance(data["focal_lengths_35mm"], list)
    assert isinstance(data["apertures"], list)
