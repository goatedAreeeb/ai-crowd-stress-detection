"""
Rolling-window FPS counter.
"""
import time
from collections import deque


class FPSCounter:
    """Tracks FPS using a sliding window of timestamps."""

    def __init__(self, window: int = 30):
        self._timestamps: deque = deque(maxlen=window)
        self._fps: float = 0.0

    def tick(self):
        """Call once per frame."""
        now = time.perf_counter()
        self._timestamps.append(now)
        if len(self._timestamps) >= 2:
            elapsed = self._timestamps[-1] - self._timestamps[0]
            if elapsed > 0:
                self._fps = (len(self._timestamps) - 1) / elapsed

    @property
    def fps(self) -> float:
        return round(self._fps, 1)
