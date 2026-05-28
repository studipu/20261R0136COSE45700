"""
Collect raw geometric measurements across all available images and
suggest calibrated lo/hi values for compute_avatar_keys.

Usage:
    python tools/calibrate_keys.py
    python tools/calibrate_keys.py --out output_test/calibration_log.txt

Scans:
  - input_image/*.{png,jpg,jpeg}
  - output/*/renders/front.png

Requires: ADF WSL server or ADF_SERVER_URL env set.
"""

from __future__ import annotations

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.feature_extractor import _run_adf, _to_bgr, _ensure_path, compute_avatar_keys
from pipeline.avatar_keys import SIGNED_CALIBRATION as SIGNED_KEYS, MAP01_CALIBRATION as MAP01_KEYS

# Keys with fixed formula (raw = already meaningful, just observe)
OBSERVE_KEYS = [
    "Eye_Rot",         # raw = avg tilt degrees (/20 then clamp)
    "Brow_Rot",        # raw = avg tilt degrees (/30 then clamp)
    "Eye_TopLidDown",  # raw = center opening ratio
    "Eye_TopLidFlat",
    "Eye_LowerLidFlat",
    "Face_JawLine",
    "Face_Roundness",
]

ALL_RAW_KEYS = list(dict.fromkeys(list(SIGNED_KEYS) + list(MAP01_KEYS) + OBSERVE_KEYS))


def _coerce_raw_value(value):
    """Extract a numeric raw value from debug payloads."""
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (int, float, np.floating)):
        return float(value)
    return None


def find_images(root: Path) -> list[Path]:
    exts = {".png", ".jpg", ".jpeg"}
    images = []
    # input_image/
    inp = root / "input_image"
    if inp.is_dir():
        images += sorted(p for p in inp.iterdir() if p.suffix.lower() in exts)
    # output/*/renders/front.png
    out = root / "output"
    if out.is_dir():
        for subdir in sorted(out.iterdir()):
            fp = subdir / "renders" / "front.png"
            if fp.is_file():
                images.append(fp)
    return images


def extract_raw(image_path: Path) -> "dict | None":
    img_bgr = _to_bgr(str(image_path))
    img_path, _tmp = _ensure_path(str(image_path), img_bgr)
    groups, _, kps_raw = _run_adf(img_bgr, img_path)
    if _tmp:
        try:
            os.unlink(_tmp)
        except OSError:
            pass
    if groups is None or kps_raw is None:
        return None

    # depth map이 있으면 로드 (output/*/renders/front.png 케이스)
    depth = None
    img_shape = None
    depth_path = image_path.parent / "front_depth.npy"
    if depth_path.is_file():
        depth = np.load(str(depth_path))
        img_shape = (img_bgr.shape[0], img_bgr.shape[1])

    raw_out: dict = {}
    compute_avatar_keys(kps_raw, _raw_out=raw_out, depth=depth, img_shape=img_shape)
    return raw_out


