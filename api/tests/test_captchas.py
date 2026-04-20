import pytest


@pytest.mark.asyncio
async def test_submit_captcha(client, org_and_token):
    _, token = org_and_token
    resp = await client.post(
        "/v1/captchas",
        json={
            "name": "Test VTT",
            "version": "1.0",
            "type": "visual_reasoning",
            "metadata": {
                "category_set_size": 100,
                "occlusion_enabled": True,
                "occlusion_type": "full",
                "variation_count": 4,
                "challenge_format": "14x14 grid",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "captcha_id" in data
    assert data["status"] == "pending"
    assert "upload_url" in data


@pytest.mark.asyncio
async def test_list_captchas(client, org_and_token):
    _, token = org_and_token
    resp = await client.get(
        "/v1/captchas",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_confirm_upload(client, org_and_token):
    _, token = org_and_token
    create = await client.post(
        "/v1/captchas",
        json={"name": "Confirm Test", "type": "visual_reasoning"},
        headers={"Authorization": f"Bearer {token}"},
    )
    captcha_id = create.json()["captcha_id"]

    resp = await client.post(
        f"/v1/captchas/{captcha_id}/confirm-upload",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_design_guideline_scores(client, org_and_token):
    _, token = org_and_token
    resp = await client.post(
        "/v1/captchas",
        json={
            "name": "High Score CAPTCHA",
            "type": "visual_reasoning",
            "metadata": {
                "category_set_size": 120,
                "occlusion_enabled": True,
                "occlusion_type": "full",
                "variation_count": 5,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    captcha_id = resp.json()["captcha_id"]
    detail = await client.get(
        f"/v1/captchas/{captcha_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    scores = detail.json()["design_guideline_scores"]
    assert scores["category_diversity"] >= 1.0
    assert scores["occlusion_score"] == 1.0
    assert scores["variation_density"] >= 1.0


@pytest.mark.asyncio
async def test_cross_tenant_isolation(client, db_session):
    import uuid
    from app.core.security import create_access_token
    other_org_id = str(uuid.uuid4())
    other_token = create_access_token({"org_id": other_org_id, "role": "analyst"})

    resp = await client.get(
        "/v1/captchas",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    # Should return 401 (org not in DB) not 200 with other org's data
    assert resp.status_code == 401
