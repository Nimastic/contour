"""
Terrain processing - GeoTIFF extraction and heightmap generation
"""

import io
import base64
import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path

# Try rasterio, fall back gracefully
try:
    import rasterio
    from rasterio.warp import transform_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False
    print("Warning: rasterio not installed. GeoTIFF georeferencing disabled.")


def extract_geotiff_data(file_path: str) -> dict:
    """
    Extract bounds and texture from a GeoTIFF file.
    
    Returns:
        {
            "bounds": {"north": ..., "south": ..., "east": ..., "west": ...},
            "texture_b64": "...",  # Base64 JPEG
            "width": ...,
            "height": ...,
        }
    """
    file_path = Path(file_path)
    
    if not HAS_RASTERIO:
        raise RuntimeError("rasterio required for GeoTIFF processing")
    
    with rasterio.open(file_path) as src:
        # Extract bounds in WGS84 (lat/lon)
        wgs84_bounds = transform_bounds(src.crs, 'EPSG:4326', *src.bounds)
        bounds = {
            "west": wgs84_bounds[0],
            "south": wgs84_bounds[1],
            "east": wgs84_bounds[2],
            "north": wgs84_bounds[3]
        }
        
        # Read image data
        data = src.read()  # Shape: (bands, height, width)
        
        # Convert to RGB or normalize single band
        if data.shape[0] >= 3:
            # Traditional 3-band (RGB) GeoTIFF
            rgb = np.stack([data[0], data[1], data[2]], axis=-1)
            # Ensure 8-bit
            if rgb.dtype != np.uint8:
                rgb = ((rgb - rgb.min()) / (rgb.max() - rgb.min()) * 255).astype(np.uint8)
        else:
            # Single-band (DEM/Grayscale) - Perform min-max normalization (Whitescaling)
            band = data[0].astype(float)
            valid_mask = band != src.nodata if src.nodata is not None else np.ones_like(band, dtype=bool)
            
            b_min = band[valid_mask].min() if np.any(valid_mask) else 0
            b_max = band[valid_mask].max() if np.any(valid_mask) else 1
            
            if b_max > b_min:
                normalized = (band - b_min) / (b_max - b_min) * 255
            else:
                normalized = np.zeros_like(band)
                
            normalized = np.clip(normalized, 0, 255).astype(np.uint8)
            rgb = np.stack([normalized, normalized, normalized], axis=-1)
        
        # Create PIL image
        img = Image.fromarray(rgb)
        original_width, original_height = img.size
        
        # Resize for web (max 2048 on longest side)
        max_dim = 2048
        if img.width > max_dim or img.height > max_dim:
            ratio = min(max_dim / img.width, max_dim / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # Encode as base64 JPEG
        buffer = io.BytesIO()
        img.save(buffer, 'JPEG', quality=85)
        buffer.seek(0)
        texture_b64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return {
            "bounds": bounds,
            "texture_b64": texture_b64,
            "width": img.width,
            "height": img.height,
            "original_width": original_width,
            "original_height": original_height,
        }


def extract_from_image(file_path: str) -> dict:
    """
    Extract texture from a regular image (no georeferencing).
    Bounds must be provided separately.
    
    Returns:
        {
            "texture_b64": "...",
            "width": ...,
            "height": ...,
        }
    """
    img = Image.open(file_path)
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    original_width, original_height = img.size
    
    # Resize for web
    max_dim = 2048
    if img.width > max_dim or img.height > max_dim:
        ratio = min(max_dim / img.width, max_dim / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # Encode as base64 JPEG
    buffer = io.BytesIO()
    img.save(buffer, 'JPEG', quality=85)
    buffer.seek(0)
    texture_b64 = base64.b64encode(buffer.read()).decode('utf-8')
    
    return {
        "texture_b64": texture_b64,
        "width": img.width,
        "height": img.height,
        "original_width": original_width,
        "original_height": original_height,
    }


def process_heightmap(file_path: str, target_size: int = 512) -> str:
    """
    Process a heightmap image (e.g., from Gemini) for use in Three.js.
    Returns base64 PNG.
    """
    img = Image.open(file_path).convert('L')  # Grayscale
    
    # Apply slight blur to smooth
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Make square (required for displacement mapping)
    w, h = img.size
    max_dim = max(w, h)
    square = Image.new('L', (max_dim, max_dim), 0)
    offset = ((max_dim - w) // 2, (max_dim - h) // 2)
    square.paste(img, offset)
    
    # Resize to target
    final = square.resize((target_size, target_size), Image.LANCZOS)
    
    # Encode as base64 PNG
    buffer = io.BytesIO()
    final.save(buffer, 'PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.read()).decode('utf-8')
