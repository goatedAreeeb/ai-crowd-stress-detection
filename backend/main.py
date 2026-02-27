"""
Main FastAPI application entrypoint.
"""
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import cv2
import asyncio
import os
import aiosqlite
import numpy as np
import torch
from datetime import datetime
from pydantic import BaseModel

from utils.gpu_utils import setup_gpu
from services.crowd_detector import CrowdDetector
from services.weapon_detector import WeaponDetector
from services.video_engine import VideoEngine

# Initialize GPU
setup_gpu()

# Initialize Models
CROWD_MODEL = "yolov8m.pt" # Upgraded to medium for better accuracy, runs fine on 4050 FP16
WEAPON_MODEL = "runs/detect/train/weights/best.pt"

print(f"Loading Crowd Model: {CROWD_MODEL}...")
crowd_detector = CrowdDetector(model_path=CROWD_MODEL, conf_threshold=0.30, imgsz=960)
print(f"Loading Weapon Model: {WEAPON_MODEL}...")
weapon_detector = WeaponDetector(model_path=WEAPON_MODEL, conf_threshold=0.40, imgsz=960)

engine = VideoEngine(crowd_detector, weapon_detector)

app = FastAPI(title="AI Crowd Detection System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

DB_FILE = "detection_logs.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                crowd_count INTEGER NOT NULL,
                weapon_detected BOOLEAN NOT NULL,
                risk_level TEXT NOT NULL
            )
        """)
        await db.commit()

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
def shutdown_event():
    engine.stop()

# =======================
# Endpoints
# =======================

@app.get("/api/health")
def health_check():
    return {"status": "ok", "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"}

@app.post("/api/start-camera")
async def start_camera():
    success = engine.start(0)
    if success:
        return {"status": "Camera started"}
    raise HTTPException(status_code=500, detail="Failed to start camera")

@app.post("/api/stop-camera")
async def stop_camera():
    engine.stop()
    return {"status": "Camera stopped"}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    input_path = os.path.join("uploads", f"raw_{file.filename}")
    
    print(f"Upload started: {file.filename}")
    
    try:
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)
        print(f"File saved to {input_path}, size: {os.path.getsize(input_path)} bytes")
        
        # Start live processing through engine (same as camera but with video file)
        # Processing runs in background threads - persists across frontend route changes
        abs_path = os.path.abspath(input_path)
        print(f"Starting engine with video: {abs_path}")
        success = engine.start(abs_path)
        if not success:
            raise ValueError(f"Failed to start video processing for {input_path}")
        
        print(f"Video processing started for {input_path}")
        return JSONResponse({"status": "Success", "processing": True})
    except Exception as e:
        print(f"Error processing video: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process video: {str(e)}")


@app.get("/api/video")
def api_video():
    """MJPEG streaming endpoint"""
    import time
    
    def frame_generator():
        boundary = b"--frame"
        last_version = -1
        try:
            while True:
                frame, _ = engine.get_latest()
                
                if frame is None:
                    blank = np.zeros((720, 1280, 3), dtype=np.uint8)
                    cv2.putText(blank, "CAMERA OFFLINE", (450, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 100), 3)
                    ok, buf = cv2.imencode(".jpg", blank, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                    if ok:
                        yield boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
                    last_version = -1
                    time.sleep(0.5)
                    continue

                # Skip encoding if frame hasn't changed (same version)
                current_version = engine.frame_version
                if current_version == last_version:
                    time.sleep(0.01)
                    continue
                last_version = current_version

                ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok:
                    yield (
                        boundary
                        + b"\r\nContent-Type: image/jpeg\r\n\r\n"
                        + buf.tobytes()
                        + b"\r\n"
                    )
                time.sleep(0.01)
        except GeneratorExit:
            print("MJPEG client disconnected, cleaning up stream")
            return

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
        },
    )

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Push detection stats to the frontend in realtime.
    Logs to DB occasionally.
    """
    await websocket.accept()
    log_counter = 0
    
    try:
        while True:
            _, stats = engine.get_latest()
            
            if not engine.is_running:
                await websocket.send_json({"status": "Offline", "crowd_count": 0, "unique_count": 0, "weapon_detected": False, "risk_level": "NORMAL", "fps": 0})
            else:
                payload = stats.copy()
                payload["status"] = "Running"
                await websocket.send_json(payload)
                
                # Log to DB every ~2 seconds (assuming 5 loops per sec)
                log_counter += 1
                if log_counter >= 10:
                    log_counter = 0
                    timestamp = datetime.utcnow().isoformat()
                    async with aiosqlite.connect(DB_FILE) as db:
                        await db.execute(
                            "INSERT INTO system_logs (timestamp, crowd_count, weapon_detected, risk_level) VALUES (?, ?, ?, ?)",
                            (timestamp, stats["crowd_count"], stats["weapon_detected"], stats["risk_level"])
                        )
                        await db.commit()

            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass
