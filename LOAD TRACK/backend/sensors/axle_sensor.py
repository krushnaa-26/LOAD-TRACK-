# Real-world hardware simulated: Inductive Loop / Piezoelectric Axle Counter
import random

def read_axle(certified_axle_count, simulation_mode="normal"):
    """
    Simulates Inductive Loop / Piezoelectric Axle Counter, returning axle count.
    """
    if simulation_mode == "modification":
        return certified_axle_count + random.choice([1, 2])
    elif simulation_mode == "normal":
        if random.random() < 0.15: # 15% chance of unauthorized axle modification test case
            return certified_axle_count + random.choice([1, 2])
            
    return certified_axle_count
