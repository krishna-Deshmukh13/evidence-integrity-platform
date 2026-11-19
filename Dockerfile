# Multi-stage Dockerfile: Frontend Vite Build + Python 3.11 Backend Runtime (Offline CPU)

# ==================== Stage 1: Build React Frontend ====================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==================== Stage 2: Python Backend Runtime ====================
FROM python:3.11-slim AS runtime

# Install system dependencies (ffmpeg for video/audio forensics, libgl for OpenCV, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Copy compiled frontend distribution from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure storage directories exist
RUN mkdir -p ./backend/storage/uploads ./backend/storage/artifacts ./backend/storage/keys ./backend/storage/models

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    APP_STORAGE=/app/backend/storage

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/auth/status || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
