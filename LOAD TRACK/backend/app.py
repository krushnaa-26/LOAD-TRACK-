import os
import sys
from datetime import datetime, date, timezone
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, Vehicle, Scan, Challan, Officer, OfficerNotification
from composite_score import composite_score, classify, deviation_pct
from ocr import extract_plate_number
from challan_engine import process_overload
from sensors import (
    read_weight,
    read_axle,
    read_dimensions,
    read_height,
    read_clearance,
    read_shape_match
)

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'loadtrack_default_secret_key_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'loadtrack.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['SAMPLE_FOLDER'] = os.path.join(os.path.dirname(__file__), 'sample_images')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SAMPLE_FOLDER'], exist_ok=True)

# Enable CORS for frontend cross-origin requests
CORS(app, supports_credentials=True)

db.init_app(app)

# Ensure DB tables exist on app startup
with app.app_context():
    db.create_all()


# Helper function to find or auto-create vehicle by plate
def get_or_create_vehicle(plate_number):
    clean_plate = plate_number.strip().upper()
    vehicle = Vehicle.query.filter_by(plate_number=clean_plate).first()
    if not vehicle:
        # Create default mock vehicle record with certified specs
        vehicle = Vehicle(
            plate_number=clean_plate,
            model_name="Tata Signa Commercial",
            manufacturer="Tata Motors",
            certified_capacity_kg=28000,
            certified_length_mm=10500,
            certified_width_mm=2500,
            certified_height_mm=3800,
            certified_axle_count=3,
            certified_volume_m3=99.75,
            owner_name="Transport Partner",
            owner_phone="+919876543210",
            violation_count=0,
            status="compliant"
        )
        db.session.add(vehicle)
        db.session.commit()
    return vehicle


# Helper function to assign officer notification
def notify_officers_for_scan(scan, vehicle, message):
    try:
        # Find officers in matching jurisdiction
        officers = Officer.query.filter(Officer.jurisdiction_area == scan.toll_plaza).all()
        if not officers:
            # Fallback to all officers if specific plaza has no matching officer assigned
            officers = Officer.query.all()
            
        for officer in officers:
            # Check if notification already exists for this scan and officer
            existing = OfficerNotification.query.filter_by(officer_id=officer.id, scan_id=scan.id).first()
            if not existing:
                notif = OfficerNotification(
                    officer_id=officer.id,
                    vehicle_id=vehicle.id,
                    scan_id=scan.id,
                    message=message,
                    is_read=False,
                    status='pending_inspection'
                )
                db.session.add(notif)
        db.session.commit()
    except Exception as err:
        print(f"Error creating officer notification: {err}")


# Serve Main Frontend index.html
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

# Serve RTO Officer App HTML directly or from rto-app subfolder
@app.route('/rto-app/')
@app.route('/rto-app/index.html')
def serve_rto_app():
    rto_path = os.path.join(app.static_folder, 'rto-app')
    return send_from_directory(rto_path, 'index.html')

@app.route('/rto-app/<path:filename>')
def serve_rto_static(filename):
    rto_path = os.path.join(app.static_folder, 'rto-app')
    return send_from_directory(rto_path, filename)


