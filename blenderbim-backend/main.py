from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import subprocess
import json
import os
import tempfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BlenderBIM IFC Generator")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ToolCall(BaseModel):
    function: str
    params: Dict[str, Any]

class IFCGenerateRequest(BaseModel):
    tool_calls: List[ToolCall]
    project_name: Optional[str] = "AI Generated BIM Model"

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if Blender is available
        result = subprocess.run(
            ["blender", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        blender_version = result.stdout.split('\n')[0] if result.returncode == 0 else "Unknown"
        
        return {
            "status": "healthy",
            "blender_version": blender_version,
            "service": "BlenderBIM IFC Generator"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/generate-ifc")
async def generate_ifc(request: IFCGenerateRequest):
    """
    Generate IFC file using BlenderBIM based on tool calls
    """
    logger.info(f"Generating IFC for project: {request.project_name}")
    logger.info(f"Tool calls: {len(request.tool_calls)}")
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
        input_path = input_file.name
        json.dump({
            "project_name": request.project_name,
            "tool_calls": [call.dict() for call in request.tool_calls]
        }, input_file)
    
    output_path = tempfile.mktemp(suffix='.ifc')
    
    try:
        # Run Blender in background mode with our generator script
        blender_script = "/app/blender_generator.py"
        
        logger.info(f"Running Blender with input: {input_path}, output: {output_path}")
        
        process = subprocess.run(
            [
                "blender",
                "--background",
                "--python", blender_script,
                "--",
                "--input", input_path,
                "--output", output_path
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if process.returncode != 0:
            logger.error(f"Blender process failed: {process.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Blender generation failed: {process.stderr}"
            )
        
        logger.info(f"Blender output: {process.stdout}")
        
        # Check if output file was created
        if not os.path.exists(output_path):
            raise HTTPException(
                status_code=500,
                detail="IFC file was not generated"
            )
        
        file_size = os.path.getsize(output_path)
        logger.info(f"Generated IFC file: {file_size} bytes")
        
        # Return the IFC file
        return FileResponse(
            output_path,
            media_type="application/x-step",
            filename=f"{request.project_name}.ifc",
            headers={
                "Content-Disposition": f'attachment; filename="{request.project_name}.ifc"'
            }
        )
        
    except subprocess.TimeoutExpired:
        logger.error("Blender process timed out")
        raise HTTPException(status_code=504, detail="Generation timed out")
    except Exception as e:
        logger.error(f"Error generating IFC: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup input file
        try:
            os.unlink(input_path)
        except:
            pass
