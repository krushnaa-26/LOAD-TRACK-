# Sensor modules package
from .weight_sensor import read_weight
from .axle_sensor import read_axle
from .dimension_sensor import read_dimensions
from .height_sensor import read_height
from .clearance_sensor import read_clearance
from .camera_shape_match import read_shape_match

__all__ = [
    'read_weight',
    'read_axle',
    'read_dimensions',
    'read_height',
    'read_clearance',
    'read_shape_match'
]