# Endpoint 1: POST /api/scan (Updated with Multi-Parameter Sensors & Composite Scoring)
@app.route('/api/scan', methods=['POST'])
def scan_vehicle():
    try:
        data = request.form if request.form else (request.get_json(silent=True) or {})
        
        toll_plaza = data.get('toll_plaza', 'Kharegaon Toll Plaza').strip()
        manual_plate = data.get('plate_number', '').strip()
        sim_mode = data.get('simulation_mode', 'normal')

        plate_detected = None
        raw_ocr_text = None
        ocr_confidence = 0.0
        image_url = None

        # Check uploaded file
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Run OCR engine
            ocr_res = extract_plate_number(filepath)
            if ocr_res.get('success'):
                plate_detected = ocr_res.get('plate_number')
                raw_ocr_text = ocr_res.get('raw_text')
                ocr_confidence = ocr_res.get('confidence', 1.0)
            
            image_url = f"/api/uploads/{filename}"

        elif data.get('sample_filename'):
            sample_fn = data.get('sample_filename')
            filepath = os.path.join(app.config['SAMPLE_FOLDER'], sample_fn)
            ocr_res = extract_plate_number(filepath)
            if ocr_res.get('success'):
                plate_detected = ocr_res.get('plate_number')
                raw_ocr_text = ocr_res.get('raw_text')
                ocr_confidence = ocr_res.get('confidence', 1.0)
            image_url = f"/api/samples/{sample_fn}"

        final_plate = plate_detected or manual_plate

        if not final_plate:
            return jsonify({
                'success': False, 
                'error': 'License plate could not be detected from image and no manual plate was supplied.'
            }), 422

        # Vehicle DB Lookup
        vehicle = get_or_create_vehicle(final_plate)

        # Extract helper for form & json data
        def parse_int(key):
            try:
                if request.form and key in request.form:
                    return int(request.form[key])
                if request.is_json and request.json and key in request.json:
                    return int(request.json[key])
                if isinstance(data, dict) and key in data and data[key] is not None:
                    return int(data[key])
            except (ValueError, TypeError):
                pass
            return None

        # ---------------- SENSOR SIMULATION & CAPTURE ----------------
        # 1. Weight Sensor (Piezoelectric WIM)
        provided_weight = parse_int('weight')
        if provided_weight and provided_weight > 0:
            actual_weight = provided_weight
        else:
            actual_weight = read_weight(vehicle.certified_capacity_kg, simulation_mode=sim_mode)

        # 2. Axle Counter Sensor
        provided_axles = parse_int('measured_axle_count')
        measured_axles = provided_axles if (provided_axles and provided_axles > 0) else read_axle(vehicle.certified_axle_count, sim_mode)

        # 3. LiDAR Dimension Sensor (Length & Width)
        provided_l = parse_int('measured_length_mm')
        provided_w = parse_int('measured_width_mm')
        if provided_l and provided_w:
            measured_l, measured_w = provided_l, provided_w
        else:
            measured_l, measured_w = read_dimensions(vehicle.certified_length_mm, vehicle.certified_width_mm, sim_mode)

        # 4. IR Height Curtain Sensor
        provided_h = parse_int('measured_height_mm')
        measured_h = provided_h if (provided_h and provided_h > 0) else read_height(vehicle.certified_height_mm, sim_mode)

        # 5. Volume Calculation (L × W × H in m³)
        measured_volume = round((measured_l * measured_w * measured_h) / 1e9, 2)

        # 6. IR Ground Clearance Sensor
        weight_dev = deviation_pct(actual_weight, vehicle.certified_capacity_kg)
        measured_clearance = read_clearance(300, weight_dev)

        # 7. CNN Visual Comparison Camera (Shape Match %)
        is_mod_sim = (sim_mode == 'modification' or measured_axles != vehicle.certified_axle_count or measured_h > vehicle.certified_height_mm * 1.15)
        shape_match_pct = read_shape_match(is_modified=is_mod_sim)

        # ---------------- DEVIATIONS & COMPOSITE SCORE ENGINE ----------------
        deviations = {
            "weight": weight_dev,
            "axle": deviation_pct(measured_axles, vehicle.certified_axle_count),
            "length": deviation_pct(measured_l, vehicle.certified_length_mm),
            "width": deviation_pct(measured_w, vehicle.certified_width_mm),
            "height": deviation_pct(measured_h, vehicle.certified_height_mm),
            "volume": deviation_pct(measured_volume, vehicle.certified_volume_m3)
        }

        score = composite_score(deviations)
        classification = classify(score, deviations)
        modification_flag = (classification == "overload_modification_flag")

        # Record Scan in Database
        scan = Scan(
            vehicle_id=vehicle.id,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            actual_weight_kg=actual_weight,
            measured_length_mm=measured_l,
            measured_width_mm=measured_w,
            measured_height_mm=measured_h,
            measured_axle_count=measured_axles,
            measured_volume_m3=measured_volume,
            measured_ground_clearance_mm=measured_clearance,
            camera_shape_match_pct=shape_match_pct,

            load_percentage=weight_dev,
            weight_deviation_pct=deviations["weight"],
            axle_deviation_pct=deviations["axle"],
            length_deviation_pct=deviations["length"],
            height_deviation_pct=deviations["height"],
            width_deviation_pct=deviations["width"],
            volume_deviation_pct=deviations["volume"],

            composite_score=score,
            classification=classification,
            modification_flag=modification_flag,
            recheck_flag=False,
            image_url=image_url,
            toll_plaza=toll_plaza
        )
        db.session.add(scan)
        db.session.commit()

        # Challan Escalation & RTO Notification Trigger
        challan_data = None
        if classification in ['overload', 'overload_modification_flag']:
            challan = process_overload(scan, vehicle)
            challan_dict = challan.to_dict()
            if hasattr(challan, 'sms_dispatch'):
                challan_dict['sms_dispatch'] = challan.sms_dispatch
            challan_data = challan_dict

            # Create Notification for RTO Officers
            msg = f"OVERLOAD/MODIFICATION FLAGGED: Vehicle {vehicle.plate_number} composite score {score}% at {toll_plaza}."
            notify_officers_for_scan(scan, vehicle, msg)

        return jsonify({
            'success': True,
            'scan': scan.to_dict(),
            'vehicle': vehicle.to_dict(),
            'classification': classification,
            'composite_score': score,
            'deviations': deviations,
            'modification_flag': modification_flag,
            'ocr': {
                'detected_plate': plate_detected,
                'raw_text': raw_ocr_text,
                'confidence': round(ocr_confidence, 2) if ocr_confidence else 0.0,
                'image_url': image_url
            },
            'challan': challan_data
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f"Internal scan error: {str(e)}"}), 500


