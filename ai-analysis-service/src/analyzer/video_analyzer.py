"""
High-level orchestrator: runs the full analysis pipeline on a single video.

Pipeline:
  1. Extract frames (FrameExtractor)
  2. Detect pose per frame (PoseDetector)
  3. Calculate joint metrics per frame (JointCalculator)
  4. Detect badminton movements (MovementDetector)
  5. Compute technique scores (TechniqueScorer)
  6. Generate frame comparisons – faulty vs ideal (FrameComparator)
  7. Generate feedback (FeedbackGenerator)
  8. Return AnalysisPipelineResult
"""
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

from .frame_comparator import FrameComparator
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
    feedback_items: list
    metrics_json: str
    frame_count: int
    detected_frames: int


# worst_frames init: issue -> [timestamp_sec, comparison_value]
_WORST_INIT = {
    "knee_bend":       [None, -1.0],   # maximise (most straight knees)
    "elbow_extension": [None, 999.0],  # minimise (most bent elbow)
    "trunk_lean":      [None, -1.0],   # maximise (most forward lean)
    "stance_width":    [None, 999.0],  # minimise (narrowest stance)
}


class VideoAnalyzer:
    def __init__(self, sample_fps=5, max_duration_sec=60, min_pose_confidence=0.5):
        self.extractor         = FrameExtractor(sample_fps, max_duration_sec)
        self.joint_calc        = JointCalculator()
        self.movement_detector = MovementDetector()
        self.scorer            = TechniqueScorer()
        self.feedback_gen      = FeedbackGenerator()
        self.comparator        = FrameComparator()
        self.min_pose_confidence = min_pose_confidence

    def analyze(self, video_path, video_id, user_id, frames_storage_path=None):
        logger.info("Starting analysis: video_id={} path={}", video_id, video_path)

        frame_metrics  = []
        frame_count    = 0
        detected_count = 0
        worst_frames   = {k: list(v) for k, v in _WORST_INIT.items()}

        with PoseDetector(
            min_detection_confidence=self.min_pose_confidence,
            min_tracking_confidence=self.min_pose_confidence,
        ) as detector:
            for frame_data in self.extractor.extract_frames(video_path):
                frame_count += 1
                pose = detector.detect(frame_data)
                if pose.detected:
                    detected_count += 1
                    metrics = self.joint_calc.compute(pose)
                    metrics["timestamp_sec"] = frame_data.timestamp_sec
                    frame_metrics.append(metrics)
                    self._update_worst(worst_frames, metrics, frame_data.timestamp_sec)
                else:
                    frame_metrics.append({"timestamp_sec": frame_data.timestamp_sec})

        logger.info("Pose detected in {}/{} frames", detected_count, frame_count)

        if detected_count == 0:
            logger.warning("No pose detected – returning default scores")
            return self._default_result(video_id, user_id, frame_count)

        events   = self.movement_detector.detect(frame_metrics)
        smash    = self.scorer.score_smash(frame_metrics, events)
        serve    = self.scorer.score_serve(frame_metrics, events)
        footwork = self.scorer.score_footwork(frame_metrics, events)
        posture  = self.scorer.score_posture(frame_metrics, events)
        overall  = self.scorer.compute_overall(smash, serve, footwork, posture)

        # Generate faulty/ideal frame image pairs
        frame_urls = {}
        if frames_storage_path is not None:
            frames_dir = Path(frames_storage_path) / video_id
            frame_urls = self._generate_frame_pairs(video_path, worst_frames, video_id, frames_dir)

        feedback = self.feedback_gen.generate(
            smash, serve, footwork, posture, frame_metrics, events,
            frame_urls=frame_urls,
        )

        metrics_json = json.dumps(self._summarise_metrics(frame_metrics, events))

        logger.info(
            "Analysis complete video_id={}: smash={} serve={} footwork={} posture={} overall={}",
            video_id, smash, serve, footwork, posture, overall,
        )

        return AnalysisPipelineResult(
            video_id=video_id, user_id=user_id,
            smash_score=smash, serve_score=serve,
            footwork_score=footwork, posture_score=posture,
            overall_score=overall, feedback_items=feedback,
            metrics_json=metrics_json,
            frame_count=frame_count, detected_frames=detected_count,
        )

    @staticmethod
    def _update_worst(worst, metrics, ts):
        knee = metrics.get("right_knee_angle") or metrics.get("left_knee_angle")
        if knee is not None and knee > worst["knee_bend"][1]:
            worst["knee_bend"] = [ts, knee]
        elbow = metrics.get("right_elbow_angle")
        if elbow is not None and elbow < worst["elbow_extension"][1]:
            worst["elbow_extension"] = [ts, elbow]
        lean = metrics.get("trunk_lean_deg")
        if lean is not None and lean > worst["trunk_lean"][1]:
            worst["trunk_lean"] = [ts, lean]
        ratio = metrics.get("ankle_to_hip_ratio")
        if ratio is not None and ratio < worst["stance_width"][1]:
            worst["stance_width"] = [ts, ratio]

    def _generate_frame_pairs(self, video_path, worst_frames, video_id, frames_dir):
        urls = {}
        for issue_type, (timestamp, _) in worst_frames.items():
            if timestamp is None:
                continue
            try:
                faulty_url, ideal_url = self.comparator.save_frame_pair(
                    video_path=video_path,
                    timestamp_sec=timestamp,
                    issue_type=issue_type,
                    video_id=video_id,
                    frames_dir=frames_dir,
                )
                urls[issue_type] = (faulty_url, ideal_url)
            except Exception as exc:
                logger.warning("Frame pair failed for issue={}: {}", issue_type, exc)
        return urls

    def _default_result(self, video_id, user_id, frame_count):
        return AnalysisPipelineResult(
            video_id=video_id, user_id=user_id,
            smash_score=0, serve_score=0, footwork_score=0,
            posture_score=0, overall_score=0,
            feedback_items=[FeedbackItem(
                category="POSTURE", severity="CRITICAL",
                message="No player detected in video",
                detail="Ensure the video shows a single player clearly visible from head to toe.",
            )],
            metrics_json="{}", frame_count=frame_count, detected_frames=0,
        )

    @staticmethod
    def _summarise_metrics(frame_metrics, events):
        def safe_mean(key):
            vals = [m.get(key) for m in frame_metrics if m.get(key) is not None]
            return round(statistics.mean(vals), 2) if vals else None

        return {
            "avg_right_elbow_angle":    safe_mean("right_elbow_angle"),
            "avg_left_elbow_angle":     safe_mean("left_elbow_angle"),
            "avg_right_shoulder_angle": safe_mean("right_shoulder_angle"),
            "avg_trunk_lean_deg":       safe_mean("trunk_lean_deg"),
            "avg_knee_angle":           safe_mean("right_knee_angle"),
            "avg_ankle_hip_ratio":      safe_mean("ankle_to_hip_ratio"),
            "smash_count":              len(events.get("smash_frames", [])),
            "serve_count":              len(events.get("serve_frames", [])),
            "step_count":               events.get("step_count", 0),
            "avg_recovery_frames": (
                round(statistics.mean(events["recovery_times"]), 1)
                if events.get("recovery_times") else None
            ),
        }
