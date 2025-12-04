import requests
import logging

logger = logging.getLogger(__name__)

MCP_URL = "http://localhost:7777"

def call_mcp_tool(tool_name: str, params: dict) -> dict:
    """Call an MCP4IFC tool with given parameters"""
    try:
        # ifc-bonsai-mcp uses standard MCP protocol
        response = requests.post(
            f"{MCP_URL}/tools/call",
            json={
                "name": tool_name,
                "arguments": params
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"MCP call failed: {e}")
        raise

def get_mcp_tools() -> dict:
    """Get available MCP tools manifest"""
    try:
        response = requests.get(f"{MCP_URL}/tools/list", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get MCP tools: {e}")
        raise

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
