"""
Generates faulty/ideal frame pairs for each detected posture issue.

- Faulty frame : actual video frame at the worst-scoring moment, with MediaPipe
                 skeleton drawn and problem joints highlighted in RED.
- Ideal frame  : synthetic stick-figure on a dark background showing the
                 correct position in GREEN, with angle annotations.
"""
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import mediapipe as mp
from loguru import logger

# ── MediaPipe landmark indices (same subset as pose_detector.py) ──────────────
LANDMARK_IDX = {
    "nose": 0,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13,    "right_elbow": 14,
    "left_wrist": 15,    "right_wrist": 16,
    "left_hip": 23,      "right_hip": 24,
    "left_knee": 25,     "right_knee": 26,
    "left_ankle": 27,    "right_ankle": 28,
}

SKELETON_CONNECTIONS = [
    ("nose", "left_shoulder"), ("nose", "right_shoulder"),
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),   ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),     ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),   ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
]

# ── Which joints to highlight per issue ──────────────────────────────────────
ISSUE_JOINTS: dict[str, list[str]] = {
    "knee_bend":       ["left_knee", "right_knee"],
    "elbow_extension": ["right_elbow", "right_wrist", "right_shoulder"],
    "trunk_lean":      ["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
    "stance_width":    ["left_ankle", "right_ankle", "left_hip", "right_hip"],
}

# ── Ideal skeleton joint positions (normalised 0-1) for 480×640 canvas ───────
_W, _H = 480, 640

IDEAL_SKELETONS: dict[str, dict[str, tuple[float, float]]] = {
    "knee_bend": {
        # Athletic ready position — knees bent ~140°, wide stance
        "nose":           (0.50, 0.09),
        "left_shoulder":  (0.37, 0.27), "right_shoulder": (0.63, 0.27),
        "left_elbow":     (0.28, 0.40), "right_elbow":    (0.72, 0.40),
        "left_wrist":     (0.25, 0.51), "right_wrist":    (0.75, 0.51),
        "left_hip":       (0.41, 0.53), "right_hip":      (0.59, 0.53),
        "left_knee":      (0.36, 0.70), "right_knee":     (0.64, 0.70),
        "left_ankle":     (0.31, 0.87), "right_ankle":    (0.69, 0.87),
    },
    "elbow_extension": {
        # Smash position — right arm raised, elbow extended ~155°
        "nose":           (0.50, 0.09),
        "left_shoulder":  (0.40, 0.28), "right_shoulder": (0.60, 0.28),
        "left_elbow":     (0.33, 0.40), "right_elbow":    (0.73, 0.15),
        "left_wrist":     (0.29, 0.51), "right_wrist":    (0.82, 0.05),
        "left_hip":       (0.42, 0.53), "right_hip":      (0.58, 0.53),
        "left_knee":      (0.40, 0.70), "right_knee":     (0.60, 0.70),
        "left_ankle":     (0.36, 0.87), "right_ankle":    (0.64, 0.87),
    },
    "trunk_lean": {
        # Upright spine — trunk lean < 10°
        "nose":           (0.50, 0.09),
        "left_shoulder":  (0.38, 0.28), "right_shoulder": (0.62, 0.28),
        "left_elbow":     (0.30, 0.42), "right_elbow":    (0.70, 0.42),
        "left_wrist":     (0.27, 0.55), "right_wrist":    (0.73, 0.55),
        "left_hip":       (0.41, 0.53), "right_hip":      (0.59, 0.53),
        "left_knee":      (0.39, 0.70), "right_knee":     (0.61, 0.70),
        "left_ankle":     (0.37, 0.87), "right_ankle":    (0.63, 0.87),
    },
    "stance_width": {
        # Wide stance — feet ~1.5× hip width
        "nose":           (0.50, 0.09),
        "left_shoulder":  (0.38, 0.28), "right_shoulder": (0.62, 0.28),
        "left_elbow":     (0.28, 0.42), "right_elbow":    (0.72, 0.42),
        "left_wrist":     (0.24, 0.55), "right_wrist":    (0.76, 0.55),
        "left_hip":       (0.42, 0.53), "right_hip":      (0.58, 0.53),
        "left_knee":      (0.36, 0.70), "right_knee":     (0.64, 0.70),
        "left_ankle":     (0.23, 0.87), "right_ankle":    (0.77, 0.87),
    },
}

FAULTY_LABELS: dict[str, str] = {
    "knee_bend":       "Issue: Knees too straight (>165 deg)\nReduces power & balance",
    "elbow_extension": "Issue: Elbow not extended (<110 deg)\nLimits smash power",
    "trunk_lean":      "Issue: Excessive trunk lean (>30 deg)\nReduces reaction time",
    "stance_width":    "Issue: Narrow stance\nReduces lateral stability",
}

IDEAL_LABELS: dict[str, str] = {
    "knee_bend":       "Ideal: Bend knees to 130-150 deg\nAthletic ready position",
    "elbow_extension": "Ideal: Extend elbow to 145 deg+\nFull smash power",
    "trunk_lean":      "Ideal: Keep spine upright\nLean < 10 deg at address",
    "stance_width":    "Ideal: Feet wider than hips (1.3x+)\nStable balanced base",
}


class FrameComparator:
    """Generates faulty / ideal frame pairs for detected posture issues."""

    CANVAS_W = _W
    CANVAS_H = _H
    JPEG_QUALITY = 78

    # ── Public API ────────────────────────────────────────────────────────────

    def save_frame_pair(
        self,
        video_path: str | Path,
        timestamp_sec: float,
        issue_type: str,
        video_id: str,
        frames_dir: Path,
    ) -> tuple[str, str]:
        """
        Generate and persist a faulty + ideal frame image for one issue.
        Returns (faulty_relative_url, ideal_relative_url) suitable for the
        Video Service frames endpoint.
        """
        frames_dir.mkdir(parents=True, exist_ok=True)

        faulty_file = f"faulty_{issue_type}.jpg"
        ideal_file  = f"ideal_{issue_type}.jpg"

        faulty_img = self._extract_faulty_frame(video_path, timestamp_sec, issue_type)
        if faulty_img is None:
            faulty_img = self._blank_dark(text="Frame unavailable")

        ideal_img = self._draw_ideal_frame(issue_type)

        cv2.imwrite(str(frames_dir / faulty_file), faulty_img,
                    [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY])
        cv2.imwrite(str(frames_dir / ideal_file), ideal_img,
                    [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY])

        logger.info("Saved frame pair: issue={} video_id={}", issue_type, video_id)
        return (
            f"storage/frames/{video_id}/{faulty_file}",
            f"storage/frames/{video_id}/{ideal_file}",
        )

    # ── Faulty frame ──────────────────────────────────────────────────────────

    def _extract_faulty_frame(
        self,
        video_path: str | Path,
        timestamp_sec: float,
        issue_type: str,
    ) -> Optional[np.ndarray]:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.warning("Cannot open video for frame capture: {}", video_path)
            return None

        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000)
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame at {}s", timestamp_sec)
                return None

            frame = cv2.resize(frame, (self.CANVAS_W, self.CANVAS_H))
            faulty_joints = set(ISSUE_JOINTS.get(issue_type, []))

            # Run a quick MediaPipe pass on this single frame
            mp_pose = mp.solutions.pose
            with mp_pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                min_detection_confidence=0.4,
            ) as pose:
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)

            if results.pose_landmarks:
                h, w = frame.shape[:2]
                lms  = results.pose_landmarks.landmark
                pts: dict[str, tuple[int, int]] = {}
                for name, idx in LANDMARK_IDX.items():
                    lm = lms[idx]
                    if lm.visibility > 0.3:
                        pts[name] = (int(lm.x * w), int(lm.y * h))

                for a, b in SKELETON_CONNECTIONS:
                    if a in pts and b in pts:
                        bad   = a in faulty_joints or b in faulty_joints
                        color = (0, 0, 220) if bad else (0, 220, 0)
                        cv2.line(frame, pts[a], pts[b], color, 3, cv2.LINE_AA)

                for name, pt in pts.items():
                    bad    = name in faulty_joints
                    color  = (0, 0, 255) if bad else (0, 255, 0)
                    radius = 10 if bad else 7
                    cv2.circle(frame, pt, radius, color,         -1, cv2.LINE_AA)
                    cv2.circle(frame, pt, radius, (255, 255, 255), 2, cv2.LINE_AA)

            # Semi-transparent header banner
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (self.CANVAS_W, 72), (20, 8, 8), -1)
            cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

            cv2.putText(frame, "YOUR POSTURE", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.66, (180, 180, 255), 2, cv2.LINE_AA)
            for i, line in enumerate(FAULTY_LABELS.get(issue_type, "").split("\n")):
                cv2.putText(frame, line, (10, 46 + i * 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.44, (100, 120, 255), 1, cv2.LINE_AA)

            cv2.putText(frame, f"t = {timestamp_sec:.1f}s",
                        (self.CANVAS_W - 90, self.CANVAS_H - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 120, 120), 1, cv2.LINE_AA)
            return frame

        finally:
            cap.release()

    # ── Ideal frame ───────────────────────────────────────────────────────────

    def _draw_ideal_frame(self, issue_type: str) -> np.ndarray:
        canvas   = np.zeros((self.CANVAS_H, self.CANVAS_W, 3), dtype=np.uint8)
        canvas[:] = (18, 15, 35)  # dark navy

        skeleton       = IDEAL_SKELETONS.get(issue_type, IDEAL_SKELETONS["knee_bend"])
        highlight_set  = set(ISSUE_JOINTS.get(issue_type, []))

        pts = {
            name: (int(x * self.CANVAS_W), int(y * self.CANVAS_H))
            for name, (x, y) in skeleton.items()
        }

        # Bones
        for a, b in SKELETON_CONNECTIONS:
            if a in pts and b in pts:
                is_key = a in highlight_set or b in highlight_set
                color  = (80, 255, 120) if is_key else (50, 160, 70)
                cv2.line(canvas, pts[a], pts[b], color, 3, cv2.LINE_AA)

        # Joints
        for name, pt in pts.items():
            is_key = name in highlight_set
            color  = (100, 255, 140) if is_key else (55, 190, 85)
            radius = 11 if is_key else 7
            cv2.circle(canvas, pt, radius, color,           -1, cv2.LINE_AA)
            cv2.circle(canvas, pt, radius, (200, 255, 210),  2, cv2.LINE_AA)

        # Header
        cv2.rectangle(canvas, (0, 0), (self.CANVAS_W, 72), (10, 28, 14), -1)
        cv2.putText(canvas, "IDEAL POSTURE", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.66, (100, 255, 140), 2, cv2.LINE_AA)
        for i, line in enumerate(IDEAL_LABELS.get(issue_type, "").split("\n")):
            cv2.putText(canvas, line, (10, 46 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (70, 200, 100), 1, cv2.LINE_AA)

        # Watermark
        cv2.putText(canvas, "AI Badminton Coach", (10, self.CANVAS_H - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (50, 70, 50), 1, cv2.LINE_AA)
        return canvas

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _blank_dark(self, text: str = "") -> np.ndarray:
        canvas = np.zeros((self.CANVAS_H, self.CANVAS_W, 3), dtype=np.uint8)
        canvas[:] = (25, 20, 35)
        if text:
            cv2.putText(canvas, text, (20, self.CANVAS_H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 120), 1, cv2.LINE_AA)
        return canvas
