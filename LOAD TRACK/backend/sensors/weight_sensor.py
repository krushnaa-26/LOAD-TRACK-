# Real-world hardware simulated: Piezoelectric WIM / Bending-Plate WIM (Weigh-In-Motion) sensor
import random

def read_weight(certified_weight_kg, simulation_mode="normal"):
    """
    Simulates Piezoelectric / Bending-Plate WIM load cell readings.
    """
    if simulation_mode == "overload":
        factor = random.uniform(1.12, 1.35)
    elif simulation_mode == "underload":
        factor = random.uniform(0.70, 0.88)
    elif simulation_mode == "moderate":
        factor = random.uniform(0.92, 0.99)
    elif simulation_mode == "modification":
        factor = random.uniform(1.20, 1.45)
    else:
        # Default random variance: mostly compliant, occasionally out of range
        r = random.random()
        if r < 0.65:
            factor = random.uniform(0.75, 0.90)
        elif r < 0.80:
            factor = random.uniform(0.91, 0.99)
        else:
            factor = random.uniform(1.10, 1.32)
            
    return int(certified_weight_kg * factor)
