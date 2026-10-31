# Real-world hardware simulated: CNN-based Visual Comparison Camera against RTO-registered vehicle profile
import random

def read_shape_match(is_modified=False):
    """
    Simulates CNN Visual Comparison Camera returning similarity score against registered RTO baseline image.
    Returns similarity percentage (80–100% compliant, 50–75% for modified vehicles).
    """
    if is_modified:
        return round(random.uniform(52.0, 74.0), 1)
    else:
        return round(random.uniform(88.0, 99.5), 1)