# Endpoint 2: GET /api/scans (Fetch Scans List for Toll Gate Dashboard)
@app.route('/api/scans', methods=['GET'])
def get_scans():
    limit = request.args.get('limit', 50, type=int)
    scans = Scan.query.order_by(Scan.timestamp.desc()).limit(limit).all()
    return jsonify({'success': True, 'scans': [s.to_dict() for s in scans]}), 200


# Endpoint 3: POST /api/scan/<id>/recheck (Toll Operator Flag for Re-check)
@app.route('/api/scan/<int:scan_id>/recheck', methods=['POST'])
def flag_scan_recheck(scan_id):
    scan = db.session.get(Scan, scan_id)
    if not scan:
        return jsonify({'success': False, 'error': f"Scan #{scan_id} not found."}), 404

    scan.recheck_flag = True
    vehicle = scan.vehicle
    
    # Notify RTO Officer for manual human inspection
    msg = f"MANUAL RE-CHECK REQUEST: Toll Operator requested review for Vehicle {vehicle.plate_number} (Scan #{scan.id})."
    notify_officers_for_scan(scan, vehicle, msg)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Scan #{scan_id} successfully flagged for human officer review.",
        'scan': scan.to_dict()
    }), 200


# Endpoint 4: GET /api/vehicles
@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    vehicles = Vehicle.query.order_by(Vehicle.id.desc()).all()
    return jsonify({'success': True, 'vehicles': [v.to_dict() for v in vehicles]}), 200


# Endpoint 5: GET /api/vehicles/<plate>
@app.route('/api/vehicles/<plate>', methods=['GET'])
def get_vehicle_detail(plate):
    clean_plate = plate.strip().upper()
    vehicle = Vehicle.query.filter_by(plate_number=clean_plate).first()
    if not vehicle:
        return jsonify({'success': False, 'error': f"Vehicle with plate '{plate}' not found."}), 404

    scans = Scan.query.filter_by(vehicle_id=vehicle.id).order_by(Scan.timestamp.desc()).all()
    challans = Challan.query.filter_by(vehicle_id=vehicle.id).order_by(Challan.created_at.desc()).all()

    return jsonify({
        'success': True,
        'vehicle': vehicle.to_dict(),
        'scans': [s.to_dict() for s in scans],
        'challans': [c.to_dict() for c in challans]
    }), 200


# Endpoint 6: GET /api/challans
@app.route('/api/challans', methods=['GET'])
def get_challans():
    status_filter = request.args.get('status', '').strip()
    query = Challan.query.order_by(Challan.created_at.desc())
    if status_filter:
        query = query.filter(Challan.status == status_filter)
    challans = query.all()
    return jsonify({'success': True, 'challans': [c.to_dict() for c in challans]}), 200


# Endpoint 7: POST /api/challans/<id>/verify (Verify Challan & Update Vehicle Status)
@app.route('/api/challans/<int:challan_id>/verify', methods=['POST'])
def verify_challan(challan_id):
    challan = db.session.get(Challan, challan_id)
    if not challan:
        return jsonify({'success': False, 'error': f"Challan #{challan_id} not found."}), 404

    challan.status = 'confirmed'
    challan.rto_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Recalculate vehicle status
    vehicle = db.session.get(Vehicle, challan.vehicle_id)
    if vehicle:
        pending_escalated = Challan.query.filter(
            Challan.vehicle_id == vehicle.id,
            Challan.id != challan.id,
            Challan.status.in_(['escalated', 'seizure_ordered'])
        ).count()
        
        pending_first = Challan.query.filter(
            Challan.vehicle_id == vehicle.id,
            Challan.id != challan.id,
            Challan.status == 'pending_rto_verification'
        ).count()

        if pending_escalated > 0:
            vehicle.status = 'escalated'
        elif pending_first > 0:
            vehicle.status = '1st_offense'
        else:
            vehicle.status = 'compliant'

    # Update associated Officer Notification status if any
    notif = OfficerNotification.query.filter_by(scan_id=challan.scan_id).first()
    if notif:
        notif.status = 'confirmed'
        notif.is_read = True

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Challan #{challan_id} successfully verified by RTO.",
        'challan': challan.to_dict(),
        'vehicle': vehicle.to_dict() if vehicle else None
    }), 200


