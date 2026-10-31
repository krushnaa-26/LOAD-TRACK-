# Real-world hardware simulated: LiDAR Laser Scanner for length and width measurement
import random

def read_dimensions(certified_length_mm, certified_width_mm, simulation_mode="normal"):
    """
    Simulates LiDAR Laser Scanner 3D point-cloud profiling for length and width.
    """
    if simulation_mode == "modification":
        l_factor = random.uniform(1.20, 1.38)
        w_factor = random.uniform(1.10, 1.25)
    elif simulation_mode == "normal":
        if random.random() < 0.15: # 15% chance of overhang / dimension modification
            l_factor = random.uniform(1.22, 1.35)
            w_factor = random.uniform(1.08, 1.20)
        else:
            l_factor = random.uniform(0.98, 1.02)
            w_factor = random.uniform(0.98, 1.02)
    else:
        l_factor = random.uniform(0.98, 1.02)
        w_factor = random.uniform(0.98, 1.02)
        
    measured_length = int(certified_length_mm * l_factor)
    measured_width = int(certified_width_mm * w_factor)
    return measured_length, measured_width
