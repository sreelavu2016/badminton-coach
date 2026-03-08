"""
Rule-based feedback generator.

Given scores and aggregated metrics, produces a list of specific feedback items
structured as { category, severity, message, detail }.
"""
import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeedbackItem:
    category: str     # SMASH | SERVE | FOOTWORK | POSTURE | BALANCE | RECOVERY
    severity: str     # INFO | WARNING | CRITICAL
    message: str
    detail: str = ""


class FeedbackGenerator:

    def generate(
        self,
        smash_score: int,
        serve_score: int,
        footwork_score: int,
        posture_score: int,
        frame_metrics: list[dict],
        events: dict,
    ) -> list[FeedbackItem]:
        items: list[FeedbackItem] = []

        # --- Smash feedback ---
        items.extend(self._smash_feedback(smash_score, frame_metrics, events))

        # --- Serve feedback ---
        items.extend(self._serve_feedback(serve_score, frame_metrics, events))

        # --- Footwork feedback ---
        items.extend(self._footwork_feedback(footwork_score, events))

        # --- Posture feedback ---
        items.extend(self._posture_feedback(posture_score, frame_metrics))

        # Sort: CRITICAL first, then WARNING, then INFO
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        items.sort(key=lambda x: severity_order.get(x.severity, 3))

        return items

    # ----------------------------------------------------------------- SMASH
    def _smash_feedback(self, score: int, frame_metrics, events) -> list[FeedbackItem]:
        items = []
        smash_frames = events.get("smash_frames", [])

        elbow_vals = [frame_metrics[i].get("right_elbow_angle")
                      for i in smash_frames if i < len(frame_metrics)]
        mean_elbow = self._mean(elbow_vals)

        if mean_elbow is not None and mean_elbow < 110:
            items.append(FeedbackItem(
                category="SMASH",
                severity="CRITICAL",
                message="Raise your elbow higher before the smash",
                detail=f"Average elbow angle at impact: {mean_elbow:.1f}° (target ≥ 140°). "
                       "A low elbow limits power and accuracy.",
            ))
        elif mean_elbow is not None and mean_elbow < 130:
            items.append(FeedbackItem(
                category="SMASH",
                severity="WARNING",
                message="Improve elbow position during smash",
                detail=f"Elbow angle {mean_elbow:.1f}° – try to reach 145°+ for full extension.",
            ))

        wrist_vals = [frame_metrics[i].get("right_wrist_above_shoulder")
                      for i in smash_frames if i < len(frame_metrics)]
        mean_wrist = self._mean(wrist_vals)
        if mean_wrist is not None and mean_wrist < 0.06:
            items.append(FeedbackItem(
                category="SMASH",
                severity="WARNING",
                message="Increase wrist snap at contact",
                detail="Wrist velocity appears low. Snap the wrist downward at the point of contact "
                       "to generate more shuttle speed.",
            ))

        if not smash_frames:
            items.append(FeedbackItem(
                category="SMASH",
                severity="INFO",
                message="No clear smash motion detected in this clip",
                detail="Upload a clip with at least one clear overhead smash for detailed feedback.",
            ))
        elif score >= 80:
            items.append(FeedbackItem(
                category="SMASH",
                severity="INFO",
                message="Smash technique looks solid",
                detail=f"Score {score}/100. Keep maintaining full arm extension.",
            ))

        return items

    # ------------------------------------------------------------------ SERVE
    def _serve_feedback(self, score: int, frame_metrics, events) -> list[FeedbackItem]:
        items = []
        serve_frames = events.get("serve_frames", [])

        trunk_vals = [frame_metrics[i].get("trunk_lean_deg")
                      for i in serve_frames if i < len(frame_metrics)]
        mean_lean = self._mean(trunk_vals)

        if mean_lean is not None and mean_lean > 20:
            items.append(FeedbackItem(
                category="SERVE",
                severity="WARNING",
                message="Keep your body more upright during the serve",
                detail=f"Detected trunk lean of {mean_lean:.1f}° – reduce to < 10° for better control.",
            ))

        wrist_vals = [frame_metrics[i].get("right_wrist_above_shoulder")
                      for i in serve_frames if i < len(frame_metrics)]
        mean_wrist = self._mean(wrist_vals)
        if mean_wrist is not None and mean_wrist < 0.04:
            items.append(FeedbackItem(
                category="SERVE",
                severity="INFO",
                message="Toss the shuttle higher before contact",
                detail="A higher contact point gives you more control over serve direction.",
            ))

        return items

    # -------------------------------------------------------------- FOOTWORK
    def _footwork_feedback(self, score: int, events: dict) -> list[FeedbackItem]:
        items = []
        recovery_times = events.get("recovery_times", [])
        step_count = events.get("step_count", 0)

        if recovery_times:
            mean_rec = statistics.mean(recovery_times)
            if mean_rec > 5:
                items.append(FeedbackItem(
                    category="RECOVERY",
                    severity="CRITICAL",
                    message="Recover to centre court faster after each shot",
                    detail=f"Average recovery: {mean_rec:.0f} frames. Aim to return within 3 frames "
                           "(≈ 0.6 s at 5 fps sample rate).",
                ))
            elif mean_rec > 3:
                items.append(FeedbackItem(
                    category="RECOVERY",
                    severity="WARNING",
                    message="Improve centre-court recovery speed",
                    detail="Try split-step or push-off technique to accelerate return.",
                ))

        if step_count < 10:
            items.append(FeedbackItem(
                category="FOOTWORK",
                severity="WARNING",
                message="Increase movement efficiency on court",
                detail="Low step count detected. Use small adjustment steps to stay balanced.",
            ))
        elif score >= 75:
            items.append(FeedbackItem(
                category="FOOTWORK",
                severity="INFO",
                message="Good footwork movement detected",
                detail=f"Score {score}/100. Continue working on explosive first step.",
            ))

        return items

    # -------------------------------------------------------------- POSTURE
    def _posture_feedback(self, score: int, frame_metrics: list[dict]) -> list[FeedbackItem]:
        items = []

        knee_vals = [m.get("left_knee_angle") or m.get("right_knee_angle") for m in frame_metrics]
        mean_knee = self._mean(knee_vals)

        if mean_knee is not None and mean_knee > 165:
            items.append(FeedbackItem(
                category="POSTURE",
                severity="WARNING",
                message="Bend your knees more to lower your centre of gravity",
                detail=f"Average knee angle: {mean_knee:.1f}° – aim for 130–150° for athletic stance.",
            ))

        trunk_vals = [m.get("trunk_lean_deg") for m in frame_metrics]
        mean_lean = self._mean(trunk_vals)
        if mean_lean is not None and mean_lean > 30:
            items.append(FeedbackItem(
                category="POSTURE",
                severity="WARNING",
                message="Maintain a more neutral spine angle",
                detail=f"Trunk lean averaging {mean_lean:.1f}°. Excessive lean reduces reaction time.",
            ))

        ratio_vals = [m.get("ankle_to_hip_ratio") for m in frame_metrics]
        mean_ratio = self._mean(ratio_vals)
        if mean_ratio is not None and mean_ratio < 1.1:
            items.append(FeedbackItem(
                category="BALANCE",
                severity="WARNING",
                message="Widen your stance for better balance",
                detail="Feet appear close together. A wider base improves lateral stability.",
            ))

        if score >= 80:
            items.append(FeedbackItem(
                category="POSTURE",
                severity="INFO",
                message="Overall posture is well maintained",
                detail=f"Score {score}/100. Focus on consistency across all rallies.",
            ))

        return items

    @staticmethod
    def _mean(vals: list) -> Optional[float]:
        clean = [v for v in vals if v is not None]
        return statistics.mean(clean) if clean else None
