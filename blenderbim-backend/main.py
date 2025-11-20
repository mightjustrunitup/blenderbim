import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BlenderBIM IFC Generator", version="2.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IFCGenerateRequest(BaseModel):
    python_code: str = Field(..., description="Python code to execute in Blender")
    project_name: str = Field(default="AI Generated BIM Model", description="Name for the IFC project")

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
    stage: Optional[str] = None
    traceback: Optional[str] = None

@app.get("/health")
async def health_check():
    """Health check endpoint with Blender version verification"""
    try:
        result = subprocess.run(
            ["blender", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        blender_available = result.returncode == 0
        blender_version = result.stdout.split('\n')[0] if blender_available else "Not available"
        
        return {
            "status": "healthy" if blender_available else "degraded",
            "service": "BlenderBIM IFC Generator v2.0",
            "blender_version": blender_version,
            "blender_available": blender_available
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "BlenderBIM IFC Generator v2.0",
            "error": str(e)
        }

def validate_python_code(code: str) -> tuple[bool, Optional[str]]:
    """
    Validate Python code for common issues before execution
    Returns: (is_valid, error_message)
    """
    # Check for dangerous operations
    dangerous_patterns = [
        "os.system",
        "subprocess.run",
        "eval(",
        "exec(",
        "__import__",
        "open(",
    ]
    
    for pattern in dangerous_patterns:
        if pattern in code:
            return False, f"Forbidden operation detected: {pattern}"
    
    # Check for balanced braces/brackets
    open_brackets = code.count('[') + code.count('(') + code.count('{')
    close_brackets = code.count(']') + code.count(')') + code.count('}')
    
    if open_brackets != close_brackets:
        return False, "Unmatched brackets detected"
    
    return True, None

def wrap_code_with_safety(user_code: str, project_name: str, output_path: str) -> str:
    """Wrap user code with proper imports and error handling"""
    wrapper = f'''
import sys
import traceback
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
from blenderbim.bim.ifc import IfcStore

try:
    # === BEGIN USER CODE ===
{user_code}
    # === END USER CODE ===
    
    # Store in IfcStore for export
    if 'ifc' in locals():
        IfcStore.file = ifc
        print("✓ IFC file object created successfully")
    else:
        raise RuntimeError("Variable 'ifc' not found. Code must create an IFC file object.")
        
except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# Export IFC file
try:
    if IfcStore.file:
        IfcStore.file.write("{output_path}")
        print(f"✓ IFC file written to: {output_path}")
    else:
        print("ERROR: No IFC file to export", file=sys.stderr)
        sys.exit(1)
except Exception as export_error:
    print(f"ERROR during export: {{type(export_error).__name__}}: {{str(export_error)}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
'''
    return wrapper

@app.post("/generate-ifc")
async def generate_ifc(request: IFCGenerateRequest):
    """
    Generate IFC file from Python code
    
    This endpoint:
    1. Validates the Python code
    2. Wraps it with proper error handling
    3. Executes it in headless Blender
    4. Returns the generated IFC file
    """
    logger.info(f"Received IFC generation request for project: {request.project_name}")
    logger.debug(f"Code length: {len(request.python_code)} characters")
    
    # Step 1: Validate code
    is_valid, validation_error = validate_python_code(request.python_code)
    if not is_valid:
        logger.error(f"Code validation failed: {validation_error}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Code validation failed",
                "details": validation_error,
                "stage": "validation"
            }
        )
    
    # Create temp directories
    temp_dir = Path(tempfile.mkdtemp())
    script_path = temp_dir / "generate_ifc.py"
    ifc_path = temp_dir / f"{request.project_name.replace(' ', '_')}.ifc"
    
    try:
        # Step 2: Wrap code with safety
        wrapped_code = wrap_code_with_safety(request.python_code, request.project_name, str(ifc_path))
        
        # Write wrapped code to temp file
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(wrapped_code)
        
        logger.info(f"Executing Blender with script: {script_path}")
        
        # Step 3: Execute in Blender
        result = subprocess.run(
            [
                "blender",
                "--background",
                "--python", str(script_path),
                "--addons", "blenderbim"
            ],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            cwd=str(temp_dir)
        )
        
        # Log Blender output
        if result.stdout:
            logger.info(f"Blender stdout:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Blender stderr:\n{result.stderr}")
        
        # Step 4: Check execution result
        if result.returncode != 0:
            error_details = {
                "error": "Blender execution failed",
                "stage": "execution",
                "return_code": result.returncode,
                "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
                "stderr": result.stderr[-1000:] if result.stderr else "",
            }
            
            # Parse specific error types
            if "Traceback" in result.stderr:
                error_details["traceback"] = result.stderr.split("Traceback")[-1]
            
            if "ifcopenshell.api.run" in result.stderr:
                error_details["details"] = "BlenderBIM API error. Check parameter names (use 'product=' not 'products=')."
            elif "NameError" in result.stderr:
                error_details["details"] = "Variable not defined. Check that 'ifc' variable is created."
            elif "AttributeError" in result.stderr:
                error_details["details"] = "Invalid attribute or method call."
            
            logger.error(f"Execution failed: {json.dumps(error_details, indent=2)}")
            raise HTTPException(status_code=500, detail=error_details)
        
        # Step 5: Verify IFC file exists
        if not ifc_path.exists():
            logger.error("IFC file was not created")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "IFC file not created",
                    "details": "Blender execution completed but no IFC file was produced",
                    "stage": "file_creation",
                    "stdout": result.stdout[-500:] if result.stdout else "",
                }
            )
        
        file_size = ifc_path.stat().st_size
        logger.info(f"✓ IFC file generated successfully: {ifc_path} ({file_size} bytes)")
        
        # Step 6: Return IFC file
        return FileResponse(
            path=str(ifc_path),
            media_type="application/x-step",
            filename=f"{request.project_name.replace(' ', '_')}.ifc",
            headers={
                "X-File-Size": str(file_size),
                "X-Generation-Time": "success"
            }
        )
        
    except subprocess.TimeoutExpired:
        logger.error("Blender execution timed out")
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Execution timeout",
                "details": "Blender execution exceeded 2 minute timeout. Try simplifying your model.",
                "stage": "timeout"
            }
        )
    
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "details": str(e),
                "stage": "unknown",
                "type": type(e).__name__
            }
        )
    
    finally:
        # Cleanup temp files (keep them for a bit for debugging)
        try:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp directory: {temp_dir}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)





