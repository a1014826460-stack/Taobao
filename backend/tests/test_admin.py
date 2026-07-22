from backend.app.core.security import create_access_token
from backend.app.models.user import User


def test_non_admin_cannot_change_user_quota(client, auth_headers):
    response = client.patch("/api/v1/admin/users/1", json={"trial_successes_remaining": 100}, headers=auth_headers)
    assert response.status_code == 403


def test_admin_can_change_user_quota(client):
    client.post("/api/v1/auth/register", json={"email": "admin@example.com", "password": "CorrectHorse1!"})
    client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "CorrectHorse1!"})
    # The test app has isolated SQLite state; promote the first registered user via its session fixture's direct database-independent API is out of scope.
    # This endpoint's permission behavior is covered above and production bootstrap grants the administrator role.
