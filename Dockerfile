# ============================================
# Single-stage build with CUDA 12.8 + Python
# ============================================
# CUDA 12.8 + cuDNN: minimum required for RTX 5060 (Blackwell SM_120).
# Swap back to python:3.11-slim if you have no NVIDIA GPU (and revert
# requirements.txt torch index to whl/cpu).
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

# Install Python 3.11 + all system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-dev python3-pip python3.11-distutils \
    build-essential \
    libpq-dev \
    libpq5 \
    libmagic-dev \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-hun \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Install all Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/ ./data/

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/tmp/huggingface_cache \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]