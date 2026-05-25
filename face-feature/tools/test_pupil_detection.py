"""
Quick test: OpenCV pupil detection vs proxy comparison.
Usage: ADF_SERVER_URL=http://127.0.0.1:8000 python tools/test_pupil_detection.py
"""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from pipeline.feature_extractor import _to_bgr, _run_adf, _ensure_path
from pipeline.avatar_keys import compute_avatar_keys
from pipeline.pupil_detector import detect_pupils

root = Path(__file__).resolve().parents[1]
imgs = sorted(
    list((root / "input_image").glob("*.png"))
    + list((root / "input_image").glob("*.jpg"))
)

header = f"{'Image':<28} {'w_proxy':>8} {'w_cv':>8} {'wv_cv':>8} {'detected':>8}"
print(header)
print("-" * len(header))

detected_cnt = 0
total = 0

for img_path in imgs:
    img_bgr = _to_bgr(str(img_path))
    ip, tmp = _ensure_path(str(img_path), img_bgr)
    groups, _, kps = _run_adf(img_bgr, ip)
    if tmp:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    if groups is None:
        print(f"{img_path.name:<28} FAIL")
        continue

    total += 1

    r0: dict = {}
    compute_avatar_keys(kps, _raw_out=r0)
    w_proxy = r0["Eye_PupilWidth"]

    manual = detect_pupils(img_bgr, kps)
    r1: dict = {}
    compute_avatar_keys(kps, manual=manual, _raw_out=r1)
    w_cv  = r1["Eye_PupilWidth"]
    wv_cv = r1.get("Eye_PupilWidthV", w_cv)

    det = manual is not None
    if det:
        detected_cnt += 1

    note = "  <- proxy fallback" if not det else ""
    print(f"{img_path.name:<28} {w_proxy:>8.3f} {w_cv:>8.3f} {wv_cv:>8.3f} {str(det):>8}{note}")

print()
print(f"OpenCV 검출 성공: {detected_cnt}/{total} ({100*detected_cnt/max(total,1):.0f}%)")
