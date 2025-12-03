import requests
import logging

logger = logging.getLogger(__name__)

MCP_URL = "http://localhost:7777"

def call_mcp_tool(tool_name: str, params: dict) -> dict:
    """Call an MCP4IFC tool with given parameters"""
    try:
        response = requests.post(
            f"{MCP_URL}/run",
            json={
                "tool": tool_name,
                "params": params
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"MCP call failed: {e}")
        raise

def get_mcp_tools() -> dict:
    """Get available MCP tools manifest"""
    try:
        response = requests.get(f"{MCP_URL}/mcp/tools", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get MCP tools: {e}")
        raise

def execute_tool_calls(tool_calls: list) -> dict:
    """Execute a sequence of MCP tool calls"""
    results = []
    for call in tool_calls:
        tool_name = call.get("tool")
        params = call.get("params", call.get("args", {}))
        
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
    return call_mcp_tool("ifc.write_file", {"path": output_path})
