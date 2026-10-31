from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    model_name = db.Column(db.String(100), nullable=False)
    manufacturer = db.Column(db.String(100), nullable=False)
    certified_capacity_kg = db.Column(db.Integer, nullable=False)
    
    # Certified Specifications
    certified_length_mm = db.Column(db.Integer, nullable=False, default=10500)
    certified_width_mm = db.Column(db.Integer, nullable=False, default=2500)
    certified_height_mm = db.Column(db.Integer, nullable=False, default=3800)
    certified_axle_count = db.Column(db.Integer, nullable=False, default=3)
    certified_volume_m3 = db.Column(db.Float, nullable=False, default=99.75)
    
    owner_name = db.Column(db.String(100), nullable=False)
    owner_phone = db.Column(db.String(20), nullable=False)
    violation_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='compliant') # "compliant" | "1st_offense" | "escalated" | "seized"

    scans = db.relationship('Scan', backref='vehicle', lazy=True, cascade="all, delete-orphan")
    challans = db.relationship('Challan', backref='vehicle', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'plate_number': self.plate_number,
            'model_name': self.model_name,
            'manufacturer': self.manufacturer,
            'certified_capacity_kg': self.certified_capacity_kg,
            'certified_length_mm': self.certified_length_mm,
            'certified_width_mm': self.certified_width_mm,
            'certified_height_mm': self.certified_height_mm,
            'certified_axle_count': self.certified_axle_count,
            'certified_volume_m3': round(self.certified_volume_m3, 2),
            'owner_name': self.owner_name,
            'owner_phone': self.owner_phone,
            'violation_count': self.violation_count,
            'status': self.status
        }


class Scan(db.Model):
    __tablename__ = 'scans'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=get_utc_now)
    
    # Sensor Measurement Values
    actual_weight_kg = db.Column(db.Integer, nullable=False)
    measured_length_mm = db.Column(db.Integer, nullable=True, default=10500)
    measured_width_mm = db.Column(db.Integer, nullable=True, default=2500)
    measured_height_mm = db.Column(db.Integer, nullable=True, default=3800)
    measured_axle_count = db.Column(db.Integer, nullable=True, default=3)
    measured_volume_m3 = db.Column(db.Float, nullable=True, default=99.75)
    measured_ground_clearance_mm = db.Column(db.Integer, nullable=True, default=290)
    camera_shape_match_pct = db.Column(db.Float, nullable=True, default=95.0)

    # Parameter Deviation Percentages relative to certified spec
    load_percentage = db.Column(db.Float, nullable=False) # weight_deviation_pct
    weight_deviation_pct = db.Column(db.Float, nullable=True, default=100.0)
    axle_deviation_pct = db.Column(db.Float, nullable=True, default=100.0)
    length_deviation_pct = db.Column(db.Float, nullable=True, default=100.0)
    height_deviation_pct = db.Column(db.Float, nullable=True, default=100.0)
    width_deviation_pct = db.Column(db.Float, nullable=True, default=100.0)
    volume_deviation_pct = db.Column(db.Float, nullable=True, default=100.0)

    # Composite Analytics
    composite_score = db.Column(db.Float, nullable=False, default=100.0)
    classification = db.Column(db.String(30), nullable=False) # "underload" | "moderate" | "overload" | "overload_modification_flag"
    modification_flag = db.Column(db.Boolean, default=False)
    recheck_flag = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.String(255), nullable=True)

    toll_plaza = db.Column(db.String(100), nullable=False, default="Kharegaon Toll Plaza")

    challan = db.relationship('Challan', backref='scan', uselist=False, lazy=True)
    notifications = db.relationship('OfficerNotification', backref='scan', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'vehicle_id': self.vehicle_id,
            'plate_number': self.vehicle.plate_number if self.vehicle else None,
            'model_name': self.vehicle.model_name if self.vehicle else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            
            # Certified Specs
            'certified_capacity_kg': self.vehicle.certified_capacity_kg if self.vehicle else None,
            'certified_length_mm': self.vehicle.certified_length_mm if self.vehicle else None,
            'certified_width_mm': self.vehicle.certified_width_mm if self.vehicle else None,
            'certified_height_mm': self.vehicle.certified_height_mm if self.vehicle else None,
            'certified_axle_count': self.vehicle.certified_axle_count if self.vehicle else None,
            'certified_volume_m3': round(self.vehicle.certified_volume_m3, 2) if self.vehicle else None,

            # Measured Values
            'actual_weight_kg': self.actual_weight_kg,
            'measured_length_mm': self.measured_length_mm,
            'measured_width_mm': self.measured_width_mm,
            'measured_height_mm': self.measured_height_mm,
            'measured_axle_count': self.measured_axle_count,
            'measured_volume_m3': round(self.measured_volume_m3, 2) if self.measured_volume_m3 else None,
            'measured_ground_clearance_mm': self.measured_ground_clearance_mm,
            'camera_shape_match_pct': self.camera_shape_match_pct,

            # Deviations
            'load_percentage': round(self.load_percentage, 1),
            'weight_deviation_pct': round(self.weight_deviation_pct or self.load_percentage, 1),
            'axle_deviation_pct': round(self.axle_deviation_pct or 100.0, 1),
            'length_deviation_pct': round(self.length_deviation_pct or 100.0, 1),
            'height_deviation_pct': round(self.height_deviation_pct or 100.0, 1),
            'width_deviation_pct': round(self.width_deviation_pct or 100.0, 1),
            'volume_deviation_pct': round(self.volume_deviation_pct or 100.0, 1),

            # Score & Classification
            'composite_score': round(self.composite_score, 1),
            'classification': self.classification,
            'modification_flag': bool(self.modification_flag),
            'recheck_flag': bool(self.recheck_flag),
            'image_url': self.image_url,
            'toll_plaza': self.toll_plaza
        }