def calibrated_range(values: list, range_mode: str, p_lo: float = 10.0, p_hi: float = 90.0):
    arr = np.array(values)
    if range_mode == "percentile":
        return float(np.percentile(arr, p_lo)), float(np.percentile(arr, p_hi))
    return float(arr.min()), float(arr.max())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="output_test/calibration_log.txt")
    parser.add_argument("--range-mode", choices=("minmax", "percentile"), default="minmax",
                        help="lo/hi source: minmax for curated valid samples, percentile for noisy batches")
    parser.add_argument("--p-lo", type=float, default=10.0, dest="p_lo",
                        help="lower percentile for lo bound when --range-mode percentile")
    parser.add_argument("--p-hi", type=float, default=90.0, dest="p_hi",
                        help="upper percentile for hi bound when --range-mode percentile")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    images = find_images(root)
    print(f"[Calib] found {len(images)} images")

    log_lines = []
    def log(s=""):
        print(s)
        log_lines.append(s)

    log("=" * 70)
    log(f"Avatar Key Calibration Run")
    log(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Images    : {len(images)}")
    log(f"Range mode: {args.range_mode}")
    if args.range_mode == "percentile":
        log(f"Percentile: p{args.p_lo:.0f} / p{args.p_hi:.0f}")
    log("=" * 70)

    # ── Per-image collection ─────────────────────────────────────────────
    collected: dict[str, list[float]] = {k: [] for k in ALL_RAW_KEYS}
    successes, failures = [], []

    for img in images:
        label = img.relative_to(root)
        raw = extract_raw(img)
        if raw is None:
            log(f"  FAIL  {label}")
            failures.append(str(label))
            continue

        log(f"  OK    {label}")
        for k in ALL_RAW_KEYS:
            raw_value = _coerce_raw_value(raw.get(k))
            if raw_value is not None:
                collected[k].append(raw_value)
                log(f"          {k:<22} {raw_value:+.4f}")

    log()
    log(f"Success: {len(successes) + len(images) - len(failures)}/{len(images)}  "
        f"Failed: {len(failures)}")
    if failures:
        for f in failures:
            log(f"  - {f}")

    # ── Per-key statistics ───────────────────────────────────────────────
    log()
    log("=" * 70)
    log("Raw value statistics per key")
    log("=" * 70)
    fmt = f"{'Key':<22} {'n':>3}  {'min':>8} {'p10':>8} {'p50':>8} {'p90':>8} {'max':>8}  {'cur_lo':>8} {'cur_hi':>8}"
    log(fmt)
    log("-" * len(fmt))

    all_current = {**SIGNED_KEYS, **MAP01_KEYS}
    for k in ALL_RAW_KEYS:
        vals = collected[k]
        if not vals:
            log(f"  {k:<22} {'0':>3}  (no data)")
            continue
        arr = np.array(vals)
        p10, p90 = float(np.percentile(arr, args.p_lo)), float(np.percentile(arr, args.p_hi))
        cur = all_current.get(k)
        cur_lo = f"{cur[0]:+.3f}" if cur else "  obs"
        cur_hi = f"{cur[1]:+.3f}" if cur else "  obs"
        log(f"  {k:<22} {len(vals):>3}  "
            f"{arr.min():>8.4f} {p10:>8.4f} {float(np.median(arr)):>8.4f} "
            f"{p90:>8.4f} {arr.max():>8.4f}  {cur_lo:>8} {cur_hi:>8}")

    # ── Recommended lo/hi ────────────────────────────────────────────────
    log()
    log("=" * 70)
    if args.range_mode == "percentile":
        log(f"Recommended lo/hi  (p{args.p_lo:.0f}/p{args.p_hi:.0f} of collected data)")
    else:
        log("Recommended lo/hi  (min/max of collected data)")
    log("Paste into compute_avatar_keys in feature_extractor.py")
    log("=" * 70)

    rec: dict[str, tuple] = {}
    for k, (cur_lo, cur_hi) in {**SIGNED_KEYS, **MAP01_KEYS}.items():
        vals = collected[k]
        if len(vals) < 3:
            log(f"  # {k}: insufficient data ({len(vals)} samples) — keep current ({cur_lo}, {cur_hi})")
            rec[k] = (cur_lo, cur_hi)
            continue
        lo, hi = calibrated_range(vals, args.range_mode, args.p_lo, args.p_hi)
        # Add 10% margin
        span = hi - lo
        lo_m = round(lo - 0.05 * span, 4)
        hi_m = round(hi + 0.05 * span, 4)
        changed = abs(lo_m - cur_lo) > 0.005 or abs(hi_m - cur_hi) > 0.005
        marker = "  # CHANGED" if changed else ""
        log(f'    "{k}": ({lo_m:.4f}, {hi_m:.4f}),{marker}')
        rec[k] = (lo_m, hi_m)

    # ── Python snippet ───────────────────────────────────────────────────
    log()
    log("=" * 70)
    log("Copy-paste snippet for compute_avatar_keys (only changed lines)")
    log("=" * 70)
    for k, (cur_lo, cur_hi) in {**SIGNED_KEYS, **MAP01_KEYS}.items():
        new_lo, new_hi = rec.get(k, (cur_lo, cur_hi))
        if abs(new_lo - cur_lo) > 0.005 or abs(new_hi - cur_hi) > 0.005:
            if k in SIGNED_KEYS:
                log(f"    {k} = _map_signed(_rv, {new_lo}, {new_hi})  # was ({cur_lo}, {cur_hi})")
            else:
                log(f"    {k} = _map_01(_rv, {new_lo}, {new_hi})  # was ({cur_lo}, {cur_hi})")

    log()
    log("=" * 70)

    out_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n[Calib] log saved: {out_path}")


if __name__ == "__main__":
    main()
