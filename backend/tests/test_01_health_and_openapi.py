def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()


def test_openapi_has_core_paths(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    expected = [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/agenda/unified-daily",
        "/api/v1/notifications/center",
        "/api/v1/notifications/web-push/subscriptions",
        "/api/v1/automation/status",
        "/api/v1/monitoring/metrics",
    ]
    for path in expected:
        assert path in paths
