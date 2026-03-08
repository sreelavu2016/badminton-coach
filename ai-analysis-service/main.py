"""
Entry point: starts Kafka consumer in main thread + FastAPI health server in background thread.
"""
import threading
import uvicorn
from loguru import logger

from src.api.health import app
from src.kafka.consumer import run_consumer
from src.config import settings

import logging
logging.basicConfig(level=settings.log_level)


def start_api():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=settings.log_level.lower())


if __name__ == "__main__":
    logger.info("Starting AI Badminton Analysis Service")

    # FastAPI health server runs in a daemon thread
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    logger.info("Health API started on http://0.0.0.0:8000")

    # Kafka consumer blocks the main thread
    run_consumer()
