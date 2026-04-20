"""
Statistical significance engine — Wald binomial CI + two-proportion z-test.
Matches methods from Kozlov et al. Section 5.6.
"""
import math
import numpy as np
from scipy import stats


def wald_confidence_interval(p: float, n: int, alpha: float = 0.05) -> tuple[float, float]:
    z = stats.norm.ppf(1 - alpha / 2)
    margin = z * math.sqrt(p * (1 - p) / max(n, 1))
    return max(0.0, p - margin), min(1.0, p + margin)


def two_proportion_z_test(p1: float, n1: int, p2: float, n2: int) -> float:
    if n1 == 0 or n2 == 0:
        return 1.0
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    if p_pool in (0.0, 1.0):
        return 1.0
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (p1 - p2) / se
    return float(2 * (1 - stats.norm.cdf(abs(z))))


def minimum_sample_size(effect_size: float, alpha: float = 0.05, power: float = 0.80) -> int:
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    if effect_size <= 0:
        return 10000
    n = ((z_alpha + z_beta) / effect_size) ** 2
    return int(math.ceil(n))


def bonferroni_correct(pvalues: list[float]) -> list[float]:
    k = len(pvalues)
    return [min(1.0, p * k) for p in pvalues]


def compute_significance(
    control_rate: float,
    control_n: int,
    test_rate: float,
    test_n: int,
    segments: int = 1,
) -> dict:
    pvalue = two_proportion_z_test(control_rate, control_n, test_rate, test_n)
    if segments > 2:
        pvalue = min(1.0, pvalue * segments)  # Bonferroni
    ci_control = wald_confidence_interval(control_rate, control_n)
    ci_test = wald_confidence_interval(test_rate, test_n)
    return {
        "pvalue": round(pvalue, 6),
        "significant": pvalue < 0.05,
        "ci_control": (round(ci_control[0], 4), round(ci_control[1], 4)),
        "ci_test": (round(ci_test[0], 4), round(ci_test[1], 4)),
    }


def compute_clearance_rate(enrolled: int, cleared: int) -> float:
    if enrolled == 0:
        return 0.0
    return round(cleared / enrolled, 6)
