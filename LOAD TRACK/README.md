# 🚛 LOAD TRACK — Toll-Plaza Vehicle Overload Detection & Enforcement System

**LOAD TRACK** is a full-stack web application designed for toll plazas to automatically detect vehicle weight overloads using Computer Vision OCR, perform instant load classification against RTO-certified Gross Vehicle Weight (GVW), issue penalty challans, trigger automated SMS alerts, and manage RTO enforcement workflows.

Built as a final-year engineering project prototype with a monorepo structure (`/backend` and `/frontend`).

---

## 🛠️ TECH STACK

- **Backend**: Python 3.11 + Flask (REST API)
- **Database**: SQLite (via SQLAlchemy ORM)
- **OCR / Computer Vision**: OpenCV + EasyOCR (Indian License Plate Text Extraction)
- **Frontend**: Plain HTML5 + CSS3 + Vanilla JavaScript (Single-Page Dashboard with Industrial Highway-Signage UI)
- **SMS Integration**: Twilio Python SDK (Trial/Sandbox mode with automatic simulated console fallback)

---

## 📊 SIMULATED VS REAL COMPONENTS

As an academic prototype:
1. **RTO Database**: Realistically seeded locally with 18 standard Indian commercial truck models (Tata Signa, Ashok Leyland, BharatBenz, Eicher Pro, Mahindra Blazo, etc.) with capacities ranging from 16,000 kg to 49,000 kg.
2. **Weighbridge Scale**: Simulated via direct sensor input or auto-generated random weight trigger in the Toll Operator UI.
3. **SMS Alert Gateway**: Uses Twilio SDK if credentials are in `.env`, or gracefully falls back to printing `[SIMULATED SMS DISPATCH]` in the console so the full workflow operates end-to-end without requiring active credentials.
4. **Core Application Logic**: OCR detection, plate normalization, overload classification, database persistence, status escalation engine, and RTO verification REST API are **100% real and fully functional**.

---

## 🚀 QUICK START & LOCAL EXECUTION

### 1. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Seed Database & Generate Sample Test Images
Run the seed script to create the SQLite database schema (`loadtrack.db`), populate sample vehicle/scan records, and create synthetic test license plate images in `backend/sample_images/`:
```bash
python seed_data.py
```

### 3. Start Flask REST API Server
```bash
python app.py
```
The Flask server will start running at `http://localhost:5000`.

### 4. Open Frontend Dashboard
Open `frontend/index.html` directly in any web browser, or navigate to `http://localhost:5000/` in your browser.

---

## 📁 PROJECT MONOREPO STRUCTURE

```
LOAD TRACK/
├── README.md                 # Project Overview & Execution Guide
├── backend/
│   ├── app.py                # Main Flask REST API & Static File Server
│   ├── database.py           # DB Instance initialization
│   ├── models.py             # SQLAlchemy Schema (Vehicle, Scan, Challan)
│   ├── ocr.py                # OpenCV + EasyOCR Plate Recognition Engine
│   ├── classifier.py         # GVW Load Percentage & Classification Logic
│   ├── challan_engine.py     # Violation Counter, Fine Multipliers & Escalation
│   ├── sms.py                # Twilio SDK Integration & Simulated Console Fallback
│   ├── seed_data.py          # Database Seeder & Test Image Generator
│   ├── requirements.txt      # Python Package Dependencies
│   ├── .env.example          # Environment Configuration Template
│   ├── .env                  # Local Environment Keys
│   ├── loadtrack.db          # SQLite Database File (Created after seeding)
│   └── sample_images/        # Sample Truck License Plate Images for Testing
└── frontend/
    ├── index.html            # Tabbed Single-Page Interface
    ├── style.css             # Industrial Asphalt & Safety Yellow Styling
    └── app.js                # REST API Fetch Calls & Interactive UI Logic
```

---

## 📡 REST API ENDPOINTS

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `POST /api/scan` | `POST` | Upload plate image + weighbridge weight. Runs OCR → DB Lookup → Classification → Escalation Engine → SMS Alert. |
| `GET /api/vehicles` | `GET` | List all registered vehicles and their violation status. |
| `GET /api/vehicles/<plate>`| `GET` | Retrieve complete vehicle dossier, scan history, and past challans. |
| `GET /api/challans` | `GET` | List all challans for RTO dashboard (filterable by `?status=`). |
| `POST /api/challans/<id>/verify` | `POST` | RTO Officer confirms on-site inspection, marks status as `confirmed`. |
| `GET /api/stats` | `GET` | Dashboard summary metrics (Scanned today, Overloads, Active Challans, Seizure Orders). |
| `GET /api/samples` | `GET` | List pre-generated sample truck plate images for rapid testing. |

---

## 🔒 ENVIRONMENT VARIABLES (`.env`)

```env
FLASK_APP=app.py
FLASK_ENV=development
PORT=5000
SECRET_KEY=loadtrack_dev_secret_key_2026

# Twilio SMS API Credentials (Optional - auto falls back to simulated console mode)
TWILIO_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

---

## ⚖️ ESCALATION & PENALTY WORKFLOW

1. **Compliant (Load ≤ 90%)**: Marked as `underload`. No penalty.
2. **Moderate (90% < Load ≤ 100%)**: Marked as `moderate`. Warning clear.
3. **1st Offense Overload (Load > 100%)**:
   - Status set to `1st_offense`.
   - Fine: Base ₹5,000 + ₹500 per each 5% overload over certified GVW.
   - Challan created with status `pending_rto_verification`.
   - SMS Alert sent to owner.
4. **Repeat Offense (Offense #2+)**:
   - Status escalated to `escalated` / `seized`.
   - Fine: **3x Multiplier** on base fine calculation.
   - Seizure Notice SMS dispatched to owner with 7-day reporting directive.
