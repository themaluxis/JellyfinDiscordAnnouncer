# Multi-stage build for Jellynouncer
# Build arguments for metadata
ARG BUILDTIME
ARG VERSION
ARG REVISION

FROM node:20-alpine AS web-builder

# Set working directory for web build
WORKDIR /app/web

# Copy web dependencies and build files
COPY web/package*.json ./
COPY web/tsconfig*.json ./
COPY web/vite.config.ts ./
COPY web/tailwind.config.js ./
COPY web/postcss.config.js ./

# Install dependencies
RUN npm install

# Copy web source
COPY web/src ./src
COPY web/index.html ./

# Build web interface
RUN npm run build

# Python runtime stage
FROM python:3.13-slim AS runtime

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -g 1000 app && \
    useradd -r -u 1000 -g app app

# Set working directory
WORKDIR /app

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .

# Copy built web interface
COPY --from=web-builder /app/web/dist ./web/dist

# Create directories and set permissions
RUN mkdir -p /app/config /app/data /app/logs /app/templates && \
    chown -R app:app /app

# Switch to app user
USER app

# Create health check script
COPY --chown=app:app <<EOF /app/healthcheck.py
#!/usr/bin/env python3
import sys
import httpx
try:
    response = httpx.get("http://localhost:1984/health", timeout=10)
    sys.exit(0 if response.status_code == 200 else 1)
except:
    sys.exit(1)
EOF

RUN chmod +x /app/healthcheck.py

# Expose ports
EXPOSE 1984

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python /app/healthcheck.py

# Add metadata labels (build args must be redeclared in runtime stage)
ARG BUILDTIME
ARG VERSION
ARG REVISION

LABEL org.opencontainers.image.title="Jellynouncer" \
      org.opencontainers.image.description="Intelligent Discord notifications for Jellyfin media server" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${BUILDTIME}" \
      org.opencontainers.image.source="https://github.com/MarkusMcNugen/Jellynouncer" \
      org.opencontainers.image.url="https://github.com/MarkusMcNugen/Jellynouncer" \
      org.opencontainers.image.documentation="https://github.com/MarkusMcNugen/Jellynouncer/blob/main/README.md" \
      org.opencontainers.image.vendor="Mark Newton" \
      org.opencontainers.image.licenses="MIT"

# Default command
CMD ["python", "main.py"]