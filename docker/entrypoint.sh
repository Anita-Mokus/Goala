#!/bin/bash
set -e

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
DISPLAY=:99 fluxbox &
sleep 1

# Start x11vnc server (allows you to view the display via VNC)
# -nopw: no password
# -forever: keep running after client disconnects
# -shared: allow multiple clients
# -noxdamage: better performance
# -rfbport 5900: use standard VNC port
# -listen 0.0.0.0: listen on all interfaces (allows localhost connections)
echo "Starting VNC server on port 5900..."
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw -noxdamage -listen 0.0.0.0 &
VNC_PID=$!

echo "✓ Virtual display ready!"
echo "✓ You can connect to VNC at localhost:5900 to see Chrome running"

# Execute the main command (uvicorn)
exec "$@"
