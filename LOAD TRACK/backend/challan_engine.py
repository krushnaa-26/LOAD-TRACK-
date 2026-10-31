import logging
from datetime import datetime, timezone
from models import db, Challan, Vehicle, Scan
from sms import send_challan_sms

logger = logging.getLogger("loadtrack.challan_engine")

def calculate_fine(actual_weight, certified_capacity, offense_number, is_modification=False):
    """
    Calculates fine based on percentage of overload and offense history.
    Base fine = ₹5,000 + ₹500 per each full 5% over 100% threshold.
    Repeat offense (offense_number > 1) = 3x multiplier.
    If unauthorized structural modification is detected, add ₹5,000 extra fine.
    """
    overload_pct = max(0.0, ((actual_weight - certified_capacity) / certified_capacity) * 100.0)
    five_pct_blocks = int(overload_pct // 5)
    
    base_fine = 5000 + (five_pct_blocks * 500)
    if is_modification:
        base_fine += 5000 # Additional penalty for unauthorized body modification
    
    if offense_number > 1:
        fine = base_fine * 3
    else:
        fine = base_fine
        
    return int(fine)


def process_overload(scan, vehicle):
    """
    Processes an overload/modification scan: creates challan, updates vehicle violation counts & status,
    dispatches SMS notifications, and logs step-by-step actions for audit transparency.
    """
    current_violations = vehicle.violation_count
    offense_number = current_violations + 1

    is_modification = (scan.classification == 'overload_modification_flag' or scan.modification_flag)
    fine_amount = calculate_fine(scan.actual_weight_kg, vehicle.certified_capacity_kg, offense_number, is_modification)
    
    logger.info(f"--- PROCESSING OVERLOAD/MODIFICATION FOR VEHICLE {vehicle.plate_number} ---")
    logger.info(f"Current Violation Count: {current_violations} -> New Offense Number: {offense_number}")
    logger.info(f"Classification: {scan.classification} | Composite Score: {scan.composite_score}")
    logger.info(f"Actual Weight: {scan.actual_weight_kg}kg vs Certified: {vehicle.certified_capacity_kg}kg ({round(scan.load_percentage, 1)}%)")
    logger.info(f"Calculated Fine: Rs. {fine_amount}")

    reason_str = "unauthorized structural modification & overload" if is_modification else "gross weight overload"

    if current_violations == 0:
        # First offense
        challan_status = "pending_rto_verification"
        vehicle.status = "1st_offense"
        vehicle.violation_count = 1
        
        sms_msg = (
            f"LOAD TRACK ALERT: Vehicle {vehicle.plate_number} flagged for {reason_str} "
            f"(Score: {scan.composite_score}, Load: {round(scan.load_percentage, 1)}%) at {scan.toll_plaza}. "
            f"Challan pending RTO verification. Fine: Rs. {fine_amount:,}."
        )
    else:
        # Escalated repeat offense (2+)
        challan_status = "escalated"
        vehicle.status = "escalated"
        vehicle.violation_count += 1
        
        sms_msg = (
            f"LOAD TRACK NOTICE: Vehicle {vehicle.plate_number} - repeat violation ({reason_str}). "
            f"Escalated fine Rs. {fine_amount:,} issued. Seizure order initiated. "
            f"Report to nearest RTO within 7 days."
        )

    # Check if a challan already exists for this scan
    existing_challan = Challan.query.filter_by(scan_id=scan.id).first()
    if existing_challan:
        return existing_challan

    # Create new challan record
    challan = Challan(
        vehicle_id=vehicle.id,
        scan_id=scan.id,
        offense_number=offense_number,
        fine_amount=fine_amount,
        status=challan_status,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    db.session.add(challan)
    db.session.commit()
    
    logger.info(f"Created Challan #{challan.id} with status '{challan_status}'")
    logger.info(f"Updated Vehicle {vehicle.plate_number} status to '{vehicle.status}'")

    # Trigger SMS notification
    sms_res = send_challan_sms(vehicle.owner_phone, sms_msg)
    logger.info(f"SMS Dispatch Status: {sms_res.get('mode', 'unknown')}")

    challan.sms_dispatch = sms_res
    return challan
