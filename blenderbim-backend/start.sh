#!/bin/bash
PORT=${PORT:-8080}

# Start virtual display for Blender (headless rendering)
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &
sleep 2

# Blender path
export PATH="/opt/blender:$PATH"
export BLENDER_EXECUTABLE="/opt/blender/blender"

# Note: BlenderBIM addon will be loaded by the socket server script when needed
# Skipping addon enable at startup to avoid binary compatibility issues with shapely.lib

# Start FastAPI server
echo "Starting FastAPI on port $PORT..."
echo "MCP_SERVER_URL: ${MCP_SERVER_URL}"
cd /app
exec python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT

