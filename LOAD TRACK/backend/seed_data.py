import os
import sys
from datetime import datetime, timedelta, timezone
import random
from PIL import Image, ImageDraw, ImageFont
from werkzeug.security import generate_password_hash

# Ensure backend path is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Vehicle, Scan, Challan, Officer, OfficerNotification
from composite_score import composite_score, classify, deviation_pct
from challan_engine import process_overload

# 18 Realistic Indian Truck Models & Specs (with dimensions & axle counts)
SAMPLE_TRUCKS = [
    {"plate": "MH 20 BT 4471", "model": "Tata Signa 5530.S", "mfr": "Tata Motors", "capacity": 35000, "length": 12800, "width": 2500, "height": 3850, "axles": 5, "owner": "Ramesh Logistics Pvt Ltd", "phone": "+919820112233"},
    {"plate": "KA 05 MC 8812", "model": "Ashok Leyland 2820", "mfr": "Ashok Leyland", "capacity": 28000, "length": 10500, "width": 2500, "height": 3600, "axles": 3, "owner": "Venkateshwara Transport", "phone": "+919448012345"},
    {"plate": "MH 12 QW 9901", "model": "BharatBenz 3528C", "mfr": "Daimler India", "capacity": 35000, "length": 11200, "width": 2500, "height": 3750, "axles": 4, "owner": "Sahyadri Freightlines", "phone": "+919890123456"},
    {"plate": "DL 01 GB 3342", "model": "Eicher Pro 6028", "mfr": "VE Commercial Vehicles", "capacity": 28000, "length": 10200, "width": 2500, "height": 3550, "axles": 3, "owner": "Northern Cargo Movers", "phone": "+919810987654"},
    {"plate": "GJ 06 AX 5510", "model": "Mahindra Blazo X 28", "mfr": "Mahindra & Mahindra", "capacity": 28000, "length": 10400, "width": 2500, "height": 3600, "axles": 3, "owner": "Gujarat Heavy Haulers", "phone": "+919725011223"},
    {"plate": "HR 38 BX 1109", "model": "Tata LPT 1613", "mfr": "Tata Motors", "capacity": 16000, "length": 8600, "width": 2400, "height": 3300, "axles": 2, "owner": "Apex Highway Logistics", "phone": "+919812345678"},
    {"plate": "MH 04 ER 7723", "model": "Ashok Leyland 3520", "mfr": "Ashok Leyland", "capacity": 35000, "length": 11500, "width": 2500, "height": 3700, "axles": 4, "owner": "Thane Container Services", "phone": "+919821098765"},
    {"plate": "TN 09 CK 4040", "model": "BharatBenz 2823R", "mfr": "Daimler India", "capacity": 28000, "length": 10500, "width": 2500, "height": 3600, "axles": 3, "owner": "Chennai Express Carriers", "phone": "+919444011223"},
    {"plate": "WB 23 CD 6611", "model": "Mahindra Blazo X 35", "mfr": "Mahindra & Mahindra", "capacity": 35000, "length": 11800, "width": 2500, "height": 3800, "axles": 4, "owner": "Bengal Coal Carriers", "phone": "+919830055443"},
    {"plate": "AP 16 TX 9087", "model": "Tata Prima 4928.S", "mfr": "Tata Motors", "capacity": 49000, "length": 13500, "width": 2550, "height": 3950, "axles": 5, "owner": "Amaravati Bulk Carriers", "phone": "+919848011223"},
    {"plate": "RJ 14 GC 2234", "model": "Ashok Leyland 4220", "mfr": "Ashok Leyland", "capacity": 42000, "length": 12200, "width": 2500, "height": 3800, "axles": 5, "owner": "Rajputana Heavy Freight", "phone": "+919414012345"},
    {"plate": "TS 08 UV 6789", "model": "Eicher Pro 8035", "mfr": "VE Commercial Vehicles", "capacity": 35000, "length": 11200, "width": 2500, "height": 3750, "axles": 4, "owner": "Deccan Mining Movers", "phone": "+919849098765"},
    {"plate": "MH 43 CC 1234", "model": "Tata Signa 4825.TK", "mfr": "Tata Motors", "capacity": 47500, "length": 13200, "width": 2550, "height": 3900, "axles": 5, "owner": "Navi Mumbai Infra Logistics", "phone": "+919867012345"},
    {"plate": "UP 14 DT 5432", "model": "BharatBenz 5528T", "mfr": "Daimler India", "capacity": 49000, "length": 13600, "width": 2550, "height": 3950, "axles": 5, "owner": "Ganga Express Freight", "phone": "+919415098765"},
    {"plate": "MP 09 HZ 8765", "model": "Ashok Leyland 5525", "mfr": "Ashok Leyland", "capacity": 49000, "length": 13500, "width": 2550, "height": 3900, "axles": 5, "owner": "Malwa Highway Lines", "phone": "+919826011223"},
    {"plate": "KL 07 BQ 3456", "model": "Tata LPT 2518", "mfr": "Tata Motors", "capacity": 25000, "length": 9800, "width": 2450, "height": 3500, "axles": 3, "owner": "Cochin Port Cargo Ltd", "phone": "+919847054321"},
    {"plate": "OD 02 AZ 9988", "model": "Mahindra Blazo X 49", "mfr": "Mahindra & Mahindra", "capacity": 49000, "length": 13400, "width": 2550, "height": 3900, "axles": 5, "owner": "Kalinga Mineral Transport", "phone": "+919437012345"},
    {"plate": "PB 10 CP 7788", "model": "Eicher Pro 6037", "mfr": "VE Commercial Vehicles", "capacity": 37000, "length": 11900, "width": 2500, "height": 3800, "axles": 4, "owner": "Punjab Agri Haulers", "phone": "+919814098765"}
]

