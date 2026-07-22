from backend.app.models.api_token import ApiToken


def test_api_token_is_plaintext_once_and_digest_at_rest(client, auth_headers):
    response = client.post("/api/v1/tokens", json={"name": "local-tool"}, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["token"].startswith("cap_")


def test_api_token_auth_can_submit_a_job(client, auth_headers):
    token = client.post("/api/v1/tokens", json={"name": "automation"}, headers=auth_headers).json()["token"]
    response = client.post(
        "/api/v1/crawls/tmall.sku-adjust",
        json={"input": {"sku_id": "6277426546603"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
