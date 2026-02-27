"""
Weapon Detector — optimized for NVIDIA RTX 4050.
"""
from typing import Dict, Any, List
import cv2
import numpy as np
from ultralytics import YOLO
import torch

from utils.gpu_utils import get_device, optimize_model
from utils.smoothing import TemporalSmoother

# The 12 threat classes (must match data.yaml)
THREAT_CLASSES = [
    "pistol", "revolver", "rifle",
    "kitchen_knife", "dagger", "machete", "large_blade",
    "metal_rod", "bat_or_club",
    "unattended_backpack", "suspicious_bag", "large_unusual_object",
]

# Severity mapping
SEVERITY_MAP = {
    "pistol": "EXTREME",
    "revolver": "EXTREME",
    "rifle": "EXTREME",
    "machete": "HIGH",
    "large_blade": "HIGH",
    "dagger": "HIGH",
    "kitchen_knife": "MEDIUM",
    "metal_rod": "MEDIUM",
    "bat_or_club": "MEDIUM",
    "unattended_backpack": "HIGH",
    "suspicious_bag": "MEDIUM",
    "large_unusual_object": "LOW",
}


class WeaponDetector:
    def __init__(self, model_path: str = "runs/detect/train/weights/best.pt", conf_threshold: float = 0.50, iou_threshold: float = 0.45, imgsz: int = 768):
        self.device = get_device()
        self.model = YOLO(model_path)
        self.model = optimize_model(self.model, self.device)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        print(f"[WeaponDetector] Loaded model classes: {self.model.names}")
        
        # Temporal smoothing (require 2 consecutive frames to confirm — relaxed for fast motion)
        self.smoother = TemporalSmoother(min_frames=2)
        self.total_weapons_detected = 0
        self._tracked_weapon_ids = set()

    def detect_weapons(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Run inference using BotSORT, apply temporal smoothing.
        """
        results = self.model.track(
            source=frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            imgsz=self.imgsz,
            device=self.device,
            persist=True,
            tracker="botsort.yaml", # Botsort handles camera motion better
            verbose=False,
        )
        
        raw_detections = []
        
        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0].item())
                    cls_id = int(box.cls[0].item())
                    track_id = int(box.id[0].item()) if box.id is not None else -1
                    
                    # Minimum bounding box area filter — ignore tiny/noisy detections
                    width = x2 - x1
                    height = y2 - y1
                    if width * height < 800:
                        continue
                    
                    # Ensure correct model names are used (fallback to unknown)
                    model_class_name = self.model.names.get(cls_id, "unknown")
                    
                    print(f"[WeaponDetector ID:{track_id}] Detected: {model_class_name} (conf: {conf:.2f})")
                    
                    normalized_name = model_class_name.lower().replace(" ", "_").replace("-", "_")
                    severity = SEVERITY_MAP.get(normalized_name, "HIGH") # default to HIGH if detected but not mapped
                    
                    raw_detections.append({
                        "id": track_id,
                        "class_name": model_class_name,
                        "confidence": round(conf, 3),
                        "severity": severity,
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "center": (int((x1 + x2) / 2), int((y1 + y2) / 2))
                    })

        # Apply temporal smoothing
        # Only detections that have appeared in 3 consecutive frames
        confirmed_detections = self.smoother.update(raw_detections)

        threat_detected = len(confirmed_detections) > 0
        highest_severity = "NONE"

        if threat_detected:
            severity_order = {"EXTREME": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
            highest = max(confirmed_detections, key=lambda d: severity_order.get(d["severity"], 0))
            highest_severity = highest["severity"]

            for det in confirmed_detections:
                wid = det["id"]
                if wid != -1 and wid not in self._tracked_weapon_ids:
                    self._tracked_weapon_ids.add(wid)
                    self.total_weapons_detected += 1
                elif wid == -1:
                    # Fallback if tracker lost ID instantly but smoother caught it.
                    self.total_weapons_detected += 1

        return {
            "threat_detected": threat_detected,
            "total_weapons_ever_detected": self.total_weapons_detected,
            "current_threat_count": len(confirmed_detections),
            "highest_severity": highest_severity,
            "detections": confirmed_detections
        }

    def reset_stats(self):
        self.smoother.reset()
        self.total_weapons_detected = 0
        self._tracked_weapon_ids.clear()
