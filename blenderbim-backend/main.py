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

class IFCGenerateRequest(BaseModel):
    python_code: str
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
    Generate IFC file using BlenderBIM by executing Python code
    """
    logger.info(f"Generating IFC for project: {request.project_name}")
    logger.info(f"Python code length: {len(request.python_code)} chars")
    
    output_path = tempfile.mktemp(suffix='.ifc')
    
    # Indent user code for function body
    indented_code = '\n'.join('    ' + line if line.strip() else '' for line in request.python_code.split('\n'))
    
    # Create a wrapper function with proper error handling
    combined_code = f"""
import sys
import traceback

def __execute_user_code__():
    '''Wrapper function to isolate user code execution'''
{indented_code}

# Execute user code with error handling
print("=" * 80)
print("Starting BlenderBIM script execution...")
print("=" * 80)

try:
    __execute_user_code__()
    print("=" * 80)
    print("User code executed successfully!")
    print("=" * 80)
except Exception as e:
    print("=" * 80)
    print(f"ERROR in user code: {{type(e).__name__}}: {{str(e)}}")
    print("=" * 80)
    print("Full traceback:")
    traceback.print_exc()
    print("=" * 80)
    sys.exit(1)

# Export the IFC file
try:
    print("=" * 80)
    print("Starting IFC export...")
    print("=" * 80)
    
    from blenderbim.bim.ifc import IfcStore
    import os
    
    print(f"Exporting IFC to: {output_path}")
    
    # Try both methods to get IFC file
    ifc_file = IfcStore.file if hasattr(IfcStore, 'file') and IfcStore.file else IfcStore.get_file()
    
    if not ifc_file:
        print("ERROR: No IFC project found in IfcStore")
        print(f"IfcStore.file = {{IfcStore.file if hasattr(IfcStore, 'file') else 'not set'}}")
        print(f"IfcStore.get_file() = {{IfcStore.get_file()}}")
        sys.exit(1)
    
    print(f"IFC file found: {{ifc_file}}")
    print(f"Writing to: {output_path}")
    
    ifc_file.write("{output_path}")
    print(f"✓ IFC file write command completed")
    
    if os.path.exists("{output_path}"):
        file_size = os.path.getsize("{output_path}")
        print(f"✓ File verified: {{file_size}} bytes")
        print("=" * 80)
        print("SUCCESS: IFC file generated successfully!")
        print("=" * 80)
    else:
        print("ERROR: Output file was not created by write() command")
        sys.exit(1)
        
except Exception as e:
    print("=" * 80)
    print(f"ERROR during IFC export: {{type(e).__name__}}: {{str(e)}}")
    print("=" * 80)
    print("Full traceback:")
    traceback.print_exc()
    print("=" * 80)
    sys.exit(1)
"""
    
    # Create temporary file with combined code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as code_file:
        code_path = code_file.name
        code_file.write(combined_code)
    
    try:
        # Run Blender in background mode with combined script
        logger.info(f"Running Blender with code: {code_path}, output: {output_path}")
        
        process = subprocess.run(
            [
                "blender",
                "--background",
                "--python", code_path
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Log all output for debugging
        logger.info("=" * 80)
        logger.info("BLENDER STDOUT:")
        logger.info(process.stdout)
        logger.info("=" * 80)
        
        if process.stderr:
            logger.info("BLENDER STDERR:")
            logger.info(process.stderr)
            logger.info("=" * 80)
        
        if process.returncode != 0:
            logger.error(f"Blender process exited with code: {process.returncode}")
            raise HTTPException(
                status_code=500,
                detail=f"Blender generation failed (exit code {process.returncode}): {process.stderr or process.stdout}"
            )
        
        # Check if output file was created
        if not os.path.exists(output_path):
            error_msg = f"IFC file was not generated at {output_path}. "
            error_msg += f"Blender output (last 2000 chars): {process.stdout[-2000:] if len(process.stdout) > 2000 else process.stdout}"
            if process.stderr:
                error_msg += f"\nBlender stderr: {process.stderr[-1000:]}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=500,
                detail=error_msg
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
        # Cleanup code file
        try:
            os.unlink(code_path)
        except:
            pass




