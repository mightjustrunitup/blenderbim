# IFC Generator Backend with IfcOpenShell

This Python FastAPI backend uses **IfcOpenShell** - the same core library that powers BlenderBIM - to generate proper IFC files with full BIM properties.

## Features

- ✅ Full IFC4 support using IfcOpenShell
- ✅ Proper BIM properties (Psets, classifications, relationships)
- ✅ Spatial hierarchy (Project → Site → Building → Storey → Elements)
- ✅ Generate walls, doors, windows, columns, beams, slabs
- ✅ Returns valid IFC files that work with all BIM software

## Deployment Options

### 1. Railway (Recommended - Easiest)

1. Push this `python-backend` folder to GitHub
2. Go to [Railway](https://railway.app)
3. Click "New Project" → "Deploy from GitHub"
4. Select your repository
5. Railway will auto-detect Python and deploy
6. Copy the public URL (e.g., `https://your-app.railway.app`)

### 2. Render

1. Push to GitHub
2. Go to [Render](https://render.com)
3. New → Web Service → Connect repository
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Google Cloud Run

```bash
gcloud run deploy ifc-generator \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 4. AWS Lambda (with Mangum)

Add to `requirements.txt`:
```
mangum==0.17.0
```

Create `lambda_handler.py`:
```python
from mangum import Mangum
from main import app

handler = Mangum(app)
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py

# Test endpoint
curl http://localhost:8000/health
```

## API Usage

### Generate IFC File

**POST** `/generate-ifc`

```json
{
  "project_name": "My Building",
  "tool_calls": [
    {
      "function": {
        "name": "create_wall",
        "arguments": {
          "name": "Wall-001",
          "length": 5.0,
          "height": 3.0,
          "thickness": 0.2,
          "x": 0,
          "y": 0,
          "z": 0
        }
      }
    }
  ]
}
```

Returns: Binary IFC file

## After Deployment

1. Get your deployed URL (e.g., `https://your-app.railway.app`)
2. Add it as a Supabase secret: `PYTHON_BACKEND_URL`
3. The edge function will automatically call your Python backend
4. Your app will now generate proper IFC files with full BIM data!

## Why IfcOpenShell?

IfcOpenShell is the core library that powers BlenderBIM. It provides:
- Full IFC schema support (IFC2x3, IFC4, IFC4.3)
- Proper geometry generation
- Complete BIM property support
- Industry-standard compliance
- No Blender GUI needed - pure Python library
