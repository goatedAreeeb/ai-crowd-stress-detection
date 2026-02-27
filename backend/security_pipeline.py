"""
=================================================================
 Suspicious Object Detection — Security Analysis Pipeline
=================================================================
 This module loads a trained YOLOv8 model (best.pt) and provides
 a clean API to detect threats in video frames.

 USAGE:
   from security_pipeline import SecurityAnalyzer

   analyzer = SecurityAnalyzer("runs/detect/train/weights/best.pt")
   result = analyzer.detect_threats(frame)
   # result = {
   #   "threat_detected": True,
   #   "risk_level": "CRITICAL",
   #   "stress_score": 100,
   #   "detections": [...],
   #   "total_threats": 3
   # }
=================================================================


=================================================================
 🔒 SECURITY & CV ENGINEERING NOTES
=================================================================

 1. WHY 300-400 IMAGES IS A "BASE" (AND HOW AUGMENTATION HELPS)
 ---------------------------------------------------------------
 • 300-400 annotated images per class is the minimum for YOLOv8 to
   learn meaningful features. Below 200, the model will overfit badly.

 • Our training script uses MOSAIC augmentation (combines 4 images
   into 1 tile) and MIXUP (blends 2 images together). Combined with
   flipping, scaling, and color jitter, each real image generates
   ~4-5 unique training variations.

 • This means 400 real images behave like ~1,600-2,000 effective
   training samples. This is enough for a PROTOTYPE model.

 • For PRODUCTION systems (airports, stadiums), aim for 2,000+
   images per class, collected from the actual deployment cameras.


 2. THE SMALL OBJECT PROBLEM (KNIVES & RODS ON CCTV)
 ---------------------------------------------------------------
 • Knives, rods, and daggers are extremely small in typical CCTV
   footage (often < 20 pixels wide). YOLOv8 struggles with objects
   smaller than ~32x32 pixels in a 640x640 input.

 • SOLUTIONS:
   a) Use HIGH-RESOLUTION feeds (1080p minimum, 4K preferred).
      The model input is 640px, so a 4K frame gets downscaled —
      but small objects are still larger in the resized image.

   b) Use TILING: Split a 4K frame into 4 overlapping 1080p tiles,
      run detection on each tile, and merge results. This is
      computationally expensive (4x slower) but catches small items.

   c) Train a SEPARATE small-object model at imgsz=1280 for
      close-range cameras (e.g., entrance security checkpoints).

   d) Use YOLOv8's built-in SAHI (Sliced Aided Hyper Inference)
      for automatic tiling at inference time.

 • For unattended bags/backpacks, the problem is different:
   they are large objects but look like NORMAL objects out of
   context. The model needs examples of bags sitting alone in
   unusual positions (on floors, benches, corners).


 3. FALSE POSITIVE MANAGEMENT
 ---------------------------------------------------------------
 • Objects like umbrellas, walking sticks, and baguettes can
   trigger false positives for knives/rods. include "hard negative"
   examples in your training data (images of these harmless objects
   annotated with NO label) to teach the model the difference.

 • In production, use a TWO-STAGE system:
   Stage 1: Fast YOLOv8 detection (this pipeline)
   Stage 2: A classification model that verifies the cropped
   detection to confirm it's truly a weapon (reduces false alarms).

=================================================================
"""

import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from ultralytics import YOLO


# The 12 threat classes (must match data.yaml)
THREAT_CLASSES = [
    "pistol", "revolver", "rifle",
    "kitchen_knife", "dagger", "machete", "large_blade",
    "metal_rod", "bat_or_club",
    "unattended_backpack", "suspicious_bag", "large_unusual_object",
]

# Severity mapping: which classes are highest priority
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


