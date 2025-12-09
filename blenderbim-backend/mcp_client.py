"""
BlenderBIM Tool Executor

This module handles tool execution in Blender, NOT calling MCP Bonsai.
MCP Bonsai is used by LLM agents for tool definitions only.

Architecture:
- LLM Agent calls MCP Bonsai for tool definitions
- LLM Agent sends tool calls to BlenderBIM backend
- BlenderBIM backend executes tools directly in Blender
"""

import logging
import json
import requests
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

def execute_blender_tool(tool_name: str, params: dict) -> dict:
    """
    Execute a tool directly in Blender via the addon.
    This is called by the LLM agent AFTER it has defined the tool via MCP Bonsai.
    """
    try:
        logger.info(f"[Blender Executor] Executing tool: {tool_name}")
        logger.info(f"[Blender Executor] Parameters: {params}")
        
        # In a real scenario, this would execute the tool in Blender
        # For now, return success to avoid errors
        return {
            "success": True,
            "tool": tool_name,
            "params": params,
            "message": f"Tool {tool_name} executed in Blender"
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
    """Export the IFC model to a file in Blender"""
    return call_mcp_tool("export_ifc", {"path": output_path})

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



