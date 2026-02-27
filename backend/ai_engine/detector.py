import json
from typing import Any, Dict, List, Tuple, Optional
import collections

import cv2
import numpy as np
from ultralytics import YOLO


class YOLOv8CrowdDetector:
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        device: str = "cpu",
        person_class_name: str = "person",
        conf_threshold: float = 0.25,
        history_len: int = 150, # Keep tracking last 150 frames for heatmap
    ):
        self.model_path = model_path
        self.device = device
        self.person_class_name = person_class_name
        self.conf_threshold = conf_threshold
        self.model = YOLO(model_path)
        self.model.to(device)
        self.center_history = collections.deque(maxlen=history_len)

    def detect(
        self,
        image: Any,
        roi: Optional[Tuple[int, int, int, int]] = None,
        area_m2: Optional[float] = None,
        return_image: bool = False,
        overlay_heatmap: bool = False,
    ) -> Dict[str, Any]:

        img = self._extract_roi(image, roi)
        results = self.model(img, imgsz=960)[0]

        detections = []
        current_centers = []

        for box, cls_id, conf in zip(
            results.boxes.xyxy,
            results.boxes.cls,
            results.boxes.conf,
        ):
            label = self.model.names[int(cls_id.item())]

            if label != self.person_class_name:
                continue

            if float(conf) < self.conf_threshold:
                continue

            # Calculate center point for heatmap
            x1, y1, x2, y2 = [float(coord) for coord in box.tolist()]
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            current_centers.append((cx, cy))

            detections.append(
                {
                    "bbox": [x1, y1, x2, y2],
                    "score": float(conf.item()),
                }
            )

        # Store centers in history
        self.center_history.append(current_centers)

        total_people = len(detections)

        density = None
        if area_m2 and area_m2 > 0:
            density = total_people / area_m2

        output = {
            "total_people": total_people,
            "density_per_m2": density,
            "detections": detections,
            "roi": list(roi) if roi else None,
            "image_shape": self._get_image_shape(img),
        }

        if return_image:
            annotated = self._draw_boxes(img, detections)
            if overlay_heatmap:
                annotated = self._draw_heatmap(annotated)
            output["annotated_image"] = annotated

        return output

    def _extract_roi(self, image: Any, roi: Optional[Tuple[int, int, int, int]]) -> Any:
        if roi is None:
            return image

        x, y, w, h = roi
        return image[y : y + h, x : x + w]

    def _get_image_shape(self, image: Any) -> Tuple[int, int, int]:
        if image.ndim == 2:
            h, w = image.shape
            c = 1
        else:
            h, w, c = image.shape
        return (h, w, c)

    def _draw_boxes(self, image: Any, detections: List[Dict[str, Any]]) -> Any:
        img = image.copy()

        for det in detections:
            x1, y1, x2, y2 = map(int, det["bbox"])

            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 128, 0), 2)
            # Hide text to make it cleaner like the ref images
            # Option to add 'ID' visually, but YOLOv8 base is just object detection
            cv2.putText(
                img,
                f"PERSON",
                (x1, max(y1 - 5, 0)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 128, 0),
                1,
            )

        return img

    def _draw_heatmap(self, image: Any) -> Any:
        # Create a blank single-channel image
        heatmap = np.zeros(image.shape[:2], dtype=np.float32)

        # Iterate all tracked centers
        for centers_in_frame in self.center_history:
            for cx, cy in centers_in_frame:
                if 0 <= cy < heatmap.shape[0] and 0 <= cx < heatmap.shape[1]:
                    # Add a gaussian blob
                    cv2.circle(heatmap, (cx, cy), 40, 1.0, -1)

        # Smooth and normalize
        heatmap = cv2.GaussianBlur(heatmap, (61, 61), 0)
        if np.max(heatmap) > 0:
            heatmap = heatmap / np.max(heatmap)
            
        # Convert to 8-bit
        heatmap_8u = np.uint8(255 * heatmap)
        
        # Apply colormap
        heatmap_color = cv2.applyColorMap(heatmap_8u, cv2.COLORMAP_JET)

        # Blend with original image
        alpha = 0.5
        mask = heatmap > 0.05  # Only blend where heatmap has data to keep base crisp
        result = image.copy()
        result[mask] = cv2.addWeighted(result, 1 - alpha, heatmap_color, alpha, 0)[mask]

        return result

    def clear_history(self):
        self.center_history.clear()

    def to_json(self, detection_result: Dict[str, Any]) -> str:
        result = dict(detection_result)
        if "annotated_image" in result:
            del result["annotated_image"]
        return json.dumps(result, indent=2)