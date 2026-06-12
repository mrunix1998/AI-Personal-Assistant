def test_register_login_and_me(client, test_user):
    me = client.get("/api/v1/auth/me", headers=test_user["headers"])
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["email"] == test_user["email"]


def test_login_rejects_wrong_password(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": "wrong-password"},
    )
    assert response.status_code in (400, 401)
