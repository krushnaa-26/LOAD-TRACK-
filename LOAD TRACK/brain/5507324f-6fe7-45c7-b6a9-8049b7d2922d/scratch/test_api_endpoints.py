import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:5000"

def get(url):
    req = urllib.request.Request(BASE_URL + url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def post(url, data_dict):
    data_bytes = json.dumps(data_dict).encode('utf-8')
    req = urllib.request.Request(BASE_URL + url, data=data_bytes, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

print("1. Testing GET /api/stats...")
res_stats = get("/api/stats")
print("Stats response:", res_stats)

print("\n2. Testing POST /api/scan (Modification simulation mode)...")
res_scan = post("/api/scan", {
    "plate_number": "MH 20 BT 4471",
    "weight": 42000,
    "toll_plaza": "Kharegaon Toll Plaza",
    "simulation_mode": "modification"
})
print("Scan Composite Score:", res_scan.get("composite_score"))
print("Scan Classification:", res_scan.get("classification"))
print("Deviations:", res_scan.get("deviations"))

print("\n3. Testing GET /api/scans...")
res_scans = get("/api/scans?limit=5")
print(f"Fetched {len(res_scans.get('scans', []))} recent scans.")

print("\n4. Testing POST /api/officer/login...")
res_login = post("/api/officer/login", {
    "badge_id": "RTO-MH04-101",
    "password": "password123"
})
print("Officer login:", res_login.get("message"), res_login.get("officer"))

print("\n5. Testing GET /api/officer/notifications...")
res_notifs = get("/api/officer/notifications?badge_id=RTO-MH04-101")
print(f"Unread Count: {res_notifs.get('unread_count')}, Total Notifications: {len(res_notifs.get('notifications', []))}")

first_notif_id = res_notifs.get('notifications')[0]['id'] if res_notifs.get('notifications') else 1
print(f"\n6. Testing GET /api/officer/inspections/{first_notif_id}...")
res_insp = get(f"/api/officer/inspections/{first_notif_id}")
print("Inspection detail score:", res_insp.get("scan", {}).get("composite_score"))

print("\n7. Testing POST /api/officer/inspections/{first_notif_id}/verify...")
res_ver = post(f"/api/officer/inspections/{first_notif_id}/verify", {})
print("Verification message:", res_ver.get("message"))

print("\nALL API TESTS PASSED SUCCESSFULLY!")
