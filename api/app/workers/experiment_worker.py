"""
Experiment analysis worker — classifies accounts via PAS, computes scorecard.
"""
import logging
import random
from datetime import datetime, timezone
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.ml.pas_model import classify_accounts
from app.ml.synthetic_data import generate_account, LABEL_REVERSE
from app.ml.statistics import compute_significance, compute_clearance_rate
from app.models.experiment import Experiment
from app.models.pas_label import PasLabel
from app.models.clearance_event import ClearanceEvent
from app.models.experiment_scorecard import ExperimentScorecard
from app.models.captcha_submission import CaptchaSubmission

logger = logging.getLogger(__name__)


def _get_session() -> Session:
    engine = create_engine(settings.SYNC_DATABASE_URL)
    return sessionmaker(bind=engine)()


def _generate_executive_summary(scorecard: ExperimentScorecard) -> str:
    bpas_diff = scorecard.control_bpas - scorecard.test_bpas
    rate_diff = scorecard.control_clearance_rate - scorecard.test_clearance_rate
    p = scorecard.bpas_pvalue or 1.0

    direction = "reduced" if bpas_diff > 0 else "increased"
    summary = (
        f"The test CAPTCHA variant {direction} bot clearance rate by "
        f"{abs(bpas_diff) * 100:.1f} percentage points "
        f"(p={p:.3f}) compared to the control, "
        f"while holding real user clearance rate at {scorecard.test_clearance_rate * 100:.1f}%. "
    )
    if scorecard.test_asr_modular is not None:
        summary += (
            f"The modular attack achieved {scorecard.test_asr_modular * 100:.1f}% success "
            f"against the test variant"
        )
        if scorecard.control_asr_modular is not None:
            summary += f", down from {scorecard.control_asr_modular * 100:.1f}% against the control. "
        else:
            summary += ". "
    summary += f"Based on these results, the test variant is {scorecard.recommendation.lower().replace('_', ' ')}."
    return summary


