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
export PYTHONPATH="/opt/app_runtime/ifc-bonsai-mcp:${PYTHONPATH}"
echo "PYTHONPATH=$PYTHONPATH" > /tmp/mcp_server.log
echo "--- sys.path ---" >> /tmp/mcp_server.log
python3 -c "import sys; print('\n'.join(sys.path))" >> /tmp/mcp_server.log 2>&1
echo "--- find_spec(ifc_bonsai_mcp) ---" >> /tmp/mcp_server.log
python3 - <<'PY' >> /tmp/mcp_server.log 2>&1
import importlib.util
print(importlib.util.find_spec('ifc_bonsai_mcp'))
PY

echo "Attempting to start MCP server (module)..." >> /tmp/mcp_server.log
python3 -m ifc_bonsai_mcp.server --port $MCP_PORT >> /tmp/mcp_server.log 2>&1 &
MCP_PID=$!
sleep 3

# If module start failed, dump logs for debugging
if ! ps -p $MCP_PID > /dev/null; then
    echo "MCP server failed to start. Check logs:"
    cat /tmp/mcp_server.log
    # Try running server directly from source as a fallback
    if [ -f "/opt/app_runtime/ifc-bonsai-mcp/server.py" ]; then
        echo "Attempting fallback: running /opt/app_runtime/ifc-bonsai-mcp/server.py" >> /tmp/mcp_server.log
        python3 /opt/app_runtime/ifc-bonsai-mcp/server.py --port $MCP_PORT >> /tmp/mcp_server.log 2>&1 &
        MCP_PID=$!
        sleep 2
        if ! ps -p $MCP_PID > /dev/null; then
            echo "Fallback also failed. Dumping logs:";
            cat /tmp/mcp_server.log
        else
            echo "Fallback MCP server started with PID $MCP_PID"
        fi
    fi
fi

# Start FastAPI
echo "Starting FastAPI on port $PORT..."
cd /app
exec uvicorn main:app --host 0.0.0.0 --port $PORT
