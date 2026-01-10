# test/test_fal.py
import os
from dotenv import load_dotenv

load_dotenv()

import base64
import fal_client
from pathlib import Path

print(f"FAL_KEY set: {'FAL_KEY' in os.environ}")

# Test image path - relative to project root
IMAGE_PATH = "test/test_map.jpg"

PROMPT = """Enhance this topographic map with vivid hypsometric tinting:

- Apply elevation-based coloring ONLY to the land terrain areas:
  - Coastal lowlands and beaches: pale cream, soft mint greens
  - Low elevations: light greens, yellow-greens
  - Mid elevations: golden yellows, warm ochres, tans
  - High elevations: deep rusty browns, burnt sienna, terra cotta reds
  - Highest peaks: dark reddish-brown (#8B4513), with snow-capped areas in white

- Ocean: deep rich blue with subtle depth gradient (darker = deeper)
- Shallow water/reefs: lighter turquoise blue

- KEEP EXACTLY AS-IS:
  - All text labels and place names
  - Map borders and margins  
  - Legend and scale bar
  - Grid lines and coordinates

- Do NOT add shadows or 3D hillshading
- Maintain exact same dimensions and layout

Style reference: vintage raised relief map with rich, saturated terrain colors"""


def test_stylize():
    # Load and encode image
    print(f"Loading {IMAGE_PATH}...")
    with open(IMAGE_PATH, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    ext = Path(IMAGE_PATH).suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    data_uri = f"data:{mime};base64,{image_data}"
    
    print(f"Image size: {len(image_data) // 1024}KB (base64)")
    print("Sending to FAL (this takes 30-60s)...")
    
    result = fal_client.subscribe(
        "fal-ai/nano-banana-pro/edit",
        arguments={
            "prompt": PROMPT,
            "image_urls": [data_uri],
            "num_images": 1,
            "aspect_ratio": "auto",
            "output_format": "png",
            "resolution": "2K"
        },
        with_logs=True,
        on_queue_update=lambda u: print(f"  Status: {u}")
    )
    
    print(f"\nSuccess!")
    print(f"Result URL: {result['images'][0]['url']}")
    return result['images'][0]['url']


if __name__ == "__main__":
    url = test_stylize()
    print(f"\nOpen this URL to see result:\n{url}")