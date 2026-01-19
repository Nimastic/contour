"""
Contour - FastAPI Backend
"""

import os
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from . import terrain
from . import gemini_client
from . import fal_stylize
from . import gpx_parser

# Load environment variables
load_dotenv()

# Setup paths
BASE_DIR = Path(__file__).parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Create FastAPI app
app = FastAPI(title="Contour", description="2D Maps to 3D Terrain")

# Serve frontend static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend"), name="static")


@app.get("/")
async def root():
    """Serve the main page."""
    return FileResponse(BASE_DIR / "frontend" / "index.html")


@app.post("/api/upload")
async def upload_map(file: UploadFile = File(...)):
    """
    Upload a map file (GeoTIFF or image).
    Returns texture and bounds (if GeoTIFF).
    """
    # Validate file type
    allowed_extensions = {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".webp"}
    ext = Path(file.filename).suffix.lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(400, f"Invalid file type. Allowed: {allowed_extensions}")
    
    # Save file
    file_id = str(uuid.uuid4())[:8]
    save_path = UPLOADS_DIR / f"{file_id}{ext}"
    
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Process based on file type
    try:
        if ext in {".tif", ".tiff"}:
            # GeoTIFF - extract bounds and texture
            data = terrain.extract_geotiff_data(str(save_path))
            return JSONResponse({
                "success": True,
                "file_id": file_id,
                "bounds": data["bounds"],
                "texture_b64": data["texture_b64"],
                "width": data["width"],
                "height": data["height"],
                "has_bounds": True,
            })
        else:
            # Regular image - just extract texture
            data = terrain.extract_from_image(str(save_path))
            return JSONResponse({
                "success": True,
                "file_id": file_id,
                "texture_b64": data["texture_b64"],
                "width": data["width"],
                "height": data["height"],
                "has_bounds": False,
            })
    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")


@app.post("/api/upload-gpx")
async def upload_gpx(file: UploadFile = File(...)):
    """
    Upload a GPX file and extract track coordinates.
    """
    ext = Path(file.filename).suffix.lower()
    
    if ext != ".gpx":
        raise HTTPException(400, "Invalid file type. Only .gpx files allowed.")
    
    # Save file
    file_id = str(uuid.uuid4())[:8]
    save_path = UPLOADS_DIR / f"{file_id}.gpx"
    
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        # Parse GPX and extract track points
        data = gpx_parser.parse_gpx(str(save_path), simplify_factor=20)
        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "name": data["name"],
            "points": data["points"],
            "bounds": data["bounds"],
            "elevation_range": data["elevation_range"],
            "total_points": data["total_points"],
            "simplified_points": data["simplified_points"]
        })
    except Exception as e:
        raise HTTPException(500, f"GPX parsing error: {str(e)}")


@app.post("/api/extract-bounds")
async def extract_bounds(file_id: str):
    """
    Use Gemini to extract bounds from an uploaded image.
    """
    # Find the file
    files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    if not files:
        raise HTTPException(404, "File not found")
    
    file_path = files[0]
    
    try:
        bounds = await gemini_client.extract_bounds_from_image(str(file_path))
        return JSONResponse({
            "success": True,
            "bounds": bounds
        })
    except Exception as e:
        raise HTTPException(500, f"Gemini error: {str(e)}")


@app.post("/api/narrate")
async def narrate(location_info: dict, features: list[str] = []):
    """
    Generate narration for current flyover position.
    """
    try:
        narration = await gemini_client.generate_narration(location_info, features)
        return JSONResponse({
            "success": True,
            "narration": narration
        })
    except Exception as e:
        raise HTTPException(500, f"Gemini error: {str(e)}")


@app.post("/api/stylize")
async def stylize(file_id: str):
    """
    Stylize uploaded texture using FAL Nano Banana Pro.
    """
    # Find the file
    files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    if not files:
        raise HTTPException(404, "File not found")

    file_path = files[0]

    try:
        stylized_url = fal_stylize.stylize_texture(str(file_path))
        return JSONResponse({
            "success": True,
            "stylized_url": stylized_url
        })
    except Exception as e:
        raise HTTPException(500, f"Stylization error: {str(e)}")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "gemini": gemini_client.HAS_GEMINI, "fal": fal_stylize.HAS_FAL}


@app.get("/api/gemini-key")
async def get_gemini_key():
    """Return Gemini API key for client-side Live API (hackathon only - not production safe)."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise HTTPException(500, "GEMINI_API_KEY not configured")
    return {"key": key}

