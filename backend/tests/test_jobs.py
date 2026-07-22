def test_trial_job_is_queued_without_consuming_quota(client, auth_headers):
    response = client.post(
        "/api/v1/crawls/tmall.sku-adjust",
        json={"input": {"sku_id": "6277426546603"}},
        headers=auth_headers,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
