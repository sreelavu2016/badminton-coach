"""
Calculate joint angles and kinematic metrics from keypoints.

All angle calculations use the law of cosines on the 2D (x,y) plane.
"""
import math
from typing import Optional

from .pose_detector import Keypoint, PoseResult


def _angle(a: Keypoint, b: Keypoint, c: Keypoint) -> Optional[float]:
    """
    Calculate angle at joint B formed by points A-B-C.
    Returns degrees [0, 180] or None if visibility is too low.
    """
    if min(a.visibility, b.visibility, c.visibility) < 0.4:
        return None

    ba = (a.x - b.x, a.y - b.y)
    bc = (c.x - b.x, c.y - b.y)

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)

    if mag_ba < 1e-6 or mag_bc < 1e-6:
        return None

    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


def _distance(a: Keypoint, b: Keypoint) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


class JointCalculator:
    """
    Compute per-frame joint angles and derived metrics.
    All angles returned in degrees.
    """

    def compute(self, pose: PoseResult) -> dict:
        kp = pose.keypoints
        metrics: dict = {}

        if not pose.detected:
            return metrics

        def get(*names) -> Optional[tuple]:
            pts = [kp.get(n) for n in names]
            return tuple(pts) if all(p is not None for p in pts) else None

        # --- Elbow angles ---
        pts = get("left_shoulder", "left_elbow", "left_wrist")
        if pts:
            metrics["left_elbow_angle"] = _angle(*pts)

        pts = get("right_shoulder", "right_elbow", "right_wrist")
        if pts:
            metrics["right_elbow_angle"] = _angle(*pts)

        # --- Shoulder abduction (rough proxy via hip-shoulder-elbow) ---
        pts = get("left_hip", "left_shoulder", "left_elbow")
        if pts:
            metrics["left_shoulder_angle"] = _angle(*pts)

        pts = get("right_hip", "right_shoulder", "right_elbow")
        if pts:
            metrics["right_shoulder_angle"] = _angle(*pts)

        # --- Knee angles ---
        pts = get("left_hip", "left_knee", "left_ankle")
        if pts:
            metrics["left_knee_angle"] = _angle(*pts)

        pts = get("right_hip", "right_knee", "right_ankle")
        if pts:
            metrics["right_knee_angle"] = _angle(*pts)

        # --- Hip alignment (shoulder-hip-knee) ---
        pts = get("left_shoulder", "left_hip", "left_knee")
        if pts:
            metrics["left_hip_angle"] = _angle(*pts)

        pts = get("right_shoulder", "right_hip", "right_knee")
        if pts:
            metrics["right_hip_angle"] = _angle(*pts)

        # --- Trunk lean: angle of shoulder-midpoint to hip-midpoint vector ---
        ls = kp.get("left_shoulder")
        rs = kp.get("right_shoulder")
        lh = kp.get("left_hip")
        rh = kp.get("right_hip")
        if ls and rs and lh and rh:
            mid_shoulder_x = (ls.x + rs.x) / 2
            mid_shoulder_y = (ls.y + rs.y) / 2
            mid_hip_x = (lh.x + rh.x) / 2
            mid_hip_y = (lh.y + rh.y) / 2
            dx = mid_shoulder_x - mid_hip_x
            dy = mid_shoulder_y - mid_hip_y
            # trunk lean from vertical (0 = upright)
            metrics["trunk_lean_deg"] = math.degrees(math.atan2(abs(dx), abs(dy)))

        # --- Wrist height relative to shoulder ---
        lw = kp.get("left_wrist")
        rw = kp.get("right_wrist")
        if ls and lw:
            # Negative means wrist is above shoulder (y increases downward in image coords)
            metrics["left_wrist_above_shoulder"] = ls.y - lw.y
        if rs and rw:
            metrics["right_wrist_above_shoulder"] = rs.y - rw.y

        # --- Centre of mass proxy (mid hip x) ---
        if lh and rh:
            metrics["com_x"] = (lh.x + rh.x) / 2
            metrics["com_y"] = (lh.y + rh.y) / 2

        # --- Ankle spread (foot width relative to hip width) ---
        la = kp.get("left_ankle")
        ra = kp.get("right_ankle")
        if la and ra and lh and rh:
            ankle_width = _distance(la, ra)
            hip_width = _distance(lh, rh)
            metrics["ankle_to_hip_ratio"] = ankle_width / max(hip_width, 1e-6)

        return metrics
