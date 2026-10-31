def classify_load(actual_weight, certified_capacity):
    """
    Classifies vehicle weight against its certified capacity (GVW).
    
    Returns:
        tuple: (classification_string, load_percentage)
        Classification: "underload" (<= 90%), "moderate" (90-100%), or "overload" (> 100%)
    """
    if certified_capacity <= 0:
        raise ValueError("Certified capacity must be greater than zero.")
    
    pct = (actual_weight / certified_capacity) * 100.0
    
    if pct <= 90.0:
        return "underload", round(pct, 2)
    elif pct <= 100.0:
        return "moderate", round(pct, 2)
    else:
        return "overload", round(pct, 2)
