"""
Attack run worker — executed by RQ.
Uses real YOLO inference when CAPTCHA sample images are found in storage.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.ml.attack_engine import run_attack, _find_sample_images
from app.models.attack_run import AttackRun
from app.models.captcha_submission import CaptchaSubmission

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    engine = create_engine(settings.SYNC_DATABASE_URL)
    Sess = sessionmaker(bind=engine)
    return Sess()


def execute_attack_run(attack_run_id: str) -> None:
    session = _get_sync_session()
    try:
        run: AttackRun = session.get(AttackRun, attack_run_id)
        if not run:
            logger.error("AttackRun %s not found", attack_run_id)
            return

        captcha: CaptchaSubmission = session.get(CaptchaSubmission, str(run.captcha_id))
        if not captcha:
            logger.error("CaptchaSubmission %s not found", run.captcha_id)
            return

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        session.commit()

        image_paths = _find_sample_images(str(run.captcha_id))
        if image_paths:
            logger.info("Found %d sample images for captcha %s — using real YOLO attack",
                        len(image_paths), run.captcha_id)

        result = run_attack(
            captcha_id=str(run.captcha_id),
            captcha_name=captcha.name,
            captcha_type=captcha.captcha_type,
            attack_type=run.attack_type,
            sample_size=run.sample_size,
            category_diversity_score=captcha.category_diversity_score,
            occlusion_score=captcha.occlusion_score,
            variation_density_score=captcha.variation_density_score,
            image_paths=image_paths,
        )

        run.asr_overall = result["asr_overall"]
        run.asr_by_category = result["asr_by_category"]
        run.error_breakdown = result["error_breakdown"]
        run.avg_processing_time_ms = result["avg_processing_time_ms"]
        run.human_parity_score = result["human_parity_score"]
        run.model_version = result["model_version"]
        run.is_estimated = result.get("is_estimated", True)
        run.n_images_used = result.get("n_images_used", 0)
        run.measurement = result.get("measurement")
        run.status = "complete"
        run.completed_at = datetime.now(timezone.utc)
        session.commit()

        logger.info("AttackRun %s complete: asr=%.3f", attack_run_id, run.asr_overall)

    except Exception as exc:
        logger.exception("AttackRun %s failed: %s", attack_run_id, exc)
        if session:
            run = session.get(AttackRun, attack_run_id)
            if run:
                run.status = "failed"
                run.error_message = str(exc)[:500]
                session.commit()
    finally:
        session.close()
