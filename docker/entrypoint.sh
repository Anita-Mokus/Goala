#!/bin/bash
set -e

# Remove stale Xvfb lock/socket from previous run (e.g. after docker restart)
# Otherwise "Server is already active for display 99" blocks startup
if [ -f /tmp/.X99-lock ]; then
    echo "Removing stale Xvfb lock file /tmp/.X99-lock..."
    rm -f /tmp/.X99-lock
fi
if [ -S /tmp/.X11-unix/X99 ]; then
    echo "Removing stale Xvfb socket /tmp/.X11-unix/X99..."
    rm -f /tmp/.X11-unix/X99
fi

# Start Xvfb (X Virtual Frame Buffer) - creates a virtual display
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!

# Wait for X server to be ready
echo "Waiting for Xvfb to be ready..."
for i in {1..30}; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "✓ Xvfb is ready on display :99"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Xvfb failed to start after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Start fluxbox window manager
echo "Starting fluxbox window manager..."
DISPLAY=:99 fluxbox >/dev/null 2>&1 &
sleep 1

# Start x11vnc server (VNC backend, only listens locally)
echo "Starting x11vnc..."
x11vnc -quiet -display :99 -forever -shared -rfbport 5900 -nopw -noxdamage -listen 127.0.0.1 >/dev/null 2>&1 &
VNC_PID=$!

# Start websockify to bridge VNC over WebSocket for noVNC
echo "Starting websockify on port 6080..."
websockify 0.0.0.0:6080 localhost:5900 >/dev/null 2>&1 &
WEBSOCKIFY_PID=$!

echo "✓ Virtual display ready!"
echo "✓ noVNC WebSocket available on port 6080"

# Run database migrations (each migration runs only once; tracked in schema_migrations table)
echo "Running database migrations..."
python -m src.utils.run_migrations
MIGRATE_EXIT=$?
if [ "$MIGRATE_EXIT" -eq 0 ]; then
    echo "✓ Migrations step finished successfully"
else
    echo "Warning: Migrations exited with code $MIGRATE_EXIT (see above)"
fi

# Execute the main command (uvicorn)
exec "$@"
