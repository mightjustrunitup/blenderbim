#!/bin/bash
PORT=${PORT:-8080}
MCP_PORT=7777

# Start MCP4IFC server in background using Blender's Python
echo "Starting MCP4IFC server on port $MCP_PORT..."
/opt/blender/4.2/python/bin/python3.11 -m mcp4ifc.server --host 0.0.0.0 --port $MCP_PORT &
MCP_PID=$!

# Wait for MCP server to be ready
sleep 3

# Start FastAPI
echo "Starting FastAPI on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
