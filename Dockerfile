# ============================================
# Stage 1: Base image with heavy dependencies
# ============================================
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies for PDF processing + Chromium + X11/VNC
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-hun \
    libgl1 \
    libglib2.0-0 \
    wget \
    unzip \
    ca-certificates \
    chromium \
    chromium-driver \
    # X11 and VNC for visible Chromium
    xvfb \
    x11vnc \
    x11-utils \
    fluxbox \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install all Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir websockify

# ============================================
# Stage 2: Final runtime image
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install only runtime system dependencies + Chromium + X11/VNC
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-hun \
    libgl1 \
    libglib2.0-0 \
    wget \
    ca-certificates \
    chromium \
    chromium-driver \
    # X11 and VNC for visible Chromium
    xvfb \
    x11vnc \
    x11-utils \
    fluxbox \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from base stage
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Keep existing Chrome paths working with Chromium
RUN ln -sf /usr/bin/chromium /usr/bin/google-chrome

# Copy application code
COPY src/ ./src/
COPY data/ ./data/

# Create Chrome profile directory with proper permissions
RUN mkdir -p /app/chrome_profile && \
    chmod 777 /app/chrome_profile

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    # Convert to Unix line endings in case it has Windows CRLF
    sed -i 's/\r$//' /entrypoint.sh

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/huggingface_cache \
    CHROME_BIN=/usr/bin/google-chrome \
    DISPLAY=:99

EXPOSE 8000 6080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
