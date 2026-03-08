"""
Kafka consumer: listens on the video-uploaded topic and triggers analysis.
"""
import json
import tempfile
from pathlib import Path

import httpx
from kafka import KafkaConsumer
from loguru import logger

from ..analyzer.video_analyzer import VideoAnalyzer
from ..config import settings


def build_feedback_payload(result) -> dict:
    return {
        "videoId": result.video_id,
        "userId": result.user_id,
        "smashScore": result.smash_score,
        "serveScore": result.serve_score,
        "footworkScore": result.footwork_score,
        "postureScore": result.posture_score,
        "overallScore": result.overall_score,
        "metricsJson": result.metrics_json,
        "feedbackItems": [
            {
                "category": fi.category,
                "severity": fi.severity,
                "message": fi.message,
                "detail": fi.detail,
            }
            for fi in result.feedback_items
        ],
    }


def resolve_video_path(video_url: str) -> Path:
    """
    Returns a local Path to the video file.
    For Azure backend: downloads the blob to a temp file and returns that path.
    For local backend: resolves the path relative to VIDEO_STORAGE_PATH.
    """
    if settings.video_storage_backend.lower() == "azure":
        return _download_from_azure(video_url)
    return _resolve_local_path(video_url)


def _resolve_local_path(video_url: str) -> Path:
    path = Path(video_url)
    if path.is_absolute() and path.exists():
        return path
    storage_root = Path(settings.video_storage_path).resolve()
    candidate = storage_root / path.name
    if candidate.exists():
        return candidate
    candidate2 = Path(video_url)
    if candidate2.exists():
        return candidate2
    raise FileNotFoundError(f"Cannot resolve local video path: {video_url}")


def _download_from_azure(blob_url: str) -> Path:
    """Download a blob to a temp file; caller is responsible for cleanup."""
    from azure.storage.blob import BlobServiceClient

    blob_name = blob_url.split("/")[-1]
    logger.info("Downloading blob '{}' from Azure", blob_name)

    service_client = BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    )
    container_client = service_client.get_container_client(
        settings.azure_storage_container_name
    )
    blob_client = container_client.get_blob_client(blob_name)

    suffix = "." + blob_name.rsplit(".", 1)[-1] if "." in blob_name else ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    download_stream = blob_client.download_blob()
    tmp.write(download_stream.readall())
    tmp.flush()
    tmp.close()

    logger.info("Downloaded blob to temp file: {}", tmp.name)
    return Path(tmp.name)


def post_results_to_feedback_service(payload: dict) -> None:
    url = f"{settings.feedback_service_url}/api/analysis"
    with httpx.Client(timeout=30) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
    logger.info("Posted analysis results to feedback service for videoId={}", payload["videoId"])


def run_consumer():
    """
    Blocking Kafka consumer loop.
    Each message triggers a full video analysis pipeline.
    """
    analyzer = VideoAnalyzer(
        sample_fps=settings.frame_sample_rate,
        max_duration_sec=settings.max_video_duration_seconds,
        min_pose_confidence=settings.min_pose_confidence,
    )

    consumer = KafkaConsumer(
        settings.kafka_topic_video_uploaded,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
    )

    logger.info(
        "Kafka consumer started. Listening on topic={} servers={}",
        settings.kafka_topic_video_uploaded,
        settings.kafka_bootstrap_servers,
    )

    for message in consumer:
        event = message.value
        if not event:
            logger.warning("Skipping empty/malformed message at offset={}", message.offset)
            consumer.commit()
            continue
        video_id = event.get("videoId", "unknown")
        video_url = event.get("videoUrl", "")
        user_id = event.get("userId", "anonymous")
        tmp_path = None

        logger.info("Received VIDEO_UPLOADED event: videoId={} url={}", video_id, video_url)

        try:
            video_path = resolve_video_path(video_url)
            # Track temp files created by Azure download for cleanup
            if settings.video_storage_backend.lower() == "azure":
                tmp_path = video_path

            result = analyzer.analyze(video_path, video_id, user_id)
            payload = build_feedback_payload(result)
            post_results_to_feedback_service(payload)
            consumer.commit()
            logger.info("Committed Kafka offset for videoId={}", video_id)

        except FileNotFoundError as e:
            logger.error("Video file not found: {}", e)
            consumer.commit()   # skip unresolvable message
        except httpx.HTTPError as e:
            logger.error("HTTP error posting results for videoId={}: {}", video_id, e)
            # Do NOT commit – will retry on restart
        except Exception as e:
            logger.exception("Unexpected error processing videoId={}: {}", video_id, e)
            consumer.commit()   # skip to avoid poison-pill loop
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