# ---------------- RTO OFFICER APP ENDPOINTS ----------------

# Officer Login Endpoint: POST /api/officer/login
@app.route('/api/officer/login', methods=['POST'])
def officer_login():
    data = request.get_json(silent=True) or request.form
    badge_id = data.get('badge_id', '').strip().upper()
    password = data.get('password', '').strip()

    if not badge_id or not password:
        return jsonify({'success': False, 'error': 'Badge ID and password are required.'}), 400

    officer = Officer.query.filter_by(badge_id=badge_id).first()
    if not officer or not check_password_hash(officer.password_hash, password):
        return jsonify({'success': False, 'error': 'Invalid Badge ID or Password.'}), 401

    session['officer_id'] = officer.id
    session['badge_id'] = officer.badge_id

    return jsonify({
        'success': True,
        'message': f"Welcome Officer {officer.name}!",
        'officer': officer.to_dict(),
        'session_token': f"badge_token_{officer.id}_{officer.badge_id}"
    }), 200


# Get Current Logged-in Officer: GET /api/officer/me
@app.route('/api/officer/me', methods=['GET'])
def get_current_officer():
    officer_id = session.get('officer_id')
    badge_id = request.args.get('badge_id')

    officer = None
    if officer_id:
        officer = db.session.get(Officer, officer_id)
    elif badge_id:
        officer = Officer.query.filter_by(badge_id=badge_id.strip().upper()).first()

    if not officer:
        # Default to first officer for ease of demonstration if requested
        officer = Officer.query.first()

    if not officer:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    return jsonify({'success': True, 'officer': officer.to_dict()}), 200


# Officer Logout: POST /api/officer/logout
@app.route('/api/officer/logout', methods=['POST'])
def officer_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Successfully logged out.'}), 200


# Get Officer Notifications: GET /api/officer/notifications
@app.route('/api/officer/notifications', methods=['GET'])
def get_officer_notifications():
    badge_id = request.args.get('badge_id')
    officer = None
    if badge_id:
        officer = Officer.query.filter_by(badge_id=badge_id.strip().upper()).first()
    elif session.get('officer_id'):
        officer = db.session.get(Officer, session['officer_id'])

    if not officer:
        officer = Officer.query.first() # Default fallback for live demo

    query = OfficerNotification.query
    if officer:
        query = query.filter_by(officer_id=officer.id)
    
    notifications = query.order_by(OfficerNotification.created_at.desc()).all()
    unread_count = sum(1 for n in notifications if not n.is_read)

    return jsonify({
        'success': True,
        'unread_count': unread_count,
        'notifications': [n.to_dict() for n in notifications]
    }), 200


# Mark Notification as Read: POST /api/officer/notifications/<id>/read
@app.route('/api/officer/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    notif = db.session.get(OfficerNotification, notif_id)
    if not notif:
        return jsonify({'success': False, 'error': f"Notification #{notif_id} not found."}), 404

    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'notification': notif.to_dict()}), 200


# Get Full Inspection Detail: GET /api/officer/inspections/<notif_id>
@app.route('/api/officer/inspections/<int:notif_id>', methods=['GET'])
def get_inspection_detail(notif_id):
    notif = db.session.get(OfficerNotification, notif_id)
    if not notif:
        return jsonify({'success': False, 'error': f"Notification #{notif_id} not found."}), 404

    scan = notif.scan_ref
    vehicle = notif.vehicle
    challan = scan.challan if scan else None

    # Generate registered vs camera visual comparison links
    registered_photo = f"https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?auto=format&fit=crop&w=600&q=80"
    scan_photo = scan.image_url if (scan and scan.image_url) else registered_photo

    return jsonify({
        'success': True,
        'notification': notif.to_dict(),
        'scan': scan.to_dict() if scan else None,
        'vehicle': vehicle.to_dict() if vehicle else None,
        'challan': challan.to_dict() if challan else None,
        'images': {
            'registered_rto_photo': registered_photo,
            'toll_camera_photo': scan_photo
        }
    }), 200


