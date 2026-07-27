def test_registered_user_receives_five_trials(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "CorrectHorse1!"},
    )

    assert response.status_code == 201
    assert response.json()["trial_successes_remaining"] == 5


def test_login_request_supports_a_bootstrap_admin_username():
    from backend.app.schemas.auth import LoginRequest

    request = LoginRequest(email="admin", password="!Lin2225427")

    assert request.email == "admin"