class Challan(db.Model):
    __tablename__ = 'challans'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False)
    offense_number = db.Column(db.Integer, nullable=False) # 1 or 2+
    fine_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(40), nullable=False, default='pending_rto_verification') 
    # status options: "pending_rto_verification" | "confirmed" | "escalated" | "seizure_ordered" | "dismissed"
    created_at = db.Column(db.DateTime, default=get_utc_now)
    rto_verified_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'vehicle_id': self.vehicle_id,
            'scan_id': self.scan_id,
            'plate_number': self.vehicle.plate_number if self.vehicle else None,
            'model_name': self.vehicle.model_name if self.vehicle else None,
            'owner_name': self.vehicle.owner_name if self.vehicle else None,
            'owner_phone': self.vehicle.owner_phone if self.vehicle else None,
            'offense_number': self.offense_number,
            'fine_amount': self.fine_amount,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'rto_verified_at': self.rto_verified_at.isoformat() if self.rto_verified_at else None,
            'actual_weight_kg': self.scan.actual_weight_kg if self.scan else None,
            'certified_capacity_kg': self.vehicle.certified_capacity_kg if self.vehicle else None,
            'load_percentage': round(self.scan.load_percentage, 1) if self.scan else None,
            'composite_score': round(self.scan.composite_score, 1) if self.scan else None,
            'classification': self.scan.classification if self.scan else None,
            'toll_plaza': self.scan.toll_plaza if self.scan else None
        }


class Officer(db.Model):
    __tablename__ = 'officers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    badge_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    jurisdiction_area = db.Column(db.String(100), nullable=False) # e.g. "Kharegaon Toll Plaza"

    notifications = db.relationship('OfficerNotification', backref='officer', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'badge_id': self.badge_id,
            'phone_number': self.phone_number,
            'jurisdiction_area': self.jurisdiction_area
        }


class OfficerNotification(db.Model):
    __tablename__ = 'officer_notifications'

    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('officers.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(30), default='pending_inspection') # "pending_inspection" | "confirmed" | "dismissed"
    created_at = db.Column(db.DateTime, default=get_utc_now)

    vehicle = db.relationship('Vehicle', lazy=True)
    scan_ref = db.relationship('Scan', foreign_keys=[scan_id], lazy=True, overlaps="notifications,scan")

    def to_dict(self):
        return {
            'id': self.id,
            'officer_id': self.officer_id,
            'vehicle_id': self.vehicle_id,
            'scan_id': self.scan_id,
            'plate_number': self.vehicle.plate_number if self.vehicle else None,
            'model_name': self.vehicle.model_name if self.vehicle else None,
            'message': self.message,
            'is_read': self.is_read,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'scan': self.scan_ref.to_dict() if self.scan_ref else None,
            'challan': self.scan_ref.challan.to_dict() if (self.scan_ref and self.scan_ref.challan) else None
        }
