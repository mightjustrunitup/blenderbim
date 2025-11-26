import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="BlenderBIM Worker", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    python_code: str
    project_name: str = "Generated Model"

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        result = subprocess.run(["blender", "--version"], capture_output=True, text=True, timeout=5)
        return {
            "status": "healthy" if result.returncode == 0 else "degraded",
            "blender": result.stdout.split('\n')[0] if result.returncode == 0 else "N/A"
        }
    except:
        return {"status": "unhealthy"}

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

        if result.returncode != 0:
            return {
                "error": True,
                "details": {
                    "error": "Blender execution failed",
                    "return_code": result.returncode,
                    "stdout": result.stdout[-1000:],
                    "stderr": result.stderr[-1000:]
                }
            }, 500

        if not ifc_path.exists():
            return {"error": True, "details": {"error": "IFC file not created"}}, 500

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
        return {
            "error": True,
            "details": {
                "error": "Blender execution timeout",
                "hint": "Model too complex."
            }
        }, 504

    except Exception as e:
        logger.exception(f"[Worker] Unexpected error: {str(e)}")
        cleanup_temp_dir(temp_dir)
        return {
            "error": True,
            "details": {"error": str(e), "type": type(e).__name__}
        }, 500


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








