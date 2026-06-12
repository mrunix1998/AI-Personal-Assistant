def test_provider_secrets_store_without_exposing_plaintext(client, test_user):
    headers = test_user["headers"]
    payload = {
        "provider": "pytest_provider",
        "key": "api_token",
        "value": "super-secret-token",
    }

    created = client.post("/api/v1/secrets", headers=headers, json=payload)
    assert created.status_code in (200, 201), created.text

    listed = client.get("/api/v1/secrets", headers=headers)
    assert listed.status_code == 200, listed.text
    assert "super-secret-token" not in listed.text