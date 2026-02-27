"""
Crowd Detector — optimized for NVIDIA RTX 4050.
"""
from typing import Dict, Any, Tuple
from collections import deque
import cv2
import numpy as np
from ultralytics import YOLO
import torch

from utils.gpu_utils import get_device, optimize_model
from services.tracker import CentroidTracker


class CrowdDetector:
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.30, iou_threshold: float = 0.50, imgsz: int = 960):
        self.device = get_device()
        self.model = YOLO(model_path)
        self.model = optimize_model(self.model, self.device)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        
        # Unique ID Tracking
        self.tracker = CentroidTracker(max_disappeared=30, max_distance=80)
        self.total_unique_people = 0
        self._tracked_ids = set()
        
        # Temporal smoothing for crowd count display (rolling avg of last 10 frames)
        self._count_history = deque(maxlen=10)

    def count_people(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Run inference using ByteTrack under the hood, but also apply
        CentroidTracker to guarantee we don't double count if ByteTrack resets IDs.
        """
        # Run tracking (bytetrack)
        results = self.model.track(
            source=frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            imgsz=self.imgsz,
            device=self.device,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0], # 0 is person
            verbose=False,
        )
        
        detections = []
        rects = []
        
        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0].item())
                    
                    track_id = int(box.id[0].item()) if box.id is not None else None
                    
                    detections.append({
                        "id": track_id,
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "conf": round(conf, 3)
                    })
                    rects.append([int(x1), int(y1), int(x2), int(y2)])

        # Update secondary tracker for total unique count
        objects = self.tracker.update(rects)
        for obj_id in objects.keys():
            if obj_id not in self._tracked_ids:
                self._tracked_ids.add(obj_id)
                self.total_unique_people += 1

        current_crowd = len(rects)
        
        # Rolling average smoothing for display
        self._count_history.append(current_crowd)
        smoothed_crowd = int(round(sum(self._count_history) / len(self._count_history)))

        return {
            "current_crowd_count": current_crowd,
            "smoothed_crowd_count": smoothed_crowd,
            "total_unique_people": self.total_unique_people,
            "detections": detections
        }

    def reset_stats(self):
        self.total_unique_people = 0
        self._tracked_ids.clear()
        self.tracker = CentroidTracker(max_disappeared=30, max_distance=80)
        self._count_history.clear()
