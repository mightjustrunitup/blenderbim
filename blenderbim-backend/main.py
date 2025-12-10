import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

from mcp_client import call_mcp_tool, get_mcp_tools, execute_tool_calls, export_ifc

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="BlenderBIM Worker", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Legacy request model (for backward compatibility)
class GenerateRequest(BaseModel):
    python_code: str
    project_name: str = "Generated Model"

# New MCP-based request model
class ToolCall(BaseModel):
    tool: str
    params: dict = {}

class MCPGenerateRequest(BaseModel):
    tool_calls: List[ToolCall]
    project_name: str = "Generated Model"

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"service": "BlenderBIM MCP Worker", "version": "4.0.0", "status": "running"}

@app.get("/tools")
async def get_tools_simple():
    """Simple /tools endpoint to view all available MCP4IFC tools"""
    try:
        tools = get_mcp_tools()
        # Format for easy reading
        tool_list = []
        for tool in tools.get("tools", tools if isinstance(tools, list) else []):
            tool_list.append({
                "name": tool.get("name"),
                "description": tool.get("description"),
                "parameters": tool.get("inputSchema", tool.get("input_schema", {}))
            })
        return {"tools": tool_list, "count": len(tool_list)}
    except Exception as e:
        return {"error": str(e), "message": "MCP server may not be running"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        result = subprocess.run(["blender", "--version"], capture_output=True, text=True, timeout=5)
        
        # Also check MCP server
        mcp_status = "unknown"
        try:
            tools = get_mcp_tools()
            mcp_status = "healthy"
        except:
            mcp_status = "unavailable"
        
        return {
            "status": "healthy" if result.returncode == 0 else "degraded",
            "blender": result.stdout.split('\n')[0] if result.returncode == 0 else "N/A",
            "mcp_server": mcp_status
        }
    except:
        return {"status": "unhealthy"}

@app.get("/mcp/tools")
async def get_tools():
    """Get available MCP4IFC tools manifest - complete schema for LLM"""
    try:
        tools = get_mcp_tools()
        return tools
    except Exception as e:
        logger.error(f"Failed to get MCP tools: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": "MCP server unavailable", "details": str(e)}
        )

@app.get("/mcp/tools-for-llm")
async def get_tools_for_llm():
    """Get tools formatted for LLM function calling - ready to paste into prompt"""
    try:
        tools = get_mcp_tools()
        # Format for OpenAI/Lovable AI function calling format
        llm_tools = []
        for tool in tools.get("tools", tools if isinstance(tools, list) else []):
            llm_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": tool.get("inputSchema", tool.get("input_schema", {}))
                }
            })
        return {"tools": llm_tools, "count": len(llm_tools)}
    except Exception as e:
        logger.error(f"Failed to format MCP tools for LLM: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": "MCP server unavailable", "details": str(e)}
        )

@app.post("/mcp/execute")
async def execute_mcp_tools(request: MCPGenerateRequest, background_tasks: BackgroundTasks):
    """
    Execute tool calls that were defined via MCP Bonsai and generate IFC file.
    
    Flow:
    1. LLM agent retrieves tool definitions from MCP Bonsai (/mcp/tools)
    2. LLM agent generates tool calls based on user request
    3. LLM agent sends tool calls to this endpoint
    4. BlenderBIM backend executes tools in Blender
    5. IFC file is generated, exported, and uploaded to Supabase Storage
    6. Frontend retrieves IFC file and displays in 3D viewer
    """
    
    import tempfile
    from pathlib import Path
    
    # Create temporary directory for IFC file
    temp_dir = tempfile.mkdtemp()
    ifc_filename = f"{request.project_name.replace(' ', '_')}.ifc"
    ifc_path = Path(temp_dir) / ifc_filename
    
    try:
        logger.info(f"[MCP Worker] Starting tool execution: {request.project_name}")
        logger.info(f"[MCP Worker] Tool calls to execute: {len(request.tool_calls)}")
        logger.info(f"[MCP Worker] IFC output path: {ifc_path}")
        
        # Execute all tool calls
        results = []
        for i, tool_call in enumerate(request.tool_calls, 1):
            logger.info(f"[MCP Worker] Executing tool {i}/{len(request.tool_calls)}: {tool_call.tool}")
            logger.info(f"[MCP Worker] Parameters: {tool_call.params}")
            
            try:
                result = call_mcp_tool(tool_call.tool, tool_call.params)
                logger.info(f"[MCP Worker] Tool {tool_call.tool} result: {result}")
                results.append({
                    "tool": tool_call.tool,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                logger.error(f"[MCP Worker] Tool {tool_call.tool} failed: {e}")
                results.append({
                    "tool": tool_call.tool,
                    "success": False,
                    "error": str(e)
                })
        
        # Export IFC file
        logger.info(f"[MCP Worker] Exporting IFC file to: {ifc_path}")
        try:
            export_result = export_ifc(str(ifc_path))
            logger.info(f"[MCP Worker] Export result: {export_result}")
        except Exception as e:
            logger.error(f"[MCP Worker] Export failed: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"IFC export failed: {str(e)}"
                }
            )
        
        # Check if IFC file was created
        if not ifc_path.exists():
            logger.error(f"[MCP Worker] IFC file not created at {ifc_path}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "IFC file was not created after tool execution"
                }
            )
        
        # Read the IFC file content
        try:
            with open(ifc_path, 'rb') as f:
                ifc_content = f.read()
            file_size = len(ifc_content)
            logger.info(f"[MCP Worker] IFC file size: {file_size} bytes")
        except Exception as e:
            logger.error(f"[MCP Worker] Failed to read IFC file: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Failed to read IFC file: {str(e)}"
                }
            )
        
        # Return the IFC file with metadata
        logger.info(f"[MCP Worker] Successfully generated IFC file")
        background_tasks.add_task(cleanup_temp_dir, Path(temp_dir))
        
        return FileResponse(
            path=str(ifc_path),
            media_type="application/x-ifc",
            filename=ifc_filename,
            headers={
                "X-File-Size": str(file_size),
                "X-Project-Name": request.project_name,
                "X-Tools-Executed": str(len(request.tool_calls))
            }
        )
        
    except Exception as e:
        logger.exception(f"[MCP Worker] Unexpected error: {str(e)}")
        cleanup_temp_dir(Path(temp_dir))
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.get("/dump-signatures")
def get_signatures():
    with open("/app/api_signatures.json") as f:
        return json.load(f)


