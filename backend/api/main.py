from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Iterable
from collections import deque
import asyncio
import cv2
import sys
import os
import time
import threading
import numpy as np
import aiosqlite
from pathlib import Path
from datetime import datetime

from ai_engine.detector import YOLOv8CrowdDetector
from security_pipeline import SecurityAnalyzer

# Paths
BASE_DIR = Path(__file__).resolve().parents[2]  # project root (folder that contains 'backend' and 'frontend')
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """
    Serve the main frontend page.
    """
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Frontend index.html not found</h1>", status_code=404)
    return HTMLResponse(index_path.read_text(encoding="utf-8"))

class DetectionItem(BaseModel):
    bbox: List[float]
    score: float

class DetectionResponse(BaseModel):
    total_people: int
    density_per_m2: Optional[float]
    detections: List[DetectionItem]
    roi: Optional[List[int]]
    image_shape: List[int]

# ===============================
# Global State & Config
# ===============================
DETECTOR_MODEL_PATH = "yolov8n.pt"
DETECTOR_DEVICE = "cpu"
PERSON_CLASS_NAME = "person"
CONF_THRESHOLD = 0.30

detector = YOLOv8CrowdDetector(
    model_path=DETECTOR_MODEL_PATH,
    device=DETECTOR_DEVICE,
    person_class_name=PERSON_CLASS_NAME,
    conf_threshold=CONF_THRESHOLD,
)

security_analyzer = SecurityAnalyzer(
    model_path="runs/detect/train/weights/best.pt", 
    conf_threshold=0.4
)

# Video Source State (None = off, 0 = webcam, or a file path)
video_source = None 
is_running = True
show_heatmap = False
is_paused = False
seek_target_percentage: Optional[float] = None
latest_webcam_frame_count = 0 
total_video_frames = 0 # To calculate progress

# Live Stream Multi-threading State
lock = threading.Lock()
latest_raw_frame = None
latest_annotated_frame = None
latest_detection_result = None
latest_detections_data = []
latest_security_result = None

# Temporal smoothing for crowd count display (rolling average of last 10 inference results)
_crowd_count_history = deque(maxlen=10)

# Density Settings
ASSUMED_AREA_M2 = 100.0 # Pretend the camera views ~100 sq meters

def compute_stress(total_people: int):
    if total_people <= 0:
        return 0, "NORMAL"
        
    area_per_person = ASSUMED_AREA_M2 / total_people
    
    # Critical: less than 2 sq meters per person
    # Warning: 2 to 4 sq meters per person
    # Normal: more than 4
    
    if area_per_person < 2.0:
        return 100, "CRITICAL"
    elif area_per_person <= 4.0:
        return 60, "WARNING"
    else:
        return 20, "NORMAL"


# ===============================
# Thread 1: High FPS Camera Reader
# ===============================
def camera_capture_thread():
    global latest_raw_frame, latest_annotated_frame, is_running, video_source, total_video_frames
    global seek_target_percentage, latest_webcam_frame_count
    
    cap = None
    current_source = None

    while is_running:
        if current_source != video_source:
            if cap: cap.release()
            
            if video_source is not None:
                detector.clear_history()
                cap = cv2.VideoCapture(video_source)
                
                # Setup best effort HD if camera
                if not isinstance(video_source, str):
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    total_video_frames = 0
                else:
                    total_video_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            else:
                cap = None
                
            current_source = video_source
            latest_webcam_frame_count = 0

        if cap is None:
            # Camera off
            with lock:
                latest_raw_frame = None
                latest_annotated_frame = None
            time.sleep(1)
            continue
            
        # Handle Seeking
        if seek_target_percentage is not None and isinstance(current_source, str):
            target_frame = int(total_video_frames * seek_target_percentage)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            seek_target_percentage = None
            latest_webcam_frame_count = target_frame
            detector.clear_history()

        # Handle Pause
        if is_paused and isinstance(current_source, str):
            time.sleep(0.1)
            continue

        ret, frame = cap.read()
        if not ret:
            if isinstance(current_source, str):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                latest_webcam_frame_count = 0
                continue
            time.sleep(0.1)
            continue
            
        latest_webcam_frame_count += 1
            
        with lock:
            latest_raw_frame = frame.copy()
            
            if not show_heatmap:
                annotated = frame.copy()
                for det in latest_detections_data:
                    x1, y1, x2, y2 = map(int, det["bbox"])
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 128, 0), 2)
                    
                if latest_security_result and latest_security_result.get("threat_detected"):
                    annotated = security_analyzer.annotate_frame(annotated, latest_security_result)
                    
                latest_annotated_frame = annotated
            
        if isinstance(current_source, str):
            time.sleep(1/45) # Slightly faster than true 30 to account for loop overhead
        else:
            time.sleep(1/60) 
            
    if cap: cap.release()

