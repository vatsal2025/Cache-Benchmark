import pytest


@pytest.mark.asyncio
async def test_register_and_token(client):
    reg = await client.post("/auth/register", json={
        "name": "My Org",
        "email": "myorg@test.io",
        "tos_accepted": True,
    })
    assert reg.status_code == 201
    data = reg.json()
    assert "client_id" in data
    assert "client_secret" in data

    token_resp = await client.post("/auth/token", json={
        "client_id": data["client_id"],
        "client_secret": data["client_secret"],
    })
    assert token_resp.status_code == 200
    assert "access_token" in token_resp.json()


@pytest.mark.asyncio
async def test_invalid_credentials(client):
    resp = await client.post("/auth/token", json={
        "client_id": "nonexistent",
        "client_secret": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_viewer_cannot_submit(client, org_and_token):
    org, _ = org_and_token
    from app.core.security import create_access_token
    viewer_token = create_access_token({"org_id": str(org.id), "role": "viewer"})

    resp = await client.post(
        "/v1/captchas",
        json={"name": "Test", "type": "visual_reasoning"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403
