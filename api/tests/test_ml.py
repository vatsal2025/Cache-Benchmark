import pytest
import numpy as np
from app.ml.synthetic_data import generate_dataset, generate_account, LABEL_MAP
from app.ml.attack_engine import run_attack
from app.ml.statistics import two_proportion_z_test, wald_confidence_interval, compute_significance
from app.ml.design_guidelines import compute_design_scores
from app.ml.pas_model import PASModel


def test_synthetic_data_generation():
    df = generate_dataset(1000)
    assert len(df) == 1000
    assert "label" in df.columns
    assert set(df["label"].unique()) == {0, 1, 2}


def test_gpas_account_has_many_friends():
    rng = np.random.default_rng(42)
    accts = [generate_account("GPAS", rng) for _ in range(100)]
    avg_friends = sum(a["num_friends"] for a in accts) / 100
    assert avg_friends > 50, "GPAS accounts should have many friends"


def test_bpas_account_sends_many_requests():
    rng = np.random.default_rng(42)
    accts = [generate_account("BPAS", rng) for _ in range(100)]
    avg_reqs = sum(a["friend_requests_sent"] for a in accts) / 100
    gpas_accts = [generate_account("GPAS", rng) for _ in range(100)]
    gpas_reqs = sum(a["friend_requests_sent"] for a in gpas_accts) / 100
    assert avg_reqs > gpas_reqs, "BPAS should send more friend requests than GPAS"


def test_pas_model_trains_and_predicts():
    model = PASModel(version="test_v1", tier="v1")
    metrics = model.train()
    assert metrics["f1_gpas"] >= 0.50
    assert metrics["f1_bpas"] >= 0.50
    assert metrics["f1_epas"] >= 0.30  # EPAS is harder

    # Build a feature vector the right length for whatever data source was used
    n_features = len(model.features)
    dummy_vector = [50.0] * n_features
    results = model.predict([dummy_vector])
    assert len(results) == 1
    assert results[0]["proxy_label"] in ("GPAS", "BPAS", "EPAS")
    assert 0 <= results[0]["proxy_probability"] <= 1


def test_attack_random_baseline():
    result = run_attack("cap1", "Test", "visual_reasoning", "random_baseline", 500)
    assert result["asr_overall"] < 0.05  # 1/196 ≈ 0.005
    assert result["attack_type"] == "random_baseline"


def test_attack_holistic_reasonable_asr():
    result = run_attack("cap1", "VTT test", "visual_reasoning", "holistic", 1000)
    assert 0.3 <= result["asr_overall"] <= 0.95
    assert "error_breakdown" in result


def test_attack_design_penalty():
    result_no_design = run_attack("cap1", "Test", "visual_reasoning", "holistic", 1000,
                                   category_diversity_score=0.0, occlusion_score=0.0, variation_density_score=0.0, seed=1)
    result_full_design = run_attack("cap1", "Test", "visual_reasoning", "holistic", 1000,
                                    category_diversity_score=1.0, occlusion_score=1.0, variation_density_score=1.0, seed=1)
    assert result_full_design["asr_overall"] < result_no_design["asr_overall"]


def test_wald_ci():
    lo, hi = wald_confidence_interval(0.5, 1000)
    assert lo < 0.5 < hi
    assert hi - lo < 0.1


def test_two_proportion_z_test():
    # Same proportions — should NOT be significant
    pval = two_proportion_z_test(0.5, 1000, 0.5, 1000)
    assert pval > 0.5

    # Very different proportions — should be significant
    pval2 = two_proportion_z_test(0.5, 1000, 0.3, 1000)
    assert pval2 < 0.05


def test_design_guideline_scores():
    scores = compute_design_scores(100, "full", 4)
    assert scores["category_diversity_score"] == 1.0
    assert scores["occlusion_score"] == 1.0
    assert scores["variation_density_score"] == 1.0
    assert scores["improvement_suggestions"] == []

    low_scores = compute_design_scores(10, "none", 0)
    assert low_scores["category_diversity_score"] == 0.1
    assert low_scores["occlusion_score"] == 0.0
    assert len(low_scores["improvement_suggestions"]) == 3
