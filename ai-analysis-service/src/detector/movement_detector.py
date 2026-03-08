"""
Detect badminton movement events from a sequence of per-frame metrics.

Heuristics used:
  Smash  – wrist rapidly above shoulder + high elbow angle → fast downward snap
  Serve  – wrist rises steadily above shoulder height with body upright
  Footwork – COM displacement between frames
"""
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from loguru import logger


@dataclass
class MovementEvent:
    event_type: str          # "smash" | "serve" | "step"
    start_frame: int
    peak_frame: int
    metric_value: float      # primary metric that triggered detection
    side: str = "right"      # dominant side detected


class MovementDetector:
    """
    Processes a list of per-frame metric dicts and returns detected events.
    """

    # Thresholds
    SMASH_ELBOW_ANGLE_MIN = 100       # elbow must be at least this open at wind-up
    SMASH_WRIST_RISE_MIN = 0.05       # wrist above shoulder by this much (normalised)
    SERVE_WRIST_RISE_MIN = 0.03
    SERVE_MIN_CONSECUTIVE = 3          # frames with wrist above shoulder
    STEP_COM_THRESHOLD = 0.015         # normalised COM displacement per sample frame

    def detect(self, frame_metrics: list[dict]) -> dict:
        """
        frame_metrics: list of metric dicts (one per sampled frame, index = frame order)
        Returns dict with keys: smash_frames, serve_frames, step_count, recovery_times
        """
        smash_frames: list[int] = []
        serve_frames: list[int] = []
        com_history: list[tuple[float, float]] = []
        step_count = 0
        recovery_times: list[float] = []   # seconds between shot and return to centre

        # Extract relevant series
        right_wrist_above = self._series(frame_metrics, "right_wrist_above_shoulder")
        right_elbow = self._series(frame_metrics, "right_elbow_angle")
        com_x_series = self._series(frame_metrics, "com_x")
        com_y_series = self._series(frame_metrics, "com_y")
        trunk_lean = self._series(frame_metrics, "trunk_lean_deg")

        # Smash detection: wrist high + elbow open → fast wrist drop
        for i in range(1, len(frame_metrics)):
            wrise = right_wrist_above.get(i)
            elbow = right_elbow.get(i)
            prev_wrise = right_wrist_above.get(i - 1)

            if wrise is None or elbow is None or prev_wrise is None:
                continue

            is_wrist_high = wrise > self.SMASH_WRIST_RISE_MIN
            is_elbow_open = elbow > self.SMASH_ELBOW_ANGLE_MIN
            # Smash = wrist was rising last frame and drops this frame
            is_downswing = prev_wrise > wrise and wrise > self.SMASH_WRIST_RISE_MIN * 0.5

            if is_wrist_high and is_elbow_open and is_downswing:
                smash_frames.append(i)

        # Serve detection: wrist rises above shoulder for multiple consecutive frames
        # with upright trunk
        consecutive = 0
        for i, metrics in enumerate(frame_metrics):
            wrise = right_wrist_above.get(i, 0.0)
            lean = trunk_lean.get(i, 90.0)

            if wrise and wrise > self.SERVE_WRIST_RISE_MIN and lean < 20:
                consecutive += 1
                if consecutive >= self.SERVE_MIN_CONSECUTIVE:
                    serve_frames.append(i)
            else:
                consecutive = 0

        # Footwork: count significant COM displacements
        prev_com = None
        for i in range(len(frame_metrics)):
            cx = com_x_series.get(i)
            cy = com_y_series.get(i)
            if cx is None or cy is None:
                continue
            com = (cx, cy)
            if prev_com is not None:
                dist = np.hypot(com[0] - prev_com[0], com[1] - prev_com[1])
                if dist > self.STEP_COM_THRESHOLD:
                    step_count += 1
            prev_com = com

        # Recovery time: after each smash, time until COM returns near centre (x≈0.5)
        CENTRE_X = 0.5
        CENTRE_TOLERANCE = 0.08
        for sf in smash_frames:
            for i in range(sf, len(frame_metrics)):
                cx = com_x_series.get(i)
                if cx is not None and abs(cx - CENTRE_X) < CENTRE_TOLERANCE:
                    recovery_times.append((i - sf))  # in frame units
                    break

        logger.debug(
            "Detected smash_frames={} serve_frames={} steps={} recoveries={}",
            len(smash_frames), len(serve_frames), step_count, recovery_times
        )

        return {
            "smash_frames": smash_frames,
            "serve_frames": serve_frames,
            "step_count": step_count,
            "recovery_times": recovery_times,
        }

    @staticmethod
    def _series(frame_metrics: list[dict], key: str) -> dict[int, Optional[float]]:
        return {i: m.get(key) for i, m in enumerate(frame_metrics)}
