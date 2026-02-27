"""
Temporal Smoothing — Confirm detections across N consecutive frames.
Prevents flickering / false positives for weapon detection.
"""
from collections import defaultdict
from typing import Dict, List, Any, Set


class TemporalSmoother:
    """
    Tracks detection IDs across frames.
    A detection is only "confirmed" if it appears in `min_frames`
    consecutive frames.
    """

    def __init__(self, min_frames: int = 3):
        self.min_frames = min_frames
        # track_id -> consecutive frame count
        self._streak: Dict[int, int] = defaultdict(int)
        # IDs seen in the current frame
        self._current_ids: Set[int] = set()
        # Confirmed IDs (have hit the streak threshold)
        self._confirmed: Set[int] = set()

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Feed in raw detections for one frame.
        Returns only detections that have been confirmed
        (appeared in >= min_frames consecutive frames).
        """
        seen_ids: Set[int] = set()
        for det in detections:
            tid = det.get("id")
            if tid is None:
                continue
            seen_ids.add(tid)

        # Increment streak for IDs still present, reset for missing
        new_streak: Dict[int, int] = defaultdict(int)
        for tid in seen_ids:
            new_streak[tid] = self._streak.get(tid, 0) + 1
        self._streak = new_streak

        # Determine confirmed set
        self._confirmed = {
            tid for tid, count in self._streak.items()
            if count >= self.min_frames
        }
        self._current_ids = seen_ids

        # Filter detections to only confirmed
        confirmed_detections = [
            det for det in detections
            if det.get("id") in self._confirmed
        ]
        return confirmed_detections

    @property
    def confirmed_ids(self) -> Set[int]:
        return self._confirmed.copy()

    def reset(self):
        self._streak.clear()
        self._confirmed.clear()
        self._current_ids.clear()