# RTO Officers across jurisdictions
SAMPLE_OFFICERS = [
    {"name": "Insp. Rajesh Sharma", "badge": "RTO-MH04-101", "phone": "+919820011111", "jurisdiction": "Kharegaon Toll Plaza"},
    {"name": "Insp. Ananya Patel", "badge": "RTO-MH07-102", "phone": "+919820022222", "jurisdiction": "Vashi Toll Naka"},
    {"name": "Insp. Suresh Deshmukh", "badge": "RTO-MH12-103", "phone": "+919820033333", "jurisdiction": "Khed-Shivapur Toll Plaza"},
    {"name": "Insp. Vikram Singh", "badge": "RTO-PB10-104", "phone": "+919820044444", "jurisdiction": "Gharota Toll Plaza"}
]


def generate_sample_plate_image(plate_text, output_path):
    """
    Generates a realistic Indian yellow/white license plate image for testing OCR.
    """
    width, height = 480, 160
    img = Image.new('RGB', (width, height), color=(255, 204, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([5, 5, width-5, height-5], outline=(0, 0, 0), width=6)
    
    try:
        font = ImageFont.truetype("arial.ttf", 46)
        small_font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        
    draw.rectangle([15, 15, 55, height-15], fill=(230, 230, 230), outline=(0, 0, 0), width=2)
    draw.text((22, height//2 - 15), "IND", fill=(0, 51, 153), font=small_font)
    
    text_bbox = draw.textbbox((0, 0), plate_text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    
    x = 65 + ((width - 80) - text_w) // 2
    y = (height - text_h) // 2 - 5
    
    draw.text((x, y), plate_text, fill=(0, 0, 0), font=font)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)


def seed_database():
    with app.app_context():
        print("Dropping existing database tables...")
        db.drop_all()
        print("Creating fresh database schema...")
        db.create_all()

        print("\n1. Seeding 4 RTO Officers...")
        officers_created = []
        for o in SAMPLE_OFFICERS:
            officer = Officer(
                name=o["name"],
                badge_id=o["badge"],
                phone_number=o["phone"],
                password_hash=generate_password_hash("password123"), # Default password
                jurisdiction_area=o["jurisdiction"]
            )
            db.session.add(officer)
            officers_created.append(officer)
        db.session.commit()
        print(f"Created {len(officers_created)} RTO Officers (Password: password123)")

        print("\n2. Seeding 18 Vehicles & generating sample plate images...")
        sample_img_dir = os.path.join(os.path.dirname(__file__), "sample_images")
        os.makedirs(sample_img_dir, exist_ok=True)

        vehicles_created = []
        for item in SAMPLE_TRUCKS:
            vol = (item["length"] * item["width"] * item["height"]) / 1e9
            vehicle = Vehicle(
                plate_number=item["plate"],
                model_name=item["model"],
                manufacturer=item["mfr"],
                certified_capacity_kg=item["capacity"],
                certified_length_mm=item["length"],
                certified_width_mm=item["width"],
                certified_height_mm=item["height"],
                certified_axle_count=item["axles"],
                certified_volume_m3=round(vol, 2),
                owner_name=item["owner"],
                owner_phone=item["phone"],
                violation_count=0,
                status="compliant"
            )
            db.session.add(vehicle)
            db.session.flush()
            vehicles_created.append(vehicle)

            filename = f"{item['plate'].replace(' ', '_')}.jpg"
            img_path = os.path.join(sample_img_dir, filename)
            generate_sample_plate_image(item["plate"], img_path)

        db.session.commit()
        print(f"Successfully seeded {len(vehicles_created)} vehicles with full certified specs!")

        print("\n3. Seeding realistic multi-parameter scan and challan history...")
        toll_plazas = ["Kharegaon Toll Plaza", "Vashi Toll Naka", "Khed-Shivapur Toll Plaza", "Gharota Toll Plaza"]
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        # Helper to create scan with complete multi-sensor readings
        def create_full_scan(v, actual_w, measured_l, measured_w, measured_h, measured_axles, shape_match, plaza, hours_ago):
            vol = round((measured_l * measured_w * measured_h) / 1e9, 2)
            devs = {
                "weight": deviation_pct(actual_w, v.certified_capacity_kg),
                "axle": deviation_pct(measured_axles, v.certified_axle_count),
                "length": deviation_pct(measured_l, v.certified_length_mm),
                "width": deviation_pct(measured_w, v.certified_width_mm),
                "height": deviation_pct(measured_h, v.certified_height_mm),
                "volume": deviation_pct(vol, v.certified_volume_m3)
            }
            sc = composite_score(devs)
            cls = classify(sc, devs)
            mod = (cls == "overload_modification_flag")

            filename = f"{v.plate_number.replace(' ', '_')}.jpg"
            image_url = f"/api/samples/{filename}"

            scan = Scan(
                vehicle_id=v.id,
                timestamp=now_utc - timedelta(hours=hours_ago),
                actual_weight_kg=actual_w,
                measured_length_mm=measured_l,
                measured_width_mm=measured_w,
                measured_height_mm=measured_h,
                measured_axle_count=measured_axles,
                measured_volume_m3=vol,
                measured_ground_clearance_mm=260 if devs["weight"] > 100 else 300,
                camera_shape_match_pct=shape_match,

                load_percentage=devs["weight"],
                weight_deviation_pct=devs["weight"],
                axle_deviation_pct=devs["axle"],
                length_deviation_pct=devs["length"],
                height_deviation_pct=devs["height"],
                width_deviation_pct=devs["width"],
                volume_deviation_pct=devs["volume"],

                composite_score=sc,
                classification=cls,
                modification_flag=mod,
                recheck_flag=False,
                image_url=image_url,
                toll_plaza=plaza
            )
            db.session.add(scan)
            db.session.flush()

            if cls in ['overload', 'overload_modification_flag']:
                ch = process_overload(scan, v)
                # Create Officer Notification
                off = Officer.query.filter_by(jurisdiction_area=plaza).first() or officers_created[0]
                notif = OfficerNotification(
                    officer_id=off.id,
                    vehicle_id=v.id,
                    scan_id=scan.id,
                    message=f"FLAGGED: Vehicle {v.plate_number} score {sc}% ({cls}) at {plaza}.",
                    is_read=False,
                    status='pending_inspection'
                )
                db.session.add(notif)

            return scan

        # Scan 1: Compliant underload
        v1 = vehicles_created[0] # MH 20 BT 4471 (5530.S)
        create_full_scan(v1, 28000, 12800, 2500, 3850, 5, 96.5, toll_plazas[0], 5)

        # Scan 2: Moderate load
        v2 = vehicles_created[1] # KA 05 MC 8812 (2820)
        create_full_scan(v2, 27100, 10500, 2500, 3600, 3, 94.0, toll_plazas[1], 4)

        # Scan 3: Overload violation
        v3 = vehicles_created[2] # MH 12 QW 9901 (3528C)
        create_full_scan(v3, 41500, 11200, 2500, 3750, 4, 91.2, toll_plazas[0], 3)

        # Scan 4: Unauthorized Modification + Overload (Height 32% over spec + extra axle)
        v4 = vehicles_created[3] # DL 01 GB 3342 (Pro 6028) - Cert L:10200, H:3550, Axles:3
        create_full_scan(v4, 34800, 11200, 2500, 4700, 4, 62.5, toll_plazas[0], 1)

        # Scan 5: Severe Overload & Length Modification (L: 14800mm vs 10500mm = 141% deviation)
        v5 = vehicles_created[7] # TN 09 CK 4040
        create_full_scan(v5, 36200, 14800, 2600, 3900, 4, 58.0, toll_plazas[0], 0.5)

        db.session.commit()
        print("Demo scan and notification records seeded successfully!")


if __name__ == "__main__":
    seed_database()
