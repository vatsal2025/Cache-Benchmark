import pytest
import uuid


@pytest.mark.asyncio
async def test_create_experiment_requires_different_captchas(client, org_and_token):
    _, token = org_and_token
    cap_id = str(uuid.uuid4())
    resp = await client.post(
        "/v1/experiments",
        json={
            "name": "Bad Experiment",
            "control_captcha_id": cap_id,
            "test_captcha_id": cap_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_experiment_with_valid_captchas(client, org_and_token, db_session):
    org, token = org_and_token
    import uuid as _uuid
    from datetime import datetime, timezone
    from app.models.captcha_submission import CaptchaSubmission
    from app.ml.design_guidelines import compute_design_scores

    scores = compute_design_scores(50, "none", 1)
    now = datetime.now(timezone.utc)

    ctrl_id = _uuid.uuid4()
    test_id = _uuid.uuid4()

    for cid, name in [(ctrl_id, "Ctrl"), (test_id, "Test")]:
        cap = CaptchaSubmission(
            id=cid, org_id=org.id, name=name, version="1.0",
            captcha_type="visual_reasoning", status="ready",
            category_set_size=50, occlusion_enabled=False, occlusion_type="none",
            variation_count=1, challenge_format="",
            **{k: v for k, v in scores.items() if k != "improvement_suggestions"},
            improvement_suggestions=[],
            created_at=now, updated_at=now,
        )
        db_session.add(cap)
    await db_session.commit()

    resp = await client.post(
        "/v1/experiments",
        json={
            "name": "Valid A/B Test",
            "control_captcha_id": str(ctrl_id),
            "test_captcha_id": str(test_id),
            "n_day_delay": 7,
            "backtest_enabled": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_experiments(client, org_and_token):
    _, token = org_and_token
    resp = await client.get(
        "/v1/experiments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
