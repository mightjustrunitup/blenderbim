import os
import tempfile
import subprocess
import logging
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import re

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="BlenderBIM Worker", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    python_code: str
    project_name: str = "Generated_Model.ifc"

ERROR_PATTERNS = [
    "Traceback",
    "TypeError",
    "NameError",
    "AttributeError",
    "RuntimeError",
    "ModuleNotFoundError",
    "Incorrect function arguments provided",
    "got an unexpected keyword argument"
]

@app.get("/health")
async def health():
    try:
        result = subprocess.run(["blender", "--version"], capture_output=True, text=True, timeout=5)
        return {"status": "healthy", "blender": result.stdout.split("\n")[0]}
    except:
        return {"status": "unhealthy"}

@app.get("/api-list")
def get_api_list():
    path = "/app/api_toolset.txt"
    if not os.path.exists(path):
        return {"error": "api_toolset.txt not found"}
    with open(path) as f:
        return {"api": f.read().splitlines()}

def wrap_code_with_safety(user_code: str, output_path: str) -> str:
    return f"""
import sys, traceback
import ifcopenshell
import ifcopenshell.api
from blenderbim.bim.ifc import IfcStore

try:
{chr(10).join("    "+line for line in user_code.splitlines())}

    if 'ifc' not in locals():
        raise RuntimeError("User code did not create 'ifc' variable")

    IfcStore.file = ifc

    if len(ifc.by_type("IfcProduct")) == 0:
        raise RuntimeError("No IFC products created by user code")

except Exception as e:
    print("PYTHON_ERROR:", type(e).__name__, str(e))
    traceback.print_exc()
    sys.exit(1)

try:
    IfcStore.file.write("{output_path}")
    print("IFC_EXPORTED")
except Exception as e:
    print("EXPORT_ERROR:", type(e).__name__, str(e))
    traceback.print_exc()
    sys.exit(1)
"""

def cleanup(temp_dir: Path):
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug(f"Cleaned: {temp_dir}")
    except:
        pass

@app.post("/generate-ifc")
async def generate_ifc(request: GenerateRequest, background_tasks: BackgroundTasks):

    temp_dir = Path(tempfile.mkdtemp())
    script_path = temp_dir / "generate.py"
    ifc_path = temp_dir / request.project_name.replace(" ", "_")

    # Write wrapped script
    script_path.write_text(wrap_code_with_safety(request.python_code, str(ifc_path)))

    # Run Blender headless
    result = subprocess.run(
        ["blender", "--background", "--python", str(script_path), "--addons", "blenderbim"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(temp_dir)
    )

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    logger.info("STDOUT:\n" + stdout)
    logger.warning("STDERR:\n" + stderr)

    # 🔥 CRITICAL FIX — detect Python errors even if Blender exits 0
    if any(pattern in stderr for pattern in ERROR_PATTERNS):
        return {
            "error": True,
            "stderr": stderr,
            "stdout": stdout,
            "return_code": result.returncode,
            "hint": "Python error detected inside Blender"
        }, 500

    # Blender returned non-zero exit code
    if result.returncode != 0:
        return {
            "error": True,
            "stderr": stderr,
            "stdout": stdout,
            "return_code": result.returncode
        }, 500

    # IFC file missing
    if not ifc_path.exists():
        return {
            "error": True,
            "stderr": stderr,
            "stdout": stdout,
            "hint": "IFC file was not created"
        }, 500

    file_size = ifc_path.stat().st_size

    background_tasks.add_task(cleanup, temp_dir)

    return FileResponse(
        path=str(ifc_path),
        media_type="application/x-step",
        filename=request.project_name,
        headers={"X-File-Size": str(file_size)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))









