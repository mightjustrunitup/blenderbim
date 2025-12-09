import requests
import logging
import os
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Get MCP URL from environment with proper Railway deployment support
# Priority order:
# 1. MCP_SERVER_URL (explicit override)
# 2. Railway private URL (internal service discovery)
# 3. Fallback to localhost for local development
def get_mcp_url() -> str:
    """Get the MCP server URL with proper Railway support"""
    # Explicit override takes precedence
    if os.environ.get("MCP_SERVER_URL"):
        return os.environ.get("MCP_SERVER_URL").rstrip('/')
    
    # Railway private URL for internal service communication
    # This is automatically set by Railway for services in the same environment
    if os.environ.get("MCP_BONSAI_PRIVATE_URL"):
        return os.environ.get("MCP_BONSAI_PRIVATE_URL").rstrip('/')
    
    # Railway public URL fallback (if service is exposed publicly)
    if os.environ.get("MCP_BONSAI_URL"):
        return os.environ.get("MCP_BONSAI_URL").rstrip('/')
    
    # Local development default
    return "http://localhost:7777"

MCP_URL = get_mcp_url()
logger.info(f"MCP Server URL configured as: {MCP_URL}")

def call_mcp_tool(tool_name: str, params: dict, max_retries: int = 3, timeout: int = 120) -> dict:
    """Call an MCP4IFC tool with given parameters and automatic retry logic"""
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"MCP call attempt {attempt}/{max_retries}: {tool_name} at {MCP_URL}")
            
            # ifc-bonsai-mcp uses standard MCP protocol
            response = requests.post(
                f"{MCP_URL}/tools/call",
                json={
                    "name": tool_name,
                    "arguments": params
                },
                timeout=timeout
            )
            response.raise_for_status()
            logger.info(f"MCP tool {tool_name} executed successfully")
            return response.json()
            
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"Connection error (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            
        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(f"Timeout error (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.error(f"MCP call failed (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
    
    # All retries exhausted
    error_msg = (
        f"Failed to call MCP tool '{tool_name}' after {max_retries} attempts. "
        f"MCP Server URL: {MCP_URL}. Last error: {last_error}"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)

def get_mcp_tools(max_retries: int = 3) -> dict:
    """Get available MCP tools manifest with retry logic"""
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching MCP tools (attempt {attempt}/{max_retries})...")
            response = requests.get(f"{MCP_URL}/tools/list", timeout=10)
            response.raise_for_status()
            logger.info("Successfully retrieved MCP tools list")
            return response.json()
            
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"Connection error fetching tools (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(f"Failed to get MCP tools (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
    
    # All retries exhausted
    error_msg = (
        f"Failed to get MCP tools after {max_retries} attempts. "
        f"MCP Server URL: {MCP_URL}. Last error: {last_error}"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)

def execute_tool_calls(tool_calls: list) -> dict:
    """Execute a sequence of MCP tool calls"""
    results = []
    for call in tool_calls:
        tool_name = call.get("tool") or call.get("name")
        params = call.get("params") or call.get("arguments") or call.get("args", {})
        
        logger.info(f"Executing MCP tool: {tool_name} with params: {params}")
        
        try:
            result = call_mcp_tool(tool_name, params)
            results.append({
                "tool": tool_name,
                "success": True,
                "result": result
            })
        except Exception as e:
            results.append({
                "tool": tool_name,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results}

def export_ifc(output_path: str) -> dict:
    """Export the current IFC model to a file"""
    return call_mcp_tool("export_ifc", {"path": output_path})

def create_project(name: str = "My Project") -> dict:
    """Create a new IFC project"""
    return call_mcp_tool("create_project", {"name": name})

def add_wall(start: list, end: list, height: float = 3.0, thickness: float = 0.2) -> dict:
    """Add a wall to the IFC model"""
    return call_mcp_tool("add_wall", {
        "start": start,
        "end": end,
        "height": height,
        "thickness": thickness
    })

def add_door(wall_id: str, position: float = 0.5, width: float = 0.9, height: float = 2.1) -> dict:
    """Add a door to a wall"""
    return call_mcp_tool("add_door", {
        "wall_id": wall_id,
        "position": position,
        "width": width,
        "height": height
    })

def add_window(wall_id: str, position: float = 0.5, width: float = 1.2, height: float = 1.5, sill_height: float = 0.9) -> dict:
    """Add a window to a wall"""
    return call_mcp_tool("add_window", {
        "wall_id": wall_id,
        "position": position,
        "width": width,
        "height": height,
        "sill_height": sill_height
    })