def wrap_code_with_safety(user_code: str, output_path: str) -> str:
    wrapper = f'''
import sys
import traceback
import numpy as np
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
from blenderbim.bim.ifc import IfcStore

try:
{chr(10).join("    " + line if line.strip() else "" for line in user_code.split(chr(10)))}

    if 'ifc' not in locals():
        raise RuntimeError("Error: Variable 'ifc' not found.")

    IfcStore.file = ifc

    products = ifc.by_type("IfcProduct")
    if len(products) == 0:
        raise RuntimeError("No IFC products created.")

    print(f"✓ Success: Created {{len(products)}} IFC products")

except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

try:
    if IfcStore.file:
        IfcStore.file.write("{output_path}")
        print(f"✓ IFC exported to: {output_path}")
    else:
        print("ERROR: IfcStore.file is empty", file=sys.stderr)
        sys.exit(1)
except Exception as export_error:
    print(f"ERROR during export: {{type(export_error).__name__}}: {{str(export_error)}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
'''
    return wrapper


def cleanup_temp_dir(temp_dir: Path):
    try:
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug(f"[Worker] Cleaned temp: {temp_dir}")
    except Exception as e:
        logger.error(f"[Worker] Cleanup failed: {e}")


@app.post("/generate-ifc")
async def generate_ifc(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Legacy endpoint - generates IFC from Python code"""

    temp_dir = Path(tempfile.mkdtemp())
    script_path = temp_dir / "generate.py"
    ifc_path = temp_dir / f"{request.project_name.replace(' ', '_')}.ifc"

    try:
        logger.info(f"[Worker] Starting IFC generation: {request.project_name}")

        wrapped = wrap_code_with_safety(request.python_code, str(ifc_path))

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(wrapped)

        logger.info(f"[Worker] Executing Blender script: {script_path}")

        result = subprocess.run(
            [
                "blender",
                "--background",
                "--python", str(script_path),
                "--addons", "blenderbim"
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(temp_dir)
        )

        if result.stdout:
            logger.info(f"[Blender] stdout:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"[Blender] stderr:\n{result.stderr}")

        # Check for Python errors in stderr even if Blender exits with code 0
        python_error_indicators = [
            "ERROR:", "TypeError", "NameError", "AttributeError", 
            "ValueError", "KeyError", "IndexError", "RuntimeError",
            "SyntaxError", "ImportError", "ModuleNotFoundError"
        ]
        
        has_python_error = any(indicator in result.stderr for indicator in python_error_indicators)
        
        if result.returncode != 0 or has_python_error:
            # Return plain text error for AI retry loop
            error_msg = f"Blender execution failed\n\nReturn code: {result.returncode}\n\n"
            error_msg += f"STDERR:\n{result.stderr}\n\n"
            error_msg += f"STDOUT:\n{result.stdout}"
            
            cleanup_temp_dir(temp_dir)
            return Response(
                content=error_msg,
                status_code=500,
                media_type="text/plain"
            )

        if not ifc_path.exists():
            cleanup_temp_dir(temp_dir)
            return Response(
                content="IFC file not created after execution",
                status_code=500,
                media_type="text/plain"
            )

        file_size = ifc_path.stat().st_size

        background_tasks.add_task(cleanup_temp_dir, temp_dir)

        return FileResponse(
            path=str(ifc_path),
            media_type="application/x-step",
            filename=f"{request.project_name}.ifc",
            headers={"X-File-Size": str(file_size)}
        )

    except subprocess.TimeoutExpired:
        logger.error("[Worker] Blender execution timeout (120s)")
        cleanup_temp_dir(temp_dir)
        return Response(
            content="Blender execution timeout (120s). Model too complex.",
            status_code=504,
            media_type="text/plain"
        )

    except Exception as e:
        logger.exception(f"[Worker] Unexpected error: {str(e)}")
        cleanup_temp_dir(temp_dir)
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
        return Response(
            content=error_msg,
            status_code=500,
            media_type="text/plain"
        )


@app.get("/api-list")
def get_api_list():
    path = "/app/api_toolset.txt"
    if not os.path.exists(path):
        return {"error": "api_toolset.txt not found"}
    
    with open(path, "r") as f:
        return {"api": f.read().splitlines()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)

