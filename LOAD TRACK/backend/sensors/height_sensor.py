# Real-world hardware simulated: IR Light Curtain / Photoelectric Beam Sensor
import random

def read_height(certified_height_mm, simulation_mode="normal"):
    """
    Simulates IR Light Curtain / Photoelectric Beam Sensor for height measurement.
    """
    if simulation_mode == "modification":
        h_factor = random.uniform(1.22, 1.38)
    elif simulation_mode == "normal":
        if random.random() < 0.15: # 15% chance of vertical height extension test case
            h_factor = random.uniform(1.25, 1.36)
        else:
            h_factor = random.uniform(0.98, 1.02)
    else:
        h_factor = random.uniform(0.98, 1.02)
        
    return int(certified_height_mm * h_factor)
