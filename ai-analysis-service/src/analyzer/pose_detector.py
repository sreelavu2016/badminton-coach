"""MediaPipe Pose wrapper – detect 33 body landmarks per frame."""
from dataclasses import dataclass, field
from typing import Optional

import mediapipe as mp
import numpy as np
from loguru import logger

# MediaPipe landmark indices (subset we care about)
LANDMARK = {
    "nose": 0,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13,    "right_elbow": 14,
    "left_wrist": 15,    "right_wrist": 16,
    "left_hip": 23,      "right_hip": 24,
    "left_knee": 25,     "right_knee": 26,
    "left_ankle": 27,    "right_ankle": 28,
}


@dataclass
class Keypoint:
    name: str
    x: float          # normalised [0,1]
    y: float          # normalised [0,1]
    z: float          # relative depth
    visibility: float # confidence


@dataclass
class PoseResult:
    frame_index: int
    timestamp_sec: float
    keypoints: dict[str, Keypoint] = field(default_factory=dict)
    detected: bool = False


class PoseDetector:
    """
    Wraps MediaPipe Pose for single-image inference.
    One instance should be reused across frames (model is heavy to load).
    """

    def __init__(self, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,          # 0=lite, 1=full, 2=heavy
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, frame_data) -> PoseResult:
        import cv2
        rgb_frame = cv2.cvtColor(frame_data.image, cv2.COLOR_BGR2RGB)
        results = self._pose.process(rgb_frame)

        pose_result = PoseResult(
            frame_index=frame_data.frame_index,
            timestamp_sec=frame_data.timestamp_sec,
        )

        if not results.pose_landmarks:
            return pose_result

        pose_result.detected = True
        landmarks = results.pose_landmarks.landmark

        for name, idx in LANDMARK.items():
            lm = landmarks[idx]
            pose_result.keypoints[name] = Keypoint(
                name=name,
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibility=lm.visibility,
            )

        return pose_result

    def close(self):
        self._pose.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
