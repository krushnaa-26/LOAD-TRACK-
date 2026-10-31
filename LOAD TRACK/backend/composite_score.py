"""
LOAD TRACK — Multi-Parameter Vehicle Modification & Overload Composite Scoring Engine
"""

WEIGHTS = {
    "weight": 0.35,
    "axle": 0.20,
    "volume": 0.15,
    "length": 0.10,
    "height": 0.10,
    "width": 0.10,
}

def deviation_pct(measured: float, certified: float) -> float:
    """
    Calculates percentage of measured value relative to certified registered spec.
    100.0% means exact match. >100% means exceeded/overloaded.
    """
    if certified <= 0:
        return 100.0
    return round((measured / certified) * 100.0, 2)

def composite_score(deviations: dict) -> float:
    """
    Calculates weighted average deviation percentage across all 6 parameters.
    deviations is a dict with keys matching WEIGHTS ('weight', 'axle', 'volume', 'length', 'height', 'width').
    """
    total = sum(deviations.get(k, 100.0) * WEIGHTS[k] for k in WEIGHTS)
    return round(total, 2)

def classify(score: float, deviations: dict) -> str:
    """
    Classifies scan based on composite score and hard threshold overrides.
    Returns one of:
      - "underload" (score <= 90)
      - "moderate" (90 < score <= 100)
      - "overload" (100 < score <= 115)
      - "overload_modification_flag" (score > 115 or any single parameter deviation >= 130%)
    """
    # Any single parameter far outside range triggers a hard modification flag
    # even if the composite score looks moderate
    hard_flag_threshold = 130.0  # e.g. axle count, height or length 30%+ over spec
    if any(v >= hard_flag_threshold for v in deviations.values()):
        return "overload_modification_flag"
    if score <= 90.0:
        return "underload"
    elif score <= 100.0:
        return "moderate"
    elif score <= 115.0:
        return "overload"
    else:
        return "overload_modification_flag"
