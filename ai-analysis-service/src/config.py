"""Central configuration loaded from environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_video_uploaded: str = "video-uploaded"
    kafka_group_id: str = "ai-analysis-group"

    # Downstream services
    feedback_service_url: str = "http://localhost:8082"
    video_service_url: str = "http://localhost:8081"

    # Storage
    video_storage_backend: str = "local"   # "local" or "azure"
    video_storage_path: str = "../backend-video-service/storage/videos"
    azure_storage_connection_string: str = ""
    azure_storage_container_name: str = "videos"

    # Analysis
    frame_sample_rate: int = 5          # frames per second to sample
    max_video_duration_seconds: int = 60
    min_pose_confidence: float = 0.5

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
