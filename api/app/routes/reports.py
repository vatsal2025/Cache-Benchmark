import json
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import any_role
from app.models.experiment import Experiment
from app.models.experiment_scorecard import ExperimentScorecard
from app.models.captcha_submission import CaptchaSubmission
import uuid

router = APIRouter(prefix="/v1/reports", tags=["reports"])


@router.get("/experiments/{experiment_id}/scorecard.json")
async def export_scorecard_json(
    experiment_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    exp, sc, ctrl_cap, test_cap = await _load_scorecard(experiment_id, ctx[0].id, db)

    payload = {
        "experiment_id": str(exp.id),
        "experiment_name": exp.name,
        "control": {
            "captcha_id": str(exp.control_captcha_id),
            "captcha_name": ctrl_cap.name if ctrl_cap else None,
            "clearance_rate": sc.control_clearance_rate,
            "gpas_proportion": sc.control_gpas,
            "bpas_proportion": sc.control_bpas,
            "epas_proportion": sc.control_epas,
            "asr_holistic": sc.control_asr_holistic,
            "asr_modular": sc.control_asr_modular,
        },
        "test": {
            "captcha_id": str(exp.test_captcha_id),
            "captcha_name": test_cap.name if test_cap else None,
            "clearance_rate": sc.test_clearance_rate,
            "gpas_proportion": sc.test_gpas,
            "bpas_proportion": sc.test_bpas,
            "epas_proportion": sc.test_epas,
            "asr_holistic": sc.test_asr_holistic,
            "asr_modular": sc.test_asr_modular,
        },
        "statistical_significance": {
            "clearance_rate_pvalue": sc.clearance_rate_pvalue,
            "bpas_proportion_pvalue": sc.bpas_pvalue,
            "significant": sc.is_significant,
        },
        "design_guideline_scores": {
            "category_diversity": sc.category_diversity_score,
            "occlusion_score": sc.occlusion_score,
            "variation_density": sc.variation_density_score,
        },
        "recommendation": sc.recommendation,
        "executive_summary": sc.executive_summary,
        "model_version": sc.model_version,
        "generated_at": sc.created_at.isoformat(),
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="scorecard_{experiment_id}.json"'},
    )


@router.get("/experiments/{experiment_id}/scorecard.pdf")
async def export_scorecard_pdf(
    experiment_id: str,
    ctx=Depends(any_role),
    db: AsyncSession = Depends(get_db),
):
    exp, sc, ctrl_cap, test_cap = await _load_scorecard(experiment_id, ctx[0].id, db)

    html = _render_scorecard_html(exp, sc, ctrl_cap, test_cap)
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="scorecard_{experiment_id}.pdf"'},
        )
    except Exception:
        return Response(
            content=html.encode(),
            media_type="text/html",
            headers={"Content-Disposition": f'inline; filename="scorecard_{experiment_id}.html"'},
        )


