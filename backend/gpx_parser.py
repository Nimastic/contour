"""
GPX Parser - Extract track coordinates from GPX files
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any


def parse_gpx(file_path: str, simplify_factor: int = 10) -> Dict[str, Any]:
    """
    Parse a GPX file and extract track points.
    
    Args:
        file_path: Path to the GPX file
        simplify_factor: Keep every Nth point to reduce data (default: 10)
    
    Returns:
        {
            "name": "Track name",
            "points": [{"lat": ..., "lon": ..., "ele": ...}, ...],
            "bounds": {"north": ..., "south": ..., "east": ..., "west": ...},
            "elevation_range": {"min": ..., "max": ...},
            "total_points": ...
        }
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Handle GPX namespace
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    # Find track name
    name_elem = root.find('.//gpx:trk/gpx:name', ns)
    track_name = name_elem.text if name_elem is not None else "Unknown Track"
    
    # Extract all track points
    points = []
    all_lats = []
    all_lons = []
    all_eles = []
    
    for trkpt in root.findall('.//gpx:trkpt', ns):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        ele_elem = trkpt.find('gpx:ele', ns)
        ele = float(ele_elem.text) if ele_elem is not None else 0
        
        all_lats.append(lat)
        all_lons.append(lon)
        all_eles.append(ele)
    
    # Simplify by taking every Nth point
    total_points = len(all_lats)
    for i in range(0, total_points, simplify_factor):
        points.append({
            "lat": all_lats[i],
            "lon": all_lons[i],
            "ele": all_eles[i]
        })
    
    # Always include the last point
    if total_points > 0 and (total_points - 1) % simplify_factor != 0:
        points.append({
            "lat": all_lats[-1],
            "lon": all_lons[-1],
            "ele": all_eles[-1]
        })
    
    # Calculate bounds and elevation range
    if all_lats:
        bounds = {
            "north": max(all_lats),
            "south": min(all_lats),
            "east": max(all_lons),
            "west": min(all_lons)
        }
        elevation_range = {
            "min": min(all_eles),
            "max": max(all_eles)
        }
    else:
        bounds = {"north": 0, "south": 0, "east": 0, "west": 0}
        elevation_range = {"min": 0, "max": 0}
    
    return {
        "name": track_name,
        "points": points,
        "bounds": bounds,
        "elevation_range": elevation_range,
        "total_points": total_points,
        "simplified_points": len(points)
    }
