import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ocr import extract_plate_number

sample_dir = os.path.join(os.path.dirname(__file__), 'sample_images')
if os.path.exists(sample_dir):
    for f in os.listdir(sample_dir):
        if f.endswith('.jpg') or f.endswith('.png'):
            path = os.path.join(sample_dir, f)
            print(f"\nTesting file: {f}")
            res = extract_plate_number(path)
            print("Result:", res)
