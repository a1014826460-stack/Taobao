def test_profile_response_redacts_cookie(client, auth_headers):
    created = client.post(
        "/api/v1/profiles/credentials",
        json={"name": "tmall-main", "platform": "tmall", "cookie": "secret-cookie"},
        headers=auth_headers,
    )

    response = client.get(f"/api/v1/profiles/credentials/{created.json()['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert "secret-cookie" not in response.text


def test_invalid_encryption_key_returns_actionable_service_error(client, auth_headers, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "backend.app.api.routes.profiles.get_settings",
        lambda: SimpleNamespace(credential_encryption_key="not-a-valid-key"),
    )

    response = client.post(
        "/api/v1/profiles/credentials",
        json={"name": "tmall-main", "platform": "tmall", "cookie": "secret-cookie"},
        headers=auth_headers,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "CREDENTIAL_ENCRYPTION_NOT_CONFIGURED"