def _render_scorecard_html(exp, sc, ctrl_cap, test_cap) -> str:
    p_color = "green" if (sc.bpas_pvalue or 1) < 0.05 else ("orange" if (sc.bpas_pvalue or 1) < 0.10 else "red")
    rec_color = "green" if sc.recommendation == "LAUNCH_TEST_VARIANT" else ("red" if sc.recommendation == "KEEP_CONTROL" else "orange")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>CAPTCHA Benchmark Scorecard — {exp.name}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #222; }}
  h1 {{ color: #1a56db; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
  th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
  th {{ background: #f3f4f6; }}
  .rec {{ padding: 12px 20px; border-radius: 6px; font-weight: bold; font-size: 1.1em; background: {rec_color}; color: white; display: inline-block; }}
  .pvalue {{ color: {p_color}; font-weight: bold; }}
  .cite {{ color: #6b7280; font-size: 0.85em; }}
</style>
</head>
<body>
<h1>CAPTCHA Robustness Benchmark — Scorecard</h1>
<p><strong>Experiment:</strong> {exp.name}</p>
<p><strong>Recommendation:</strong> <span class="rec">{sc.recommendation.replace("_", " ")}</span></p>
<p>{sc.executive_summary or ""}</p>

<h2>Performance Comparison</h2>
<table>
  <tr><th>Metric</th><th>Control ({ctrl_cap.name if ctrl_cap else "—"})</th><th>Test ({test_cap.name if test_cap else "—"})</th></tr>
  <tr><td>Clearance Rate</td><td>{sc.control_clearance_rate:.1%}</td><td>{sc.test_clearance_rate:.1%}</td></tr>
  <tr><td>GPAS (Real Users)</td><td>{sc.control_gpas:.1%}</td><td>{sc.test_gpas:.1%}</td></tr>
  <tr><td>BPAS (Fake Accounts)</td><td>{sc.control_bpas:.1%}</td><td>{sc.test_bpas:.1%}</td></tr>
  <tr><td>EPAS (Empty Signal)</td><td>{sc.control_epas:.1%}</td><td>{sc.test_epas:.1%}</td></tr>
  <tr><td>ASR Holistic</td><td>{f"{sc.control_asr_holistic:.1%}" if sc.control_asr_holistic else "—"}</td><td>{f"{sc.test_asr_holistic:.1%}" if sc.test_asr_holistic else "—"}</td></tr>
  <tr><td>ASR Modular</td><td>{f"{sc.control_asr_modular:.1%}" if sc.control_asr_modular else "—"}</td><td>{f"{sc.test_asr_modular:.1%}" if sc.test_asr_modular else "—"}</td></tr>
</table>

<h2>Statistical Significance</h2>
<table>
  <tr><th>Test</th><th>p-value</th><th>Significant (α=0.05)</th></tr>
  <tr><td>Clearance Rate difference</td><td class="pvalue">{f"{sc.clearance_rate_pvalue:.4f}" if sc.clearance_rate_pvalue else "—"}</td><td>{"Yes" if sc.clearance_rate_pvalue and sc.clearance_rate_pvalue < 0.05 else "No"}</td></tr>
  <tr><td>BPAS proportion difference</td><td class="pvalue">{f"{sc.bpas_pvalue:.4f}" if sc.bpas_pvalue else "—"}</td><td>{"Yes" if sc.bpas_pvalue and sc.bpas_pvalue < 0.05 else "No"}</td></tr>
</table>

<h2>Design Guideline Scores <span class="cite">(Gao et al., 2021)</span></h2>
<table>
  <tr><th>Guideline</th><th>Score</th></tr>
  <tr><td>Category Diversity</td><td>{sc.category_diversity_score:.2f} / 1.0</td></tr>
  <tr><td>Occlusion</td><td>{sc.occlusion_score:.2f} / 1.0</td></tr>
  <tr><td>Variation Density</td><td>{sc.variation_density_score:.2f} / 1.0</td></tr>
</table>

<p class="cite">Generated by CAPTCHA Robustness Benchmark Dashboard — Model {sc.model_version}</p>
<p class="cite">Research basis: Kozlov et al. (RAID 2020), Gao et al. (USENIX SEC 2021)</p>
</body>
</html>"""


async def _load_scorecard(experiment_id: str, org_id, db: AsyncSession):
    try:
        uid = uuid.UUID(experiment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment_id")

    result = await db.execute(
        select(Experiment).where(Experiment.id == uid, Experiment.org_id == org_id)
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    sc_result = await db.execute(
        select(ExperimentScorecard).where(ExperimentScorecard.experiment_id == exp.id)
    )
    sc = sc_result.scalar_one_or_none()
    if not sc:
        raise HTTPException(status_code=404, detail="Scorecard not yet available")

    ctrl_result = await db.execute(
        select(CaptchaSubmission).where(CaptchaSubmission.id == exp.control_captcha_id)
    )
    ctrl_cap = ctrl_result.scalar_one_or_none()

    test_result = await db.execute(
        select(CaptchaSubmission).where(CaptchaSubmission.id == exp.test_captcha_id)
    )
    test_cap = test_result.scalar_one_or_none()

    return exp, sc, ctrl_cap, test_cap
