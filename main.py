 
import time
import hmac
import hashlib
import json
import requests

API_URL = "http://127.0.0.1:8000/api/meter"
SECRET_KEY = b"hackathon_secret_key"
current_kwh = 100.0

print("🚀 Starting Smart Meter simulation. Sending data every 360 seconds...")

while True:
    current_kwh += 0.05 
    payload_dict = {"kwh": current_kwh, "timestamp": int(time.time())}
    payload_bytes = json.dumps(payload_dict).encode('utf-8')
    sig = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Signature": sig
    }
    
    try:
        response = requests.post(API_URL, data=payload_bytes, headers=headers)
        print(f"Sent: {current_kwh:.2f} kWh | Server Response: {response.json()}")
    except Exception as e:
        print(f"Connection error: {e}")
        
    time.sleep(3)

