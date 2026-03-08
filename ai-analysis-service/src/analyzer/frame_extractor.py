"""Extract frames from a video at a configurable sample rate."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

import cv2
import numpy as np
from loguru import logger


@dataclass
class FrameData:
    frame_index: int
    timestamp_sec: float
    image: np.ndarray


class FrameExtractor:
    """
    Extracts frames from a video file at a given FPS sample rate.
    Uses lazy generator to avoid loading all frames into memory at once.
    """

    def __init__(self, sample_fps: int = 5, max_duration_sec: int = 60):
        self.sample_fps = sample_fps
        self.max_duration_sec = max_duration_sec

    def extract_frames(self, video_path: str | Path) -> Generator[FrameData, None, None]:
        path = str(video_path)
        cap = cv2.VideoCapture(path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {path}")

        video_fps: float = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / video_fps

        if duration_sec > self.max_duration_sec:
            logger.warning(
                "Video duration {:.1f}s exceeds max {}s – truncating",
                duration_sec,
                self.max_duration_sec,
            )
            duration_sec = self.max_duration_sec

        # Calculate which frame indices to sample
        frame_interval = max(1, int(video_fps / self.sample_fps))
        max_frame = min(total_frames, int(duration_sec * video_fps))

        logger.info(
            "Extracting frames: video_fps={:.1f} sample_fps={} interval={} total_sampled={}",
            video_fps,
            self.sample_fps,
            frame_interval,
            max_frame // frame_interval,
        )

        frame_idx = 0
        sampled = 0
        try:
            while frame_idx < max_frame:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = frame_idx / video_fps
                yield FrameData(
                    frame_index=sampled,
                    timestamp_sec=timestamp,
                    image=frame,
                )
                sampled += 1
                frame_idx += frame_interval
        finally:
            cap.release()

        logger.info("Extracted {} frames from {}", sampled, path)
