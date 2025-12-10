"""
BlenderBIM Tool Executor

This module handles tool execution in Blender, NOT calling MCP Bonsai.
MCP Bonsai is used by LLM agents for tool definitions only.

Architecture:
- LLM Agent calls MCP Bonsai for tool definitions
- LLM Agent sends tool calls to BlenderBIM backend
- BlenderBIM backend executes tools directly in Blender via MCP Bonsai
"""

import logging
import json
import requests
import os
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)

def execute_blender_tool(tool_name: str, params: dict) -> dict:
    """
    Execute a tool in Blender by calling MCP Bonsai's execution endpoint.
    MCP Bonsai has a running Blender instance and can execute tools.
    """
    try:
        logger.info(f"[Blender Executor] Executing tool: {tool_name}")
        logger.info(f"[Blender Executor] Parameters: {params}")
        
        mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:7777")
        
        # Call MCP Bonsai to execute the tool
        # MCP Bonsai will execute it in the running Blender instance
        response = requests.post(
            f"{mcp_url}/tools/execute",
            json={
                "name": tool_name,
                "arguments": params
            },
            timeout=120
        )
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"[Blender Executor] MCP execution failed: {response.status_code} - {error_text}")
            return {
                "success": False,
                "tool": tool_name,
                "error": f"MCP execution failed: {response.status_code}"
            }
        
        result = response.json()
        logger.info(f"[Blender Executor] Tool {tool_name} executed successfully")
        return {
            "success": True,
            "tool": tool_name,
            "params": params,
            "result": result
        }
        
    except requests.exceptions.Timeout:
        logger.error(f"[Blender Executor] Timeout executing {tool_name}")
        return {
            "success": False,
            "tool": tool_name,
            "error": "Execution timeout - Blender may be busy"
        }
    except requests.exceptions.ConnectionError:
        logger.error(f"[Blender Executor] Cannot connect to MCP server at {mcp_url}")
        return {
            "success": False,
            "tool": tool_name,
            "error": f"Cannot connect to MCP server - is it running at {mcp_url}?"
        }
    except Exception as e:
        logger.error(f"[Blender Executor] Error executing {tool_name}: {e}")
        return {
            "success": False,
            "tool": tool_name,
            "error": str(e)
        }

def call_mcp_tool(tool_name: str, params: dict) -> dict:
    """
    Execute a tool in Blender.
    This receives tool calls from the LLM agent (after MCP Bonsai definition).
    """
    return execute_blender_tool(tool_name, params)

def execute_tool_calls(tool_calls: list) -> dict:
    """Execute a sequence of tool calls in Blender"""
    results = []
    
    for i, call in enumerate(tool_calls, 1):
        tool_name = call.get("tool") or call.get("name")
        params = call.get("params") or call.get("arguments") or call.get("args", {})
        
        logger.info(f"[Tool Executor] Executing tool {i}: {tool_name}")
        
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
    """
    Export the IFC model to a file by calling MCP Bonsai.
    MCP Bonsai will execute the export in the running Blender instance.
    """
    try:
        logger.info(f"[IFC Exporter] Exporting IFC to: {output_path}")
        
        mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:7777")
        
        # Call MCP Bonsai to execute the export_ifc tool
        response = requests.post(
            f"{mcp_url}/tools/execute",
            json={
                "name": "export_ifc",
                "arguments": {"path": output_path}
            },
            timeout=120
        )
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"[IFC Exporter] Export failed: {response.status_code} - {error_text}")
            return {
                "success": False,
                "error": f"Export failed: {response.status_code}"
            }
        
        result = response.json()
        logger.info(f"[IFC Exporter] IFC exported successfully to {output_path}")
        return {
            "success": True,
            "result": result
        }
        
    except requests.exceptions.Timeout:
        logger.error(f"[IFC Exporter] Timeout during export")
        return {
            "success": False,
            "error": "Export timeout - Blender may be busy"
        }
    except requests.exceptions.ConnectionError:
        logger.error(f"[IFC Exporter] Cannot connect to MCP server")
        return {
            "success": False,
            "error": f"Cannot connect to MCP server at {mcp_url}"
        }
    except Exception as e:
        logger.error(f"[IFC Exporter] Error during export: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def get_mcp_tools() -> dict:
    """
    Get tool definitions from MCP Bonsai for LLM prompting.
    This is READ-ONLY - used by LLM agents to understand available tools.
    """
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:7777")
    
    try:
        logger.info(f"[MCP Client] Fetching tools from MCP Bonsai: {mcp_url}")
        response = requests.get(f"{mcp_url}/tools/list", timeout=10)
        response.raise_for_status()
        
        tools = response.json()
        logger.info(f"[MCP Client] Retrieved tool definitions from MCP Bonsai")
        return tools
        
    except Exception as e:
        logger.error(f"[MCP Client] Failed to get tools from MCP Bonsai: {e}")
        # Return empty tools list on failure
        return {
            "tools": [],
            "error": str(e)
        }

# Backward compatibility functions
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



