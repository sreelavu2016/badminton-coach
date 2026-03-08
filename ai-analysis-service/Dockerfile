# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /install

# Install build dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install/pkgs --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

# System libraries required by OpenCV and MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install/pkgs /usr/local

COPY . .

# Storage mount point
RUN mkdir -p /app/storage/videos

EXPOSE 8000

CMD ["python", "-m", "main"]
