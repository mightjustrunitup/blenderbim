#!/bin/bash
PORT=${PORT:-8080}
MCP_PORT=${MCP_PORT:-7777}

# Start virtual display for Blender
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &
sleep 2

# Start Blender path
export PATH="/opt/app_runtime/blender:$PATH"

# Enable BlenderBIM addon
echo "Enabling BlenderBIM addon..."
/opt/app_runtime/blender/blender --background --python-expr "
import bpy
bpy.ops.preferences.addon_enable(module='blenderbim')
bpy.ops.wm.save_userpref()
" 2>&1 || echo "BlenderBIM enable completed"

# Start MCP server in background
echo "Starting MCP server on port $MCP_PORT..."
cd /opt/app_runtime/ifc-bonsai-mcp
python3 -m ifc_bonsai_mcp.server --port $MCP_PORT &
MCP_PID=$!
sleep 3

# Start FastAPI
echo "Starting FastAPI on port $PORT..."
cd /app
exec uvicorn main:app --host 0.0.0.0 --port $PORT