class SecurityAnalyzer:
    """
    Loads a trained YOLOv8 model and provides threat detection
    on individual video frames.
    """

    def __init__(self, model_path: str = "runs/detect/train/weights/best.pt",
                 conf_threshold: float = 0.4,
                 device: str = "cpu"):
        """
        Initialize the security analyzer.

        Args:
            model_path: Path to the trained YOLOv8 weights file (best.pt).
            conf_threshold: Minimum confidence to consider a detection valid.
                            0.4 is a good starting point. Increase to 0.6+
                            if you get too many false positives.
            device: 'cuda', 'mps', or 'cpu'.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found at '{model_path}'. "
                f"Please train the model first using train_security_model.py"
            )

        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.device = device
        print(f"[SecurityAnalyzer] Loaded model from: {model_path}")
        print(f"[SecurityAnalyzer] Confidence threshold: {conf_threshold}")
        print(f"[SecurityAnalyzer] Device: {device}")

    def detect_threats(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Run threat detection on a single video frame.

        Args:
            frame: A BGR image (numpy array from cv2).

        Returns:
            A JSON-ready dictionary with detection results:
            {
                "threat_detected": bool,
                "risk_level": "NORMAL" | "WARNING" | "CRITICAL",
                "stress_score": 0-100,
                "total_threats": int,
                "highest_severity": str,
                "detections": [
                    {
                        "class_name": str,
                        "confidence": float,
                        "severity": str,
                        "bbox": [x1, y1, x2, y2]
                    },
                    ...
                ]
            }
        """
        # Run YOLOv8 inference with Tracking
        results = self.model.track(
            source=frame,
            conf=self.conf_threshold,
            device=self.device,
            persist=True,             # Keep tracking IDs across frames
            tracker="botsort.yaml",   # Robust tracker suitable for camera movement/blur
            verbose=False,
        )

        detections: List[Dict[str, Any]] = []

        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    # Retrieve tracking ID if tracker is successful
                    track_id = int(box.id[0].item()) if box.id is not None else None

                    class_name = THREAT_CLASSES[cls_id] if cls_id < len(THREAT_CLASSES) else "unknown"
                    severity = SEVERITY_MAP.get(class_name, "LOW")

                    detections.append({
                        "id": track_id,
                        "class_name": class_name,
                        "confidence": round(conf, 3),
                        "severity": severity,
                        "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    })

        # Determine overall threat level
        total_threats = len(detections)
        threat_detected = total_threats > 0

        if threat_detected:
            # Find the highest severity among detections
            severity_order = {"EXTREME": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
            highest = max(detections, key=lambda d: severity_order.get(d["severity"], 0))
            highest_severity = highest["severity"]

            # Map to risk level and stress score
            if highest_severity in ("EXTREME", "HIGH"):
                risk_level = "CRITICAL"
                stress_score = 100
            elif highest_severity == "MEDIUM":
                risk_level = "WARNING"
                stress_score = 70
            else:
                risk_level = "WARNING"
                stress_score = 40
        else:
            risk_level = "NORMAL"
            stress_score = 0
            highest_severity = "NONE"

        return {
            "threat_detected": threat_detected,
            "risk_level": risk_level,
            "stress_score": stress_score,
            "total_threats": total_threats,
            "highest_severity": highest_severity,
            "detections": detections,
        }

    def annotate_frame(self, frame: np.ndarray, result: Dict[str, Any]) -> np.ndarray:
        """
        Draw bounding boxes and labels on the frame for visualization.

        Args:
            frame: Original BGR image.
            result: The dictionary returned by detect_threats().

        Returns:
            Annotated copy of the frame.
        """
        annotated = frame.copy()

        severity_colors = {
            "EXTREME": (0, 0, 255),    # Red
            "HIGH": (0, 69, 255),      # Orange
            "MEDIUM": (0, 200, 255),   # Yellow
            "LOW": (255, 200, 0),      # Cyan
        }

        for det in result["detections"]:
            x1, y1, x2, y2 = map(int, det["bbox"])
            color = severity_colors.get(det["severity"], (128, 128, 128))
            
            track_prefix = f"ID:{det['id']} " if det.get('id') is not None else ""
            label = f"{track_prefix}{det['class_name']} {det['confidence']:.0%}"

            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw label background
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw + 5, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Draw overall status banner if threat detected
        if result["threat_detected"]:
            banner_text = f"⚠ THREAT: {result['highest_severity']} — {result['total_threats']} object(s)"
            cv2.rectangle(annotated, (0, 0), (frame.shape[1], 40), (0, 0, 200), -1)
            cv2.putText(annotated, banner_text, (10, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        return annotated


# ============================================================
# Quick standalone test (run directly to test with webcam)
# ============================================================
if __name__ == "__main__":
    import sys

    model_path = sys.argv[1] if len(sys.argv) > 1 else "runs/detect/train/weights/best.pt"

    try:
        analyzer = SecurityAnalyzer(model_path=model_path)
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        print("   Train the model first: python train_security_model.py\n")
        sys.exit(1)

    cap = cv2.VideoCapture(0)
    print("\n[SecurityAnalyzer] Webcam test started. Press 'q' to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        result = analyzer.detect_threats(frame)
        annotated = analyzer.annotate_frame(frame, result)

        # Print to console if threat found
        if result["threat_detected"]:
            print(f"🚨 THREAT: {result['total_threats']} object(s) | "
                  f"Severity: {result['highest_severity']} | "
                  f"Risk: {result['risk_level']}")

        cv2.imshow("Security Monitor", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
