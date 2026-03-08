# AI Badminton Coach

Production-grade MVP system for badminton technique analysis using computer vision.

---

## Architecture

```
Angular (4200) → Video Service (8081) → Kafka → AI Service (8000) → Feedback Service (8082) → PostgreSQL (5432)
```

---

## Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Docker | 24+ |
| Docker Compose | 2.20+ |
| Java (for local dev) | 21 |
| Maven (for local dev) | 3.9 |
| Python (for local dev) | 3.11 |
| Node.js (for local dev) | 20 |

---

## Quick Start — Docker (Recommended)

```bash
# 1. Clone / navigate to project root
cd ai-badminton-coach

# 2. Start all services
cd docker
docker compose up --build

# 3. Open browser
open http://localhost:4200
```

All services start in correct order with health checks.

---

## Local Development Setup

### Step 1 – Infrastructure (PostgreSQL + Kafka)

```bash
cd docker
docker compose up postgres zookeeper kafka -d
```

### Step 2 – Feedback Service

```bash
cd backend-feedback-service
mvn spring-boot:run
# Runs on http://localhost:8082
```

### Step 3 – Video Service

```bash
cd backend-video-service
mvn spring-boot:run
# Runs on http://localhost:8081
```

### Step 4 – AI Analysis Service

```bash
cd ai-analysis-service

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure env
cp .env.example .env

# Run the service
python main.py
# Health API on http://localhost:8000
# Kafka consumer starts automatically
```

### Step 5 – Angular Frontend

```bash
cd frontend-angular
npm install
npm start
# App on http://localhost:4200
```

---

## Using the Application

### Upload a Video

1. Open http://localhost:4200
2. Click **Upload Video**
3. Drag-and-drop or select an `.mp4` or `.mov` file (max 60 seconds)
4. Click **Analyze Technique**

### View Dashboard

- After upload, you are redirected to the **Dashboard**
- The page polls every 4 seconds until the AI analysis completes
- Analysis takes **20–90 seconds** depending on video length and hardware

### Dashboard Features

| Section | Description |
|---------|-------------|
| Overall Score | Weighted composite score (0–100) |
| Score Cards | Smash / Serve / Footwork / Posture |
| Video Player | Review your uploaded clip |
| Feedback Items | Ranked suggestions (Critical → Warning → Info) |

---

## API Reference

### Video Service (port 8081)

```
POST /api/videos/upload          Upload video (multipart/form-data: file, userId)
GET  /api/videos/{videoId}       Get video metadata
GET  /api/videos/{videoId}/stream Stream video file
GET  /api/videos/health          Health check
```

### Feedback Service (port 8082)

```
POST /api/analysis               Save analysis result (called by AI service)
GET  /api/analysis/{videoId}     Retrieve analysis by video ID
GET  /api/analysis/health        Health check
```

### AI Analysis Service (port 8000)

```
GET  /health                     Health check
GET  /                           Service info
```

---

## Kafka Events

### Topic: `video-uploaded`

**Published by**: Video Service
**Consumed by**: AI Analysis Service

```json
{
  "eventType": "VIDEO_UPLOADED",
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "userId": "user123",
  "videoUrl": "storage/videos/550e8400.mp4",
  "originalFilename": "practice.mp4",
  "fileSizeBytes": 12345678,
  "uploadTime": "2024-01-15T10:30:00"
}
```

---

## Database Schema

```sql
-- Auto-created by Hibernate (ddl-auto: update)

CREATE TABLE videos (
  video_id        VARCHAR(36) PRIMARY KEY,
  user_id         VARCHAR(255) NOT NULL,
  video_url       VARCHAR(500) NOT NULL,
  original_filename VARCHAR(255),
  file_size_bytes BIGINT,
  content_type    VARCHAR(100),
  status          VARCHAR(20),
  upload_time     TIMESTAMP,
  updated_time    TIMESTAMP
);

CREATE TABLE analysis_results (
  analysis_id     VARCHAR(36) PRIMARY KEY,
  video_id        VARCHAR(36) UNIQUE NOT NULL,
  user_id         VARCHAR(255),
  smash_score     INTEGER,
  serve_score     INTEGER,
  footwork_score  INTEGER,
  posture_score   INTEGER,
  overall_score   INTEGER,
  metrics_json    TEXT,
  analysis_status VARCHAR(20),
  analyzed_at     TIMESTAMP,
  created_at      TIMESTAMP
);

CREATE TABLE feedback_items (
  id              BIGSERIAL PRIMARY KEY,
  analysis_id     VARCHAR(36) REFERENCES analysis_results(analysis_id),
  category        VARCHAR(20),
  severity        VARCHAR(10),
  message         VARCHAR(500),
  detail          TEXT
);
```

