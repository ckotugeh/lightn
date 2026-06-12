import hmac
import hashlib
import json
import asyncio
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect

app = FastAPI()

SECRET_KEY = b"hackathon_secret_key"

# State tracking: breaker_enabled starts as True
db_mock = {"last_kwh": 0.0, "total_sats_earned": 0, "breaker_enabled": True}
connected_websockets = set()

def verify_signature(payload: bytes, signature: str) -> bool:
    expected_sig = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, signature)

@app.post("/api/meter")
async def receive_meter_data(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Signature")
    
    if not signature or not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")
    
    # 🛑 CRITICAL REJECTION: If the user flipped the breaker off, reject and do not charge/count!
    if not db_mock["breaker_enabled"]:
        return {"status": "paused", "reason": "User circuit breaker is disconnected"}

    data = json.loads(body)
    current_kwh = data.get("kwh", 0.0)
    
    last_kwh = db_mock["last_kwh"]
    
    # If this is the very first packet after a pause, reset baseline to prevent massive delta jumps
    if last_kwh == 0.0:
        db_mock["last_kwh"] = current_kwh
        return {"status": "baseline_set"}

    kwh_delta = max(0.0, current_kwh - last_kwh)
    sats_to_pay = int(kwh_delta * 50)
    
    if sats_to_pay > 0:
        db_mock["last_kwh"] = current_kwh
        db_mock["total_sats_earned"] += sats_to_pay
        
        payment_event = {
            "event": "payment_sent",
            "kwh_delta": round(kwh_delta, 4),
            "sats_paid": sats_to_pay,
            "total_earned": db_mock["total_sats_earned"]
        }
        
        for websocket in connected_websockets:
            try:
                await websocket.send_json(payment_event)
            except:
                pass
                
        return {"status": "success", "paid": sats_to_pay}
    
    return {"status": "no_delta"}

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        # Send current live state on fresh load
        await websocket.send_json({
            "event": "init", 
            "total_earned": db_mock["total_sats_earned"]
        })
        while True:
            # Continuously monitor button clicks from app.js in real-time
            text_data = await websocket.receive_text()
            msg = json.loads(text_data)
            if msg.get("action") == "toggle_breaker":
                db_mock["breaker_enabled"] = msg.get("enabled", True)
                
                # If breaker turned off, wipe tracking variables temporarily to freeze billing
                if not db_mock["breaker_enabled"]:
                    db_mock["last_kwh"] = 0.0
                    
                print(f"🔌 Power Circuit Breaker state changed to: {db_mock['breaker_enabled']}")
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
