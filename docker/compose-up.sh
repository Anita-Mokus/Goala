#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

ENABLE_GPU="${ENABLE_GPU:-}"
if [ -f "$ENV_FILE" ]; then
  ENV_GPU="$(grep -E '^ENABLE_GPU=' "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- || true)"
  if [ -n "$ENV_GPU" ]; then
    ENABLE_GPU="$ENV_GPU"
  fi
fi

if [ "$ENABLE_GPU" = "true" ] || [ "$ENABLE_GPU" = "1" ]; then
  echo "Starting with GPU override (ENABLE_GPU=$ENABLE_GPU)"
  exec docker compose -f "$ROOT_DIR/docker-compose.yml" -f "$ROOT_DIR/docker-compose.gpu.yml" up -d "$@"
fi

echo "Starting in CPU mode (ENABLE_GPU=${ENABLE_GPU:-false})"
exec docker compose -f "$ROOT_DIR/docker-compose.yml" up -d "$@"
