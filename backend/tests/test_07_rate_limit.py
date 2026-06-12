def test_auth_login_rate_limit_or_stable_error(client):
    # We do not require a specific limit number because dev/prod configs may differ.
    # This test ensures repeated bad logins do not return 500 and, if rate limiting is
    # active, eventually returns 429.
    statuses = []
    for _ in range(10):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
        )
        statuses.append(response.status_code)
        assert response.status_code in (400, 401, 422, 429), response.text
    assert all(code < 500 for code in statuses)
