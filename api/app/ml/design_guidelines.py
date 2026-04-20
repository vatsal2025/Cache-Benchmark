"""
Design guideline scoring from Gao et al. Table 11 and Table 12.
"""

SUGGESTIONS = {
    "category_diversity": (
        "Consider expanding your object category set. "
        "Research shows increasing from 50 to 100 classes reduces attack success rate "
        "by ~8 percentage points (Gao et al., Table 11)."
    ),
    "occlusion": (
        "Adding occlusion of answer objects has been shown to reduce attack success rate "
        "by ~16 percentage points with less than 1 point reduction in human pass rate "
        "(Gao et al., Table 12)."
    ),
    "variation_density": (
        "Introducing more subtle visual variations (e.g., tilt direction, notch type) "
        "significantly increases bot classification error, especially for geometric objects."
    ),
}


def compute_design_scores(
    category_set_size: int,
    occlusion_type: str,  # none|partial|full
    variation_count: int,
) -> dict:
    category_diversity = min(1.0, category_set_size / 100.0)

    if occlusion_type == "none":
        occlusion = 0.0
    elif occlusion_type == "partial":
        occlusion = 0.5
    else:  # full
        occlusion = 1.0

    variation_density = min(1.0, variation_count / 4.0)
    aggregate = (category_diversity + occlusion + variation_density) / 3.0

    suggestions = []
    if category_diversity < 0.5:
        suggestions.append({"dimension": "category_diversity", "message": SUGGESTIONS["category_diversity"]})
    if occlusion < 0.5:
        suggestions.append({"dimension": "occlusion", "message": SUGGESTIONS["occlusion"]})
    if variation_density < 0.5:
        suggestions.append({"dimension": "variation_density", "message": SUGGESTIONS["variation_density"]})

    return {
        "category_diversity_score": round(category_diversity, 4),
        "occlusion_score": round(occlusion, 4),
        "variation_density_score": round(variation_density, 4),
        "aggregate_guideline_score": round(aggregate, 4),
        "improvement_suggestions": suggestions,
    }
