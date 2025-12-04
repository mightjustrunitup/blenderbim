#!/bin/bash
PORT=${PORT:-8080}
MCP_PORT=7777

# Start virtual display for Blender
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &
sleep 2

# Start Blender in background with the MCP addon socket server
echo "Starting Blender with MCP addon..."
blender --background --python-expr "
import bpy
# Enable Bonsai addon
bpy.ops.preferences.addon_enable(module='bonsai')
bpy.ops.wm.save_userpref()
" &
BLENDER_PID=$!

# Start the MCP server from ifc-bonsai-mcp
echo "Starting MCP4IFC server on port $MCP_PORT..."
cd /opt/ifc-bonsai-mcp
python3.11 -m blender_mcp.server --port $MCP_PORT &
MCP_PID=$!

# Wait for MCP server to be ready
sleep 5

# Start FastAPI
echo "Starting FastAPI on port $PORT..."
cd /app
exec uvicorn main:app --host 0.0.0.0 --port $PORT
