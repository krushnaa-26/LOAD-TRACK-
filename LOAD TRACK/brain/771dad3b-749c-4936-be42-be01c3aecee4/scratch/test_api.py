import sys
import os
import io

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app
from models import db, Vehicle, Scan, Challan

def run_tests():
    client = app.test_client()

    print("--- 1. Testing GET / ---")
    res = client.get('/')
    print(f"Status: {res.status_code}")
    assert res.status_code == 200

    print("--- 2. Testing GET /api/samples ---")
    res = client.get('/api/samples')
    print(f"Status: {res.status_code}, json: {res.get_json()}")
    assert res.status_code == 200

    print("--- 3. Testing GET /api/stats ---")
    res = client.get('/api/stats')
    print(f"Status: {res.status_code}, json: {res.get_json()}")
    assert res.status_code == 200

    print("--- 4. Testing GET /api/vehicles ---")
    res = client.get('/api/vehicles')
    print(f"Status: {res.status_code}, count: {len(res.get_json()['vehicles'])}")
    assert res.status_code == 200

    print("--- 5. Testing GET /api/vehicles/MH 20 BT 4471 ---")
    res = client.get('/api/vehicles/MH%2020%20BT%204471')
    print(f"Status: {res.status_code}, json: {res.get_json()}")
    assert res.status_code == 200

    print("--- 6. Testing GET /api/challans ---")
    res = client.get('/api/challans')
    print(f"Status: {res.status_code}, count: {len(res.get_json()['challans'])}")
    assert res.status_code == 200

    print("--- 7. Testing POST /api/scan with sample_filename ---")
    res = client.post('/api/scan', data={
        'weight': 38000,
        'toll_plaza': 'Kharegaon Toll Plaza',
        'sample_filename': 'MH_20_BT_4471.jpg'
    })
    print(f"Status: {res.status_code}, json: {res.get_json()}")
    assert res.status_code == 200

    print("--- 8. Testing POST /api/scan with manual plate and weight ---")
    res = client.post('/api/scan', data={
        'weight': 45000,
        'toll_plaza': 'Vashi Toll Naka',
        'plate_number': 'MH 12 QW 9901'
    })
    print(f"Status: {res.status_code}, json: {res.get_json()}")
    assert res.status_code == 200

    print("--- 9. Testing POST /api/challans/1/verify ---")
    res = client.post('/api/challans/1/verify')
    print(f"Status: {res.status_code}, json: {res.get_json()}")
    assert res.status_code == 200

    print("\nALL API TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
