"""
Multithreaded Video Engine.
Separates reading frames from detecting to prevent video lag.
Implements frame skipping for high FPS target.
"""
import sys
import os

# Add parent dir to python path if run standalone
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
import threading
import time
import queue
import numpy as np
from typing import Dict, Any, Optional, Tuple

from utils.fps import FPSCounter
from services.crowd_detector import CrowdDetector
from services.weapon_detector import WeaponDetector
from utils.risk_logic import compute_risk


class VideoEngine:
    def __init__(self, crowd_detector: CrowdDetector, weapon_detector: WeaponDetector):
        self.crowd_detector = crowd_detector
        self.weapon_detector = weapon_detector
        
        # State
        self.source = None
        self.cap = None
        self.is_running = False
        
        # Threads
        self.read_thread = None
        self.detect_thread = None
        
        # Data passing
        self.frame_queue = queue.Queue(maxsize=1)
        self.latest_result_lock = threading.Lock()
        
        self.latest_raw_frame = None
        self.latest_annotated_frame = None
        self.latest_stats = {
            "crowd_count": 0,
            "unique_count": 0,
            "weapon_detected": False,
            "risk_level": "NORMAL",
            "fps": 0.0,
            "message": "Initializing..."
        }
        
        # Utils
        self.fps_counter = FPSCounter(window=30)
        
        # Settings
        self.skip_frames = 2
        self.downscale_width = 640
        
        # Frame versioning (prevents duplicate MJPEG encoding)
        self._frame_version = 0
        
        # Weapon persistence buffer (prevents alert flickering in fast motion)
        self._last_weapon_frame = -999
        self._frame_counter = 0
        self._weapon_persistence_frames = 15

    def start(self, source: str | int = 0):
        self.stop(clear_frames=True)  # Clear old frames to prevent flash on mode switch
        self.source = source
        # Validate file path exists before opening
        if isinstance(source, str) and not os.path.exists(source):
            print(f"Video file not found: {source}")
            return False
        # Use CAP_DSHOW on Windows for reliable webcam access
        if isinstance(source, int):
            self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            print(f"Failed to open source {source}")
            return False
        
        # Read original video FPS for pacing (only for video files)
        if isinstance(source, str):
            video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self._frame_delay = 1.0 / video_fps if video_fps > 0 else 1.0 / 25.0
        else:
            self._frame_delay = 0.0  # Camera: no artificial delay
            
        self.is_running = True
        
        self.crowd_detector.reset_stats()
        self.weapon_detector.reset_stats()

        self.read_thread = threading.Thread(target=self._read_frames, daemon=True)
        self.detect_thread = threading.Thread(target=self._process_frames, daemon=True)
        
        self.read_thread.start()
        self.detect_thread.start()
        return True

    def stop(self, clear_frames=True):
        self.is_running = False
        if self.read_thread:
            self.read_thread.join(timeout=2.0)
        if self.detect_thread:
            self.detect_thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
            
        if clear_frames:
            with self.latest_result_lock:
                self.latest_raw_frame = None
                self.latest_annotated_frame = None

    def _read_frames(self):
        """Thread 1: Capture frames, paced to original video FPS for uploads."""
        frame_idx = 0
        while self.is_running and self.cap.isOpened():
            loop_start = time.time()
            
            ret, frame = self.cap.read()
            if not ret:
                # If video ends, loop it
                if isinstance(self.source, str) and not self.source.isdigit():
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break
                    
            if frame_idx % self.skip_frames == 0:
                # Keep original aspect ratio when resizing
                h, w = frame.shape[:2]
                scale = self.downscale_width / float(w)
                new_h = int(h * scale)
                small_frame = cv2.resize(frame, (self.downscale_width, new_h))
                
                try:
                    # Put small frame in queue, override if full to avoid lag
                    self.frame_queue.put_nowait((frame, small_frame))
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait((frame, small_frame))
                    except:
                        pass
                        
            frame_idx += 1
            
            # Pace to original video FPS (prevents fast-forward on uploads)
            if self._frame_delay > 0:
                elapsed = time.time() - loop_start
                sleep_time = self._frame_delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            else:
                time.sleep(0.001)  # Camera: tiny yield

    def _process_frames(self):
        """Thread 2: Run inference."""
        while self.is_running:
            try:
                original_frame, small_frame = self.frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue
                
            self.fps_counter.tick()
            self._frame_counter += 1

            # 1. Run inference on downscaled frame
            crowd_res = self.crowd_detector.count_people(small_frame)
            weapon_res = self.weapon_detector.detect_weapons(small_frame)

            # 1.5 Weapon persistence: keep alert active for 15 frames after last detection
            if weapon_res["threat_detected"]:
                self._last_weapon_frame = self._frame_counter
            
            weapon_persisted = (self._frame_counter - self._last_weapon_frame) < self._weapon_persistence_frames
            if weapon_persisted and not weapon_res["threat_detected"]:
                weapon_res["threat_detected"] = True
                if weapon_res["highest_severity"] == "NONE":
                    weapon_res["highest_severity"] = "MEDIUM"

            # 2. Compute risk
            risk_info = compute_risk(
                crowd_count=crowd_res["current_crowd_count"],
                weapon_detected=weapon_res["threat_detected"],
                weapon_severity=weapon_res["highest_severity"]
            )

            # 3. Compile output stats
            smoothed_count = crowd_res.get("smoothed_crowd_count", crowd_res["current_crowd_count"])
            current_stats = {
                "crowd_count": crowd_res["current_crowd_count"],
                "smoothed_crowd_count": smoothed_count,
                "unique_count": crowd_res["total_unique_people"],
                "weapon_detected": weapon_res["threat_detected"],
                "total_weapons": weapon_res["total_weapons_ever_detected"],
                "risk_level": risk_info["risk_level"],
                "color": risk_info["color"],
                "message": risk_info["message"],
                "fps": self.fps_counter.fps
            }

            # 4. Annotate Original Frame (upscale bounding boxes)
            annotated = original_frame.copy()
            h_orig, w_orig = original_frame.shape[:2]
            scale_x = w_orig / self.downscale_width
            scale_y = h_orig / small_frame.shape[0]

            # Draw Crowd
            for det in crowd_res["detections"]:
                x1, y1, x2, y2 = det["bbox"]
                x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
                y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
                
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 128, 0), 2)
                # track ID
                prefix = f"ID:{det['id']} " if det['id'] else ""
                cv2.putText(annotated, f"{prefix}Person", (x1, max(y1-5, 0)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,128,0), 2)

            # Draw Weapons
            for wdet in weapon_res["detections"]:
                wx1, wy1, wx2, wy2 = wdet["bbox"]
                wx1, wx2 = int(wx1 * scale_x), int(wx2 * scale_x)
                wy1, wy2 = int(wy1 * scale_y), int(wy2 * scale_y)
                
                color = (0, 0, 255) if wdet["severity"] in ["EXTREME", "HIGH"] else (0, 165, 255)
                cv2.rectangle(annotated, (wx1, wy1), (wx2, wy2), color, 3)
                label = f"{wdet['class_name']} ({wdet['severity']})"
                cv2.putText(annotated, label, (wx1, max(wy1-10, 0)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Draw Top Overlay
            cv2.rectangle(annotated, (0, 0), (w_orig, 40), (0,0,0), -1)
            overlay_text = f"FPS: {self.fps_counter.fps} | Crowd: {smoothed_count} | Risk: {current_stats['risk_level']}"
            cv2.putText(annotated, overlay_text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

            with self.latest_result_lock:
                self.latest_raw_frame = original_frame
                self.latest_annotated_frame = annotated
                self.latest_stats = current_stats
                self._frame_version += 1

    @property
    def frame_version(self):
        return self._frame_version

    def get_latest(self) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        with self.latest_result_lock:
            return (
                self.latest_annotated_frame.copy() if self.latest_annotated_frame is not None else None,
                self.latest_stats.copy()
            )

    def process_offline(self, file_path: str, output_path: str) -> dict:
        """Process a video file offline and save to output_path with frame skipping for speed."""
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {file_path}")
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or np.isnan(fps): fps = 30.0
        
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if orig_w == 0 or orig_h == 0:
            raise ValueError(f"Invalid video dimensions: {orig_w}x{orig_h}")
        
        # Try H.264 first (browser-compatible), fall back to mp4v
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, fps, (orig_w, orig_h))
        
        if not out.isOpened():
            print("avc1 codec unavailable, trying mp4v")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (orig_w, orig_h))
        
        if not out.isOpened():
            cap.release()
            raise ValueError(f"Cannot open video writer for {output_path}")
        
        self.crowd_detector.reset_stats()
        self.weapon_detector.reset_stats()
        
        max_crowd = 0
        total_unique = 0
        weapon_detected_ever = False
        highest_sev = "NORMAL"
        frame_count = 0
        skip_every = 3  # Process every 3rd frame for speed
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                
                # Skip frames for faster processing
                if frame_count % skip_every != 0:
                    out.write(frame)  # Write unprocessed frame
                    frame_count += 1
                    continue
                
                h, w = frame.shape[:2]
                scale = self.downscale_width / float(w)
                new_h = int(h * scale)
                small_frame = cv2.resize(frame, (self.downscale_width, new_h))
                
                crowd_res = self.crowd_detector.count_people(small_frame)
                weapon_res = self.weapon_detector.detect_weapons(small_frame)
                
                if crowd_res["current_crowd_count"] > max_crowd:
                    max_crowd = crowd_res["current_crowd_count"]
                total_unique = crowd_res["total_unique_people"]
                if weapon_res["threat_detected"]:
                    weapon_detected_ever = True
                
                risk_info = compute_risk(
                    crowd_count=crowd_res["current_crowd_count"],
                    weapon_detected=weapon_res["threat_detected"],
                    weapon_severity=weapon_res["highest_severity"]
                )
                
                # Annotate
                annotated = frame.copy()
                scale_x = w / self.downscale_width
                scale_y = h / small_frame.shape[0]
                
                for det in crowd_res["detections"]:
                    x1, y1, x2, y2 = det["bbox"]
                    x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
                    y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 128, 0), 2)
                    prefix = f"ID:{det['id']} " if det['id'] else ""
                    cv2.putText(annotated, f"{prefix}Person", (x1, max(y1-5, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,128,0), 2)
                    
                for wdet in weapon_res["detections"]:
                    wx1, wy1, wx2, wy2 = wdet["bbox"]
                    wx1, wx2 = int(wx1 * scale_x), int(wx2 * scale_x)
                    wy1, wy2 = int(wy1 * scale_y), int(wy2 * scale_y)
                    color = (0, 0, 255) if wdet["severity"] in ["EXTREME", "HIGH"] else (0, 165, 255)
                    cv2.rectangle(annotated, (wx1, wy1), (wx2, wy2), color, 3)
                    label = f"{wdet['class_name']} ({wdet['severity']})"
                    cv2.putText(annotated, label, (wx1, max(wy1-10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                cv2.rectangle(annotated, (0, 0), (w, 40), (0,0,0), -1)
                overlay_text = f"Crowd: {crowd_res['current_crowd_count']} | Risk: {risk_info['risk_level']}"
                cv2.putText(annotated, overlay_text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
                
                out.write(annotated)
                frame_count += 1
        finally:
            cap.release()
            out.release()
        
        # Determine highest severity historically
        if max_crowd > 50 and weapon_detected_ever:
            highest_sev = "CRITICAL"
        elif max_crowd > 30 or weapon_detected_ever:
            highest_sev = "WARNING"
            
        return {
            "crowd_count": max_crowd,
            "unique_count": total_unique,
            "weapon_detected": weapon_detected_ever,
            "total_weapons": self.weapon_detector.total_weapons_detected,
            "risk_level": highest_sev,
            "message": "Analysis Complete"
        }
