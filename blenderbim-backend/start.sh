#!/bin/bash
PORT=${PORT:-8080}

# Start virtual display for Blender (headless rendering)
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &
sleep 2

# Blender path
export PATH="/opt/blender:$PATH"
export BLENDER_EXECUTABLE="/opt/blender/blender"

# Enable BlenderBIM addon
echo "Enabling BlenderBIM addon..."
/opt/blender/blender --background --python-expr "
import bpy
bpy.ops.preferences.addon_enable(module='blenderbim')
bpy.ops.wm.save_userpref()
" 2>&1 || echo "BlenderBIM addon ready"

# Start FastAPI server
echo "Starting FastAPI on port $PORT..."
echo "MCP_SERVER_URL: ${MCP_SERVER_URL}"
cd /app
exec python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT
