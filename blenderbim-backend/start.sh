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
export PYTHONPATH="/opt/app_runtime/ifc-bonsai-mcp/src:/opt/app_runtime/ifc-bonsai-mcp:${PYTHONPATH}"
echo "PYTHONPATH=$PYTHONPATH" > /tmp/mcp_server.log

# Diagnostics: show which python binaries exist and their versions
echo "--- python binaries ---" >> /tmp/mcp_server.log
which python3 >> /tmp/mcp_server.log 2>&1 || true
which python3.11 >> /tmp/mcp_server.log 2>&1 || true
python3 --version >> /tmp/mcp_server.log 2>&1 || true
python3.11 --version >> /tmp/mcp_server.log 2>&1 || true

# Diagnostics: list the MCP repo contents and pyproject to verify package layout
echo "--- list /opt/app_runtime/ifc-bonsai-mcp ---" >> /tmp/mcp_server.log
ls -la /opt/app_runtime/ifc-bonsai-mcp >> /tmp/mcp_server.log 2>&1 || true
ls -la /opt/app_runtime/ifc-bonsai-mcp/src >> /tmp/mcp_server.log 2>&1 || true
echo "--- cat pyproject.toml ---" >> /tmp/mcp_server.log
cat /opt/app_runtime/ifc-bonsai-mcp/pyproject.toml >> /tmp/mcp_server.log 2>&1 || true
echo "--- sys.path ---" >> /tmp/mcp_server.log
python3.11 -c "import sys; print('\n'.join(sys.path))" >> /tmp/mcp_server.log 2>&1
echo "--- find_spec(blender_mcp) ---" >> /tmp/mcp_server.log
python3.11 - <<'PY' >> /tmp/mcp_server.log 2>&1
import importlib.util
print('blender_mcp:', importlib.util.find_spec('blender_mcp'))
print('ifc_bonsai_mcp:', importlib.util.find_spec('ifc_bonsai_mcp'))
PY

echo "Attempting to start MCP server (module: blender_mcp)..." >> /tmp/mcp_server.log
python3.11 -m blender_mcp.server --port $MCP_PORT >> /tmp/mcp_server.log 2>&1 &
MCP_PID=$!
sleep 3

# If module start failed, dump logs for debugging
if ! ps -p $MCP_PID > /dev/null; then
    echo "MCP server failed to start. Check logs:"
    cat /tmp/mcp_server.log
    # Try running server directly from source as a fallback
    # Fallback: try running the server script from the package 'src' dir
    if [ -f "/opt/app_runtime/ifc-bonsai-mcp/src/blender_mcp/server.py" ]; then
        echo "Attempting fallback: running /opt/app_runtime/ifc-bonsai-mcp/src/blender_mcp/server.py" >> /tmp/mcp_server.log
        python3.11 /opt/app_runtime/ifc-bonsai-mcp/src/blender_mcp/server.py --port $MCP_PORT >> /tmp/mcp_server.log 2>&1 &
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

# Print key diagnostics to stdout so Railway logs show them immediately
echo "----- MCP DIAGNOSTICS (BEGIN) -----"
echo "PYTHONPATH: $PYTHONPATH"
echo "--- /opt/app_runtime/ifc-bonsai-mcp (top-level) ---"
ls -la /opt/app_runtime/ifc-bonsai-mcp || true
echo "--- /opt/app_runtime/ifc-bonsai-mcp/src ---"
ls -la /opt/app_runtime/ifc-bonsai-mcp/src || true
echo "--- importlib find_spec for blender_mcp ---"
python3.11 - <<'PY' || true
import importlib.util
print(importlib.util.find_spec('blender_mcp'))
try:
    import blender_mcp
    print('blender_mcp.__file__ =', getattr(blender_mcp, '__file__', None))
except Exception as e:
    print('blender_mcp import error:', e)
PY
echo "----- MCP DIAGNOSTICS (END) -----"

# Start FastAPI
echo "Starting FastAPI on port $PORT..."
cd /app
exec python3.11 -m uvicorn main:app --host 0.0.0.0 --port $PORT
