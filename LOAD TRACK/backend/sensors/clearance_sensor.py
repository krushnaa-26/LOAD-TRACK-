# Real-world hardware simulated: IR Ground-Clearance Sensor
import random

def read_clearance(base_clearance_mm=300, weight_deviation_pct=100.0):
    """
    Simulates IR Ground-Clearance Sensor. Ground clearance decreases under heavy load weight.
    """
    compression_factor = max(0.55, 1.0 - ((weight_deviation_pct - 100.0) / 180.0))
    variance = random.uniform(-8, 8)
    measured_clearance = int(base_clearance_mm * compression_factor + variance)
    return max(110, measured_clearance)