---

## AI Analysis Logic

### MediaPipe Landmarks Used

| Body Part | Landmark Indices |
|-----------|-----------------|
| Shoulders | 11, 12 |
| Elbows | 13, 14 |
| Wrists | 15, 16 |
| Hips | 23, 24 |
| Knees | 25, 26 |
| Ankles | 27, 28 |

### Scoring Rubric

| Score | Smash Weight | Serve | Footwork | Posture |
|-------|-------------|-------|----------|---------|
| Overall | 35% | 20% | 25% | 20% |

### Smash Score Components

- **Elbow angle at impact** (40%) — target: ≥ 145°
- **Shoulder abduction** (35%) — target: ≥ 155°
- **Wrist height above shoulder** (25%) — target: ≥ 0.12 normalised

### Feedback Categories

| Category | Triggers |
|----------|---------|
| SMASH | Elbow < 110° → CRITICAL; wrist velocity low → WARNING |
| SERVE | Trunk lean > 20° → WARNING |
| FOOTWORK | Recovery > 5 frames → CRITICAL; step count low → WARNING |
| POSTURE | Knee angle > 165° (too straight) → WARNING |
| BALANCE | Ankle/hip ratio < 1.1 (narrow stance) → WARNING |
| RECOVERY | Time to return to centre court |

---

## Configuration

### Video Service (`application.yml`)

```yaml
app:
  video-storage-path: ./storage/videos
  max-video-duration-seconds: 60
  allowed-video-formats:
    - video/mp4
    - video/quicktime
```

### AI Service (`.env`)

```env
FRAME_SAMPLE_RATE=5            # frames per second to sample
MAX_VIDEO_DURATION_SECONDS=60
MIN_POSE_CONFIDENCE=0.5
```

---

## Project Structure

```
ai-badminton-coach/
├── backend-video-service/          Spring Boot (Java 21)
│   ├── src/main/java/com/badminton/video/
│   │   ├── controller/             REST endpoints
│   │   ├── service/                Business logic + Kafka producer
│   │   ├── repository/             JPA repositories
│   │   ├── model/                  JPA entities
│   │   ├── dto/                    Request/Response DTOs
│   │   ├── event/                  Kafka event payloads
│   │   └── config/                 Kafka, Storage, Exception handler
│   └── Dockerfile
│
├── backend-feedback-service/       Spring Boot (Java 21)
│   ├── src/main/java/com/badminton/feedback/
│   │   ├── controller/
│   │   ├── service/
│   │   ├── repository/
│   │   ├── model/
│   │   └── dto/
│   └── Dockerfile
│
├── ai-analysis-service/            Python 3.11
│   ├── src/
│   │   ├── analyzer/               FrameExtractor, PoseDetector, JointCalculator, VideoAnalyzer
│   │   ├── detector/               MovementDetector (smash/serve/footwork)
│   │   ├── scorer/                 TechniqueScorer (4 dimensions)
│   │   ├── feedback/               FeedbackGenerator (rule-based)
│   │   ├── kafka/                  Kafka consumer
│   │   ├── api/                    FastAPI health endpoint
│   │   └── config.py               Pydantic settings
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend-angular/               Angular 17 (standalone components)
│   ├── src/app/
│   │   ├── pages/
│   │   │   ├── upload/             Video upload page
│   │   │   └── dashboard/          Analysis dashboard
│   │   ├── components/
│   │   │   ├── score-card/         Animated score ring
│   │   │   └── feedback-list/      Feedback items with severity
│   │   ├── services/               VideoService (HTTP client)
│   │   └── models/                 TypeScript interfaces
│   ├── nginx.conf
│   └── Dockerfile
│
└── docker/
    ├── docker-compose.yml          Full stack orchestration
    └── init.sql                    PostgreSQL init
```

---

## Troubleshooting

### AI analysis never completes

1. Check AI service logs: `docker logs badminton-ai-service`
2. Ensure MediaPipe downloaded models: first run downloads ~50 MB
3. Verify Kafka connectivity: `docker logs badminton-kafka`

### Video upload fails (413)

Increase Nginx `client_max_body_size` or Spring Boot multipart size.

### No pose detected

- Ensure player is fully visible from head to ankles
- Improve lighting (avoid backlighting)
- Use a stable camera angle (side view recommended)

### PostgreSQL connection refused

```bash
docker compose up postgres -d
# Wait for health check
docker ps | grep postgres
```
