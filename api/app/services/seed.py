"""
Seed script — creates one org with two CAPTCHAs, one experiment, and 500 synthetic clearance events.
Run: python -m app.services.seed
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta, date
import random

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.security import hash_password, generate_client_credentials
from app.models.organisation import Organisation
from app.models.captcha_submission import CaptchaSubmission
from app.models.experiment import Experiment
from app.models.clearance_event import ClearanceEvent
from app.ml.design_guidelines import compute_design_scores


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        # Org
        client_id, client_secret = generate_client_credentials()
        org_id = uuid.uuid4()
        org = Organisation(
            id=org_id,
            name="Demo Organisation",
            email="demo@captcha-benchmark.io",
            client_id=client_id,
            client_secret_hash=hash_password(client_secret),
            role_tier="admin",
            tos_accepted=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(org)
        await db.flush()
        print(f"[SEED] Organisation: {org_id}")
        print(f"[SEED] client_id: {client_id}")
        print(f"[SEED] client_secret: {client_secret}")

        # CAPTCHAs
        now = datetime.now(timezone.utc)
        ctrl_scores = compute_design_scores(50, "partial", 2)
        test_scores = compute_design_scores(100, "full", 4)

        ctrl_id = uuid.uuid4()
        ctrl = CaptchaSubmission(
            id=ctrl_id, org_id=org_id, name="VTT Control v1", version="1.0",
            captcha_type="visual_reasoning", category_set_size=50,
            occlusion_enabled=True, occlusion_type="partial", variation_count=2,
            challenge_format="14x14 grid", status="ready", tags=["production"],
            **{k: v for k, v in ctrl_scores.items() if k != "improvement_suggestions"},
            improvement_suggestions=ctrl_scores["improvement_suggestions"],
            created_at=now, updated_at=now,
        )

        test_id = uuid.uuid4()
        test_cap = CaptchaSubmission(
            id=test_id, org_id=org_id, name="VTT Enhanced v2", version="2.0",
            captcha_type="visual_reasoning", category_set_size=100,
            occlusion_enabled=True, occlusion_type="full", variation_count=4,
            challenge_format="14x14 grid", status="ready", tags=["experimental"],
            **{k: v for k, v in test_scores.items() if k != "improvement_suggestions"},
            improvement_suggestions=test_scores["improvement_suggestions"],
            created_at=now, updated_at=now,
        )
        db.add(ctrl)
        db.add(test_cap)
        await db.flush()

        # Experiment
        exp_id = uuid.uuid4()
        exp = Experiment(
            id=exp_id, org_id=org_id, name="VTT v1 vs v2 A/B Test",
            control_captcha_id=ctrl_id, test_captcha_id=test_id,
            population_segments={"platforms": ["mobile", "desktop"], "locales": ["en-US"], "account_age_bands": ["0-30", "30-180", "180+"]},
            start_date=date.today() - timedelta(days=14),
            end_date=date.today(),
            n_day_delay=7, status="complete", backtest_enabled=True,
            created_at=now, updated_at=now,
        )
        db.add(exp)
        await db.flush()

        # Clearance events
        rng = random.Random(42)
        event_types = ["enrolled", "flow_started", "challenge_started", "flow_cleared"]
        countries = ["US", "GB", "IN", "DE", "FR"]
        devices = ["mobile", "desktop", "tablet"]

        for i in range(500):
            group = "control" if i % 2 == 0 else "test"
            occurred = now - timedelta(days=rng.randint(1, 14))
            db.add(ClearanceEvent(
                experiment_id=exp_id,
                account_id=f"acct_{uuid.uuid4().hex[:16]}",
                group=group,
                event_type=rng.choice(event_types),
                step_id="step_1",
                country=rng.choice(countries),
                device_type=rng.choice(devices),
                account_age_days=rng.randint(1, 365),
                occurred_at=occurred,
                created_at=now,
            ))

        await db.commit()
        print(f"[SEED] CAPTCHAs: control={ctrl_id} test={test_id}")
        print(f"[SEED] Experiment: {exp_id}")
        print("[SEED] 500 clearance events inserted")
        print("[SEED] Done ✓")


if __name__ == "__main__":
    asyncio.run(seed())
