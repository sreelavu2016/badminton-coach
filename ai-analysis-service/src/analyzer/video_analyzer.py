"""
High-level orchestrator: runs the full analysis pipeline on a single video.

Pipeline:
  1. Extract frames (FrameExtractor)
  2. Detect pose per frame (PoseDetector)
  3. Calculate joint metrics per frame (JointCalculator)
  4. Detect badminton movements (MovementDetector)
  5. Compute technique scores (TechniqueScorer)
  6. Generate feedback (FeedbackGenerator)
  7. Return AnalysisPipelineResult
"""
import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger

from .frame_extractor import FrameExtractor
from .joint_calculator import JointCalculator
from .pose_detector import PoseDetector
from ..detector.movement_detector import MovementDetector
from ..feedback.feedback_generator import FeedbackGenerator, FeedbackItem
from ..scorer.technique_scorer import TechniqueScorer


@dataclass
class AnalysisPipelineResult:
    video_id: str
    user_id: str
    smash_score: int
    serve_score: int
    footwork_score: int
    posture_score: int
    overall_score: int
    feedback_items: list[FeedbackItem]
    metrics_json: str
    frame_count: int
    detected_frames: int


class VideoAnalyzer:
    """
    Thread-safe video analysis pipeline.
    Create one instance per worker thread / process.
    """

    def __init__(
        self,
        sample_fps: int = 5,
        max_duration_sec: int = 60,
        min_pose_confidence: float = 0.5,
    ):
        self.extractor = FrameExtractor(sample_fps, max_duration_sec)
        self.joint_calc = JointCalculator()
        self.movement_detector = MovementDetector()
        self.scorer = TechniqueScorer()
        self.feedback_gen = FeedbackGenerator()
        self.min_pose_confidence = min_pose_confidence

    def analyze(self, video_path: str | Path, video_id: str, user_id: str) -> AnalysisPipelineResult:
        logger.info("Starting analysis: video_id={} path={}", video_id, video_path)

        frame_metrics: list[dict] = []
        frame_count = 0
        detected_count = 0

        with PoseDetector(min_detection_confidence=self.min_pose_confidence,
                          min_tracking_confidence=self.min_pose_confidence) as detector:

            for frame_data in self.extractor.extract_frames(video_path):
                frame_count += 1
                pose = detector.detect(frame_data)

                if pose.detected:
                    detected_count += 1
                    metrics = self.joint_calc.compute(pose)
                    metrics["timestamp_sec"] = frame_data.timestamp_sec
                    frame_metrics.append(metrics)
                else:
                    frame_metrics.append({"timestamp_sec": frame_data.timestamp_sec})

        logger.info("Pose detected in {}/{} frames", detected_count, frame_count)

        if detected_count == 0:
            logger.warning("No pose detected in any frame – returning default scores")
            return self._default_result(video_id, user_id, frame_count)

        events = self.movement_detector.detect(frame_metrics)

        smash = self.scorer.score_smash(frame_metrics, events)
        serve = self.scorer.score_serve(frame_metrics, events)
        footwork = self.scorer.score_footwork(frame_metrics, events)
        posture = self.scorer.score_posture(frame_metrics, events)
        overall = self.scorer.compute_overall(smash, serve, footwork, posture)

        feedback = self.feedback_gen.generate(
            smash, serve, footwork, posture, frame_metrics, events
        )

        # Summarise metrics for storage
        summary = self._summarise_metrics(frame_metrics, events)
        metrics_json = json.dumps(summary)

        logger.info(
            "Analysis complete video_id={}: smash={} serve={} footwork={} posture={} overall={}",
            video_id, smash, serve, footwork, posture, overall
        )

        return AnalysisPipelineResult(
            video_id=video_id,
            user_id=user_id,
            smash_score=smash,
            serve_score=serve,
            footwork_score=footwork,
            posture_score=posture,
            overall_score=overall,
            feedback_items=feedback,
            metrics_json=metrics_json,
            frame_count=frame_count,
            detected_frames=detected_count,
        )

    def _default_result(self, video_id: str, user_id: str, frame_count: int) -> AnalysisPipelineResult:
        from ..feedback.feedback_generator import FeedbackItem
        return AnalysisPipelineResult(
            video_id=video_id,
            user_id=user_id,
            smash_score=0,
            serve_score=0,
            footwork_score=0,
            posture_score=0,
            overall_score=0,
            feedback_items=[FeedbackItem(
                category="POSTURE",
                severity="CRITICAL",
                message="No player detected in video",
                detail="Ensure the video shows a single player clearly visible from head to toe.",
            )],
            metrics_json="{}",
            frame_count=frame_count,
            detected_frames=0,
        )

    @staticmethod
    def _summarise_metrics(frame_metrics: list[dict], events: dict) -> dict:
        def safe_mean(key):
            vals = [m.get(key) for m in frame_metrics if m.get(key) is not None]
            return round(statistics.mean(vals), 2) if vals else None

        return {
            "avg_right_elbow_angle": safe_mean("right_elbow_angle"),
            "avg_left_elbow_angle": safe_mean("left_elbow_angle"),
            "avg_right_shoulder_angle": safe_mean("right_shoulder_angle"),
            "avg_trunk_lean_deg": safe_mean("trunk_lean_deg"),
            "avg_knee_angle": safe_mean("right_knee_angle"),
            "avg_ankle_hip_ratio": safe_mean("ankle_to_hip_ratio"),
            "smash_count": len(events.get("smash_frames", [])),
            "serve_count": len(events.get("serve_frames", [])),
            "step_count": events.get("step_count", 0),
            "avg_recovery_frames": (
                round(statistics.mean(events["recovery_times"]), 1)
                if events.get("recovery_times") else None
            ),
        }
