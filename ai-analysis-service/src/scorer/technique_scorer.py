"""
Compute technique scores [0-100] from aggregated frame metrics and detected events.

Each scorer is a pure function: (aggregated_metrics, events) → int score.
"""
import statistics
from typing import Optional
import numpy as np
from loguru import logger


def _safe_mean(values: list) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return statistics.mean(vals) if vals else None


def _clamp(val: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, val)))


class TechniqueScorer:
    """
    Produces four technique scores from the analysis data.
    Uses a weighted rubric approach with heuristic thresholds.
    """

    # ------------------------------------------------------------------ SMASH
    IDEAL_ELBOW_ANGLE_AT_IMPACT = 155    # degrees – arm nearly straight at contact
    IDEAL_SHOULDER_ANGLE = 160           # shoulder abduction
    IDEAL_WRIST_ABOVE_SHOULDER = 0.12    # normalised units

    # ----------------------------------------------------------------- SERVE
    IDEAL_SERVE_WRIST_HEIGHT = 0.06
    IDEAL_TRUNK_UPRIGHT = 5.0            # degrees lean (less = more upright)

    # -------------------------------------------------------------- FOOTWORK
    IDEAL_STEPS_PER_SMASH = 3.5          # avg steps taken around each shot
    MAX_RECOVERY_FRAMES = 4              # frames – at 5fps → 0.8 seconds

    # -------------------------------------------------------------- POSTURE
    IDEAL_KNEE_ANGLE = 145               # slightly bent
    IDEAL_HIP_ANGLE = 160                # upright hip
    IDEAL_ANKLE_HIP_RATIO = 1.3          # wider stance than hips

    def score_smash(self, frame_metrics: list[dict], events: dict) -> int:
        smash_frames = events.get("smash_frames", [])
        if not smash_frames:
            logger.debug("No smash frames detected – base score 40")
            return 40  # player may not have smashed in this clip

        elbow_at_smash = [frame_metrics[i].get("right_elbow_angle")
                          for i in smash_frames
                          if i < len(frame_metrics)]
        shoulder_at_smash = [frame_metrics[i].get("right_shoulder_angle")
                              for i in smash_frames
                              if i < len(frame_metrics)]
        wrist_height = [frame_metrics[i].get("right_wrist_above_shoulder")
                        for i in smash_frames
                        if i < len(frame_metrics)]

        # Elbow angle component (higher ≈ fuller extension ≈ better)
        mean_elbow = _safe_mean(elbow_at_smash)
        elbow_score = 100.0
        if mean_elbow is not None:
            diff = abs(mean_elbow - self.IDEAL_ELBOW_ANGLE_AT_IMPACT)
            elbow_score = max(0, 100 - diff * 1.5)

        # Shoulder angle component
        mean_shoulder = _safe_mean(shoulder_at_smash)
        shoulder_score = 100.0
        if mean_shoulder is not None:
            diff = abs(mean_shoulder - self.IDEAL_SHOULDER_ANGLE)
            shoulder_score = max(0, 100 - diff * 1.2)

        # Wrist height component
        mean_wrist = _safe_mean(wrist_height)
        wrist_score = 100.0
        if mean_wrist is not None:
            ratio = mean_wrist / self.IDEAL_WRIST_ABOVE_SHOULDER
            wrist_score = _clamp(min(ratio, 1.0) * 100)

        final = 0.4 * elbow_score + 0.35 * shoulder_score + 0.25 * wrist_score
        logger.debug("smash score components: elbow={:.1f} shoulder={:.1f} wrist={:.1f} final={:.1f}",
                     elbow_score, shoulder_score, wrist_score, final)
        return _clamp(final)

    def score_serve(self, frame_metrics: list[dict], events: dict) -> int:
        serve_frames = events.get("serve_frames", [])
        if not serve_frames:
            return 45  # default if no serve detected

        wrist_heights = [frame_metrics[i].get("right_wrist_above_shoulder")
                         for i in serve_frames if i < len(frame_metrics)]
        trunk_leans = [frame_metrics[i].get("trunk_lean_deg")
                       for i in serve_frames if i < len(frame_metrics)]

        mean_wh = _safe_mean(wrist_heights) or 0.0
        mean_lean = _safe_mean(trunk_leans) or 45.0

        wh_score = _clamp((mean_wh / self.IDEAL_SERVE_WRIST_HEIGHT) * 100)
        lean_score = _clamp(max(0, 100 - (mean_lean - self.IDEAL_TRUNK_UPRIGHT) * 3))

        final = 0.5 * wh_score + 0.5 * lean_score
        return _clamp(final)

    def score_footwork(self, frame_metrics: list[dict], events: dict) -> int:
        step_count = events.get("step_count", 0)
        recovery_times = events.get("recovery_times", [])
        smash_count = max(len(events.get("smash_frames", [])), 1)

        # Steps per shot
        steps_per_shot = step_count / smash_count
        step_score = _clamp((steps_per_shot / self.IDEAL_STEPS_PER_SMASH) * 100)

        # Recovery speed (fewer frames = faster)
        if recovery_times:
            mean_recovery = statistics.mean(recovery_times)
            recovery_score = _clamp(max(0, 100 - (mean_recovery - 1) * 20))
        else:
            recovery_score = 60  # neutral

        final = 0.5 * step_score + 0.5 * recovery_score
        return _clamp(final)

    def score_posture(self, frame_metrics: list[dict], events: dict) -> int:
        knee_angles = [m.get("left_knee_angle") or m.get("right_knee_angle")
                       for m in frame_metrics]
        hip_angles = [m.get("left_hip_angle") or m.get("right_hip_angle")
                      for m in frame_metrics]
        ankle_ratios = [m.get("ankle_to_hip_ratio") for m in frame_metrics]
        trunk_leans = [m.get("trunk_lean_deg") for m in frame_metrics]

        mean_knee = _safe_mean(knee_angles) or self.IDEAL_KNEE_ANGLE
        mean_hip = _safe_mean(hip_angles) or self.IDEAL_HIP_ANGLE
        mean_ratio = _safe_mean(ankle_ratios) or self.IDEAL_ANKLE_HIP_RATIO
        mean_lean = _safe_mean(trunk_leans) or 0.0

        knee_score = _clamp(max(0, 100 - abs(mean_knee - self.IDEAL_KNEE_ANGLE) * 2))
        hip_score = _clamp(max(0, 100 - abs(mean_hip - self.IDEAL_HIP_ANGLE) * 2))
        ratio_score = _clamp(min(mean_ratio / self.IDEAL_ANKLE_HIP_RATIO, 1.0) * 100)
        lean_score = _clamp(max(0, 100 - mean_lean * 3))

        final = 0.3 * knee_score + 0.3 * hip_score + 0.2 * ratio_score + 0.2 * lean_score
        return _clamp(final)

    def compute_overall(self, smash: int, serve: int, footwork: int, posture: int) -> int:
        return _clamp(0.35 * smash + 0.2 * serve + 0.25 * footwork + 0.2 * posture)