# ===============================
# Thread 2: Async AI Inference
# ===============================
async def ai_inference_loop():
    global latest_detection_result, latest_detections_data, latest_annotated_frame, latest_security_result
    
    db_conn = await aiosqlite.connect("detection_logs.db")
    await db_conn.execute("""
        CREATE TABLE IF NOT EXISTS detection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_people INTEGER NOT NULL,
            stress_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL
        )
    """)
    await db_conn.commit()

    while True:
        with lock:
            frame_to_process = latest_raw_frame.copy() if latest_raw_frame is not None else None
            
        if frame_to_process is None or is_paused:
            await asyncio.sleep(0.1)
            continue
            
        try:
            result = await asyncio.to_thread(
                detector.detect, 
                frame_to_process, 
                return_image=show_heatmap, 
                overlay_heatmap=show_heatmap
            )
            # Security Detection
            sec_result = await asyncio.to_thread(
                security_analyzer.detect_threats,
                frame_to_process
            )
            
            total_people = result.get("total_people", 0)
            detections = result.get("detections", [])
            
            # Temporal smoothing for displayed crowd count
            _crowd_count_history.append(total_people)
            smoothed_count = int(round(sum(_crowd_count_history) / len(_crowd_count_history)))
            result["smoothed_crowd_count"] = smoothed_count
            
            stress_score, risk_level = compute_stress(total_people)

            # Merge Security Results
            if sec_result["threat_detected"]:
                if sec_result["risk_level"] == "CRITICAL":
                    risk_level = "CRITICAL"
                    stress_score = max(stress_score, 100)
                elif sec_result["risk_level"] == "WARNING":
                    if risk_level != "CRITICAL":
                        risk_level = "WARNING"
                    stress_score = max(stress_score, 70)

            result["stress_score"] = stress_score
            result["risk_level"] = risk_level
            
            # Security Fields for frontend
            result["threat_detected"] = sec_result["threat_detected"]
            result["highest_severity"] = sec_result["highest_severity"]
            result["total_threats"] = sec_result["total_threats"]

            # Additional UI progress info
            with lock:
                if total_video_frames > 0:
                    result["progress_pct"] = (latest_webcam_frame_count / total_video_frames) * 100
                else:
                    result["progress_pct"] = 0

            with lock:
                latest_detection_result = result
                latest_detections_data = detections
                latest_security_result = sec_result
                if show_heatmap and "annotated_image" in result:
                    heat_img = result["annotated_image"].copy()
                    if sec_result["threat_detected"]:
                        heat_img = security_analyzer.annotate_frame(heat_img, sec_result)
                    latest_annotated_frame = heat_img

            timestamp = datetime.utcnow().isoformat()
            await db_conn.execute(
                "INSERT INTO detection_logs (timestamp, total_people, stress_score, risk_level) VALUES (?, ?, ?, ?)",
                (timestamp, total_people, stress_score, risk_level)
            )
            await db_conn.commit()
            
        except Exception as e:
            print("Inference error:", e)
            
        await asyncio.sleep(0.01)

# ===============================
# App Lifecycle
# ===============================

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=camera_capture_thread, daemon=True).start()
    asyncio.create_task(ai_inference_loop())

@app.on_event("shutdown")
def shutdown_event():
    global is_running
    is_running = False


# ===============================
# REST API
# ===============================

@app.post("/api/start-camera")
async def start_camera():
    global video_source, is_paused
    video_source = 0
    is_paused = False
    return {"status": "Camera started"}

@app.post("/api/stop-camera")
async def stop_camera():
    global video_source, is_paused
    video_source = None
    is_paused = False
    return {"status": "Camera stopped"}


class VideoControlPayload(BaseModel):
    action: str
    value: Optional[float] = None
    
@app.post("/api/video-control")
async def video_control(payload: VideoControlPayload):
    global is_paused, seek_target_percentage
    
    if payload.action == "pause":
        is_paused = True
    elif payload.action == "play":
        is_paused = False
    elif payload.action == "seek" and payload.value is not None:
        seek_target_percentage = payload.value
        
    return {"status": "ok", "paused": is_paused}


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    global video_source, is_paused
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    video_source = file_path
    is_paused = False
    return JSONResponse({"status": "Success", "file": file.filename})

@app.post("/api/heatmap-toggle")
async def toggle_heatmap(payload: dict):
    global show_heatmap
    if "enabled" in payload:
        show_heatmap = payload["enabled"]
    else:
        show_heatmap = not show_heatmap
    return JSONResponse({"heatmap_enabled": show_heatmap})


@app.get("/api/video")
def api_video():
    def frame_generator() -> Iterable[bytes]:
        boundary = b"--frame"
        try:
            while True:
                with lock:
                    frame = latest_annotated_frame.copy() if latest_annotated_frame is not None else None
                    
                if frame is None:
                    blank = np.zeros((720, 1280, 3), dtype=np.uint8)
                    cv2.putText(blank, "CAMERA OFFLINE", (450, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 100), 3)
                    ok, buf = cv2.imencode(".jpg", blank, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                    if ok:
                        yield boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
                    time.sleep(0.5)
                    continue

                ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok:
                    yield (
                        boundary
                        + b"\r\nContent-Type: image/jpeg\r\n\r\n"
                        + buf.tobytes()
                        + b"\r\n"
                    )
                time.sleep(0.033)
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


# ===============================
# WebSocket (Live Streaming)
# ===============================

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if video_source is None:
                await websocket.send_json({"status": "No detection yet", "source": "off", "paused": False})
            elif latest_detection_result:
                payload = dict(latest_detection_result)
                payload["source"] = "video" if isinstance(video_source, str) else "camera"
                payload["paused"] = is_paused
                await websocket.send_json(payload)
            else:
                await websocket.send_json({"status": "Initializing...", "source": "video" if isinstance(video_source, str) else "camera", "paused": is_paused})
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass