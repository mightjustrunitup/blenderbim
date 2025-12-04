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
python3 -m ifc_bonsai_mcp.server --port $MCP_PORT > /tmp/mcp_server.log 2>&1 &
MCP_PID=$!
sleep 3

# Check if MCP server started
if ! ps -p $MCP_PID > /dev/null; then
    echo "MCP server failed to start. Check logs:"
    cat /tmp/mcp_server.log
fi

# Start FastAPI
echo "Starting FastAPI on port $PORT..."
cd /app
exec uvicorn main:app --host 0.0.0.0 --port $PORT
