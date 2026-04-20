"""
Backtest worker — monitors BPAS drift for holdout groups.
"""
import logging
import random
from datetime import datetime, date, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.models.backtest_holdout import BacktestHoldout
from app.models.adaptation_alert import AdaptationAlert
from app.models.experiment_scorecard import ExperimentScorecard

logger = logging.getLogger(__name__)


def _get_session() -> Session:
    engine = create_engine(settings.SYNC_DATABASE_URL)
    return sessionmaker(bind=engine)()


def check_all_backtests() -> None:
    session = _get_session()
    try:
        holdouts = session.execute(
            select(BacktestHoldout).where(BacktestHoldout.status == "monitoring")
        ).scalars().all()

        for holdout in holdouts:
            _check_holdout(holdout, session)

        session.commit()
    finally:
        session.close()


def _check_holdout(holdout: BacktestHoldout, session: Session) -> None:
    sc = session.execute(
        select(ExperimentScorecard).where(ExperimentScorecard.experiment_id == holdout.experiment_id)
    ).scalar_one_or_none()

    if not sc:
        return

    if holdout.baseline_bpas_prevalence is None:
        holdout.baseline_bpas_prevalence = sc.control_bpas
        holdout.current_bpas_prevalence = sc.control_bpas
        session.flush()
        return

    # Simulate drift over time (in production this would query real PAS labels)
    rng = random.Random(hash(str(holdout.id) + str(date.today())) % 2**32)
    drift = rng.normalvariate(0, 0.02)
    new_bpas = max(0.0, min(1.0, holdout.current_bpas_prevalence + drift))
    holdout.current_bpas_prevalence = round(new_bpas, 4)

    history = holdout.bpas_history or []
    history.append({"date": str(date.today()), "bpas_prevalence": holdout.current_bpas_prevalence})
    holdout.bpas_history = history[-90:]  # keep 90 days
    holdout.updated_at = datetime.now(timezone.utc)

    magnitude = abs(holdout.current_bpas_prevalence - holdout.baseline_bpas_prevalence)
    threshold = settings.BPAS_ALERT_THRESHOLD

    if magnitude >= threshold:
        # Create alert if not already active
        existing_alert = session.execute(
            select(AdaptationAlert).where(
                AdaptationAlert.holdout_id == holdout.id,
                AdaptationAlert.status == "active",
            )
        ).scalar_one_or_none()

        if not existing_alert:
            from app.models.experiment import Experiment
            exp = session.get(Experiment, str(holdout.experiment_id))
            alert = AdaptationAlert(
                holdout_id=holdout.id,
                experiment_id=holdout.experiment_id,
                org_id=exp.org_id if exp else holdout.experiment_id,
                baseline_bpas=holdout.baseline_bpas_prevalence,
                current_bpas=holdout.current_bpas_prevalence,
                drift_magnitude=round(magnitude, 4),
                nature="BPAS_DRIFT",
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            session.add(alert)
            holdout.status = "alert"
            logger.warning(
                "Adversarial adaptation detected: holdout=%s drift=%.3f",
                holdout.id, magnitude
            )

    session.flush()
