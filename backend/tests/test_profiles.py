def test_profile_response_redacts_cookie(client, auth_headers):
    created = client.post(
        "/api/v1/profiles/credentials",
        json={"name": "tmall-main", "platform": "tmall", "cookie": "secret-cookie"},
        headers=auth_headers,
    )

    response = client.get(f"/api/v1/profiles/credentials/{created.json()['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert "secret-cookie" not in response.text