def analyze_experiment(experiment_id: str) -> None:
    session = _get_session()
    try:
        exp: Experiment = session.get(Experiment, experiment_id)
        if not exp:
            logger.error("Experiment %s not found", experiment_id)
            return

        exp.status = "analysing"
        session.commit()

        rng = random.Random(hash(experiment_id) % 2**32)
        np_rng = __import__("numpy").random.default_rng(hash(experiment_id) % 2**32)

        # Simulate accounts that cleared the CAPTCHA
        n_control = rng.randint(800, 2000)
        n_test = rng.randint(800, 2000)

        def _make_accounts(n: int, group: str) -> list[dict]:
            accounts = []
            for i in range(n):
                label_idx = rng.choices(["GPAS", "BPAS", "EPAS"], weights=[0.65, 0.15, 0.20])[0]
                acct = generate_account(label_idx, np_rng)
                acct["account_id"] = f"{group}_{i}"
                accounts.append(acct)
            return accounts

        control_accounts = _make_accounts(n_control, "control")
        test_accounts = _make_accounts(n_test, "test")

        control_results = classify_accounts(control_accounts, exp.n_day_delay)
        test_results = classify_accounts(test_accounts, exp.n_day_delay)

        # Persist PAS labels
        now = datetime.now(timezone.utc)
        for res in control_results:
            session.add(PasLabel(
                experiment_id=exp.id,
                account_id=res["account_id"],
                group="control",
                proxy_label=res["proxy_label"],
                proxy_probability=res["proxy_probability"],
                delay_days=exp.n_day_delay,
                classified_at=now,
            ))
        for res in test_results:
            session.add(PasLabel(
                experiment_id=exp.id,
                account_id=res["account_id"],
                group="test",
                proxy_label=res["proxy_label"],
                proxy_probability=res["proxy_probability"],
                delay_days=exp.n_day_delay,
                classified_at=now,
            ))
        session.flush()

        def _distribution(results: list[dict]) -> dict:
            total = len(results) or 1
            return {
                "GPAS": sum(1 for r in results if r["proxy_label"] == "GPAS") / total,
                "BPAS": sum(1 for r in results if r["proxy_label"] == "BPAS") / total,
                "EPAS": sum(1 for r in results if r["proxy_label"] == "EPAS") / total,
            }

        ctrl_dist = _distribution(control_results)
        test_dist = _distribution(test_results)

        # Clearance rates (simulate enrolled vs cleared)
        ctrl_enrolled = int(n_control * rng.uniform(1.2, 1.8))
        test_enrolled = int(n_test * rng.uniform(1.2, 1.8))
        ctrl_cr = compute_clearance_rate(ctrl_enrolled, n_control)
        test_cr = compute_clearance_rate(test_enrolled, n_test)

        # Significance tests
        cr_sig = compute_significance(ctrl_cr, ctrl_enrolled, test_cr, test_enrolled)
        bpas_sig = compute_significance(ctrl_dist["BPAS"], n_control, test_dist["BPAS"], n_test)

        # Lookup latest ASR runs
        from app.models.attack_run import AttackRun
        ctrl_cap: CaptchaSubmission = session.get(CaptchaSubmission, str(exp.control_captcha_id))
        test_cap: CaptchaSubmission = session.get(CaptchaSubmission, str(exp.test_captcha_id))

        def _latest_asr(captcha_id, attack_type):
            stmt = (
                select(AttackRun.asr_overall)
                .where(AttackRun.captcha_id == captcha_id)
                .where(AttackRun.attack_type == attack_type)
                .where(AttackRun.status == "complete")
                .order_by(AttackRun.completed_at.desc())
                .limit(1)
            )
            row = session.execute(stmt).fetchone()
            return row[0] if row else None

        ctrl_holistic = _latest_asr(exp.control_captcha_id, "holistic")
        ctrl_modular = _latest_asr(exp.control_captcha_id, "modular")
        test_holistic = _latest_asr(exp.test_captcha_id, "holistic")
        test_modular = _latest_asr(exp.test_captcha_id, "modular")

        # Recommendation
        if bpas_sig["significant"] and test_dist["BPAS"] < ctrl_dist["BPAS"]:
            recommendation = "LAUNCH_TEST_VARIANT"
        elif bpas_sig["significant"] and test_dist["BPAS"] > ctrl_dist["BPAS"]:
            recommendation = "KEEP_CONTROL"
        else:
            recommendation = "INCONCLUSIVE"

        # Clearance funnel
        funnel = {
            "control": [
                {"step": "enrolled", "count": ctrl_enrolled},
                {"step": "flow_started", "count": int(ctrl_enrolled * 0.95)},
                {"step": "challenge_started", "count": int(ctrl_enrolled * 0.90)},
                {"step": "flow_cleared", "count": n_control},
            ],
            "test": [
                {"step": "enrolled", "count": test_enrolled},
                {"step": "flow_started", "count": int(test_enrolled * 0.94)},
                {"step": "challenge_started", "count": int(test_enrolled * 0.89)},
                {"step": "flow_cleared", "count": n_test},
            ],
        }

        # Upsert scorecard
        existing = session.execute(
            select(ExperimentScorecard).where(ExperimentScorecard.experiment_id == exp.id)
        ).scalar_one_or_none()

        if existing:
            sc = existing
        else:
            sc = ExperimentScorecard(experiment_id=exp.id)
            session.add(sc)

        sc.control_clearance_rate = ctrl_cr
        sc.control_gpas = ctrl_dist["GPAS"]
        sc.control_bpas = ctrl_dist["BPAS"]
        sc.control_epas = ctrl_dist["EPAS"]
        sc.control_asr_holistic = ctrl_holistic
        sc.control_asr_modular = ctrl_modular
        sc.test_clearance_rate = test_cr
        sc.test_gpas = test_dist["GPAS"]
        sc.test_bpas = test_dist["BPAS"]
        sc.test_epas = test_dist["EPAS"]
        sc.test_asr_holistic = test_holistic
        sc.test_asr_modular = test_modular
        sc.clearance_rate_pvalue = cr_sig["pvalue"]
        sc.bpas_pvalue = bpas_sig["pvalue"]
        sc.is_significant = bpas_sig["significant"]
        sc.category_diversity_score = test_cap.category_diversity_score if test_cap else 0.0
        sc.occlusion_score = test_cap.occlusion_score if test_cap else 0.0
        sc.variation_density_score = test_cap.variation_density_score if test_cap else 0.0
        sc.recommendation = recommendation
        sc.clearance_funnel = funnel
        sc.segment_breakdown = {}

        session.flush()
        sc.executive_summary = _generate_executive_summary(sc)
        exp.status = "complete"
        session.commit()
        logger.info("Experiment %s analysis complete: %s", experiment_id, recommendation)

    except Exception as exc:
        logger.exception("Experiment analysis %s failed: %s", experiment_id, exc)
        if session:
            exp = session.get(Experiment, experiment_id)
            if exp:
                exp.status = "failed" if exp.status == "analysing" else exp.status
                session.commit()
    finally:
        session.close()
