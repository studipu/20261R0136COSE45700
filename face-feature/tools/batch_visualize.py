"""
Run visualize_avatar_keys on all available images.
Usage: python tools/batch_visualize.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.visualize_avatar_keys import plot_keys
from pipeline.feature_extractor import extract_features_full, visualize_landmarks, _run_adf, _to_bgr, _ensure_path
import os

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "output_test" / "batch"
OUT.mkdir(parents=True, exist_ok=True)

def find_images():
    exts = {".png", ".jpg", ".jpeg"}
    images = []
    inp = ROOT / "input_image"
    if inp.is_dir():
        images += sorted(p for p in inp.iterdir() if p.suffix.lower() in exts)
    out = ROOT / "output"
    if out.is_dir():
        for sub in sorted(out.iterdir()):
            fp = sub / "renders" / "front.png"
            if fp.is_file():
                images.append(fp)
    return images

images = find_images()
print(f"[Batch] {len(images)} images → {OUT}")

ok, fail = 0, 0
for img in images:
    label = img.relative_to(ROOT)
    if img.parent.name == "renders":
        stem = img.parent.parent.name + "_" + img.stem   # e.g. 02_nohair_front
    elif img.parent.name == "input_image":
        stem = img.stem
    else:
        stem = img.parent.name + "_" + img.stem
    try:
        fv, avatar_keys = extract_features_full(str(img))
        if avatar_keys is None:
            print(f"  FAIL (no face) {label}")
            fail += 1
            continue
        chart = str(OUT / f"keys_{stem}.png")
        lm    = str(OUT / f"lm_{stem}.png")
        plot_keys(avatar_keys, chart, title=str(label))
        visualize_landmarks(str(img), save_path=lm)
        print(f"  OK   {label}")
        ok += 1
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        fail += 1

print(f"\n[Batch] done: {ok} ok, {fail} failed — saved to {OUT}")