# Confirm Violation & Verify Challan: POST /api/officer/inspections/<notif_id>/verify
@app.route('/api/officer/inspections/<int:notif_id>/verify', methods=['POST'])
def confirm_inspection_violation(notif_id):
    notif = db.session.get(OfficerNotification, notif_id)
    if not notif:
        return jsonify({'success': False, 'error': f"Notification #{notif_id} not found."}), 404

    scan = notif.scan_ref
    vehicle = notif.vehicle
    
    # Verify/confirm existing challan or issue one if absent
    if scan and scan.challan:
        challan = scan.challan
        challan.status = 'confirmed'
        challan.rto_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    elif scan and vehicle:
        challan = process_overload(scan, vehicle)
        challan.status = 'confirmed'
        challan.rto_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)

    notif.status = 'confirmed'
    notif.is_read = True

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Violation confirmed! Challan for vehicle {vehicle.plate_number if vehicle else ''} verified.",
        'notification': notif.to_dict()
    }), 200


# Dismiss Violation (False Positive): POST /api/officer/inspections/<notif_id>/dismiss
@app.route('/api/officer/inspections/<int:notif_id>/dismiss', methods=['POST'])
def dismiss_inspection_violation(notif_id):
    notif = db.session.get(OfficerNotification, notif_id)
    if not notif:
        return jsonify({'success': False, 'error': f"Notification #{notif_id} not found."}), 404

    scan = notif.scan_ref
    vehicle = notif.vehicle

    notif.status = 'dismissed'
    notif.is_read = True

    if scan:
        scan.recheck_flag = False
        scan.classification = 'false_positive'
        if scan.challan:
            scan.challan.status = 'dismissed'

    # Do not increment vehicle's violation count (revert count if first offense challan was created)
    if vehicle and vehicle.violation_count > 0:
        active_confirmed = Challan.query.filter(
            Challan.vehicle_id == vehicle.id,
            Challan.status.in_(['confirmed', 'escalated'])
        ).count()
        if active_confirmed == 0:
            vehicle.status = 'compliant'

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Inspection #{notif_id} dismissed as false positive. No penalty applied.",
        'notification': notif.to_dict()
    }), 200


# Get Officer Inspection History: GET /api/officer/history
@app.route('/api/officer/history', methods=['GET'])
def get_officer_history():
    badge_id = request.args.get('badge_id')
    officer = None
    if badge_id:
        officer = Officer.query.filter_by(badge_id=badge_id.strip().upper()).first()
    elif session.get('officer_id'):
        officer = db.session.get(Officer, session['officer_id'])

    if not officer:
        officer = Officer.query.first()

    query = OfficerNotification.query.filter(OfficerNotification.status.in_(['confirmed', 'dismissed']))
    if officer:
        query = query.filter_by(officer_id=officer.id)

    history = query.order_by(OfficerNotification.created_at.desc()).all()
    return jsonify({'success': True, 'history': [h.to_dict() for h in history]}), 200


# Endpoint 8: GET /api/stats
@app.route('/api/stats', methods=['GET'])
def get_dashboard_stats():
    today = date.today()
    start_of_day = datetime(today.year, today.month, today.day)

    scanned_today = Scan.query.filter(Scan.timestamp >= start_of_day).count()
    total_scans = Scan.query.count()

    overloads_today = Scan.query.filter(Scan.timestamp >= start_of_day, Scan.classification.in_(['overload', 'overload_modification_flag'])).count()
    total_overloads = Scan.query.filter(Scan.classification.in_(['overload', 'overload_modification_flag'])).count()

    active_challans = Challan.query.filter(Challan.status.in_(['pending_rto_verification', 'confirmed'])).count()
    seizure_orders = Challan.query.filter(Challan.status.in_(['escalated', 'seizure_ordered'])).count()

    return jsonify({
        'success': True,
        'stats': {
            'scanned_today': scanned_today,
            'total_scans': total_scans,
            'overloads_today': overloads_today,
            'total_overloads': total_overloads,
            'active_challans': active_challans,
            'seizure_orders': seizure_orders
        }
    }), 200


# Endpoint 9: GET /api/samples
@app.route('/api/samples', methods=['GET'])
def list_sample_images():
    sample_dir = app.config['SAMPLE_FOLDER']
    files = []
    if os.path.exists(sample_dir):
        for f in os.listdir(sample_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                plate_formatted = f.replace('_', ' ').replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
                files.append({
                    'filename': f,
                    'plate': plate_formatted,
                    'url': f"/api/samples/{f}"
                })
    return jsonify({'success': True, 'samples': files}), 200


# Serve Uploads & Sample Images statically
@app.route('/api/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/samples/<filename>')
def serve_sample(filename):
    return send_from_directory(app.config['SAMPLE_FOLDER'], filename)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"Starting LOAD TRACK Server on http://localhost:{port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
