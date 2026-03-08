"""FastAPI health-check and status endpoint for the AI service."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import platform, sys

app = FastAPI(title="AI Badminton Analysis Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "UP",
        "service": "ai-analysis-service",
        "python": sys.version,
        "platform": platform.system(),
    }


@app.get("/")
def root():
    return {"message": "AI Badminton Coach – Analysis Service"}
