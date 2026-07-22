def test_registered_user_receives_five_trials(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "CorrectHorse1!"},
    )

    assert response.status_code == 201
    assert response.json()["trial_successes_remaining"] == 5
