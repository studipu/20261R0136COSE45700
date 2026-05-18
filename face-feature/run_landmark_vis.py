"""Run landmark visualization on all input images."""
import sys
from pathlib import Path

_PIPELINE_DIR = Path(__file__).parent
sys.path.insert(0, str(_PIPELINE_DIR))

from pipeline.feature_extractor import visualize_landmarks

INPUT_DIR  = _PIPELINE_DIR / "input_image"
OUTPUT_DIR = _PIPELINE_DIR / "output_landmark_vis"
OUTPUT_DIR.mkdir(exist_ok=True)

images = sorted(p for p in INPUT_DIR.glob("*.png") if "_kp_debug" not in p.name)

print(f"Found {len(images)} images")
for img_path in images:
    out_path = OUTPUT_DIR / img_path.name
    print(f"  {img_path.name} ...", end=" ", flush=True)
    try:
        vis = visualize_landmarks(str(img_path), save_path=str(out_path))
        print(f"ok  ({vis.size[0]}x{vis.size[1]})")
    except Exception as e:
        print(f"FAILED: {e}")

print(f"\nSaved to: {OUTPUT_DIR}")
