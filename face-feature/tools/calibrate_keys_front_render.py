"""
Collect raw geometric measurements from front render images only and
suggest calibrated lo/hi values for compute_avatar_keys.

Usage:
    python tools/calibrate_keys_front_render.py
    python tools/calibrate_keys_front_render.py --out output_test/calibration_front_render_log.txt
    python tools/calibrate_keys_front_render.py --render-root output_wsl

Scans:
  - <render-root>/*/renders/front.png
  - <render-root>/renders/front.png

Requires: ADF WSL server or ADF_SERVER_URL env set.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.feature_extractor import _run_adf, _to_bgr, _ensure_path, compute_avatar_keys
from pipeline.avatar_keys import SIGNED_CALIBRATION as SIGNED_KEYS, MAP01_CALIBRATION as MAP01_KEYS

OBSERVE_KEYS = [
    "Eye_Rot",
    "Brow_Rot",
    "Eye_TopLidDown",
    "Eye_TopLidFlat",
    "Eye_LowerLidFlat",
    "Face_JawLine",
    "Face_Roundness",
]

ALL_RAW_KEYS = list(SIGNED_KEYS) + list(MAP01_KEYS) + OBSERVE_KEYS


def _coerce_raw_value(value):
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (int, float, np.floating)):
        return float(value)
    return None


def find_front_renders(root: Path, render_root: str) -> list[Path]:
    base = (root / render_root).resolve()
    images: list[Path] = []

    direct = base / "renders" / "front.png"
    if direct.is_file():
        images.append(direct)

    if base.is_dir():
        for subdir in sorted(base.iterdir()):
            fp = subdir / "renders" / "front.png"
            if fp.is_file():
                images.append(fp)

    return sorted(set(images))


def extract_raw(image_path: Path) -> "dict | None":
    img_bgr = _to_bgr(str(image_path))
    img_path, tmp_path = _ensure_path(str(image_path), img_bgr)
    groups, _, kps_raw = _run_adf(img_bgr, img_path)
    if tmp_path:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    if groups is None or kps_raw is None:
        return None
    raw_out: dict = {}
    compute_avatar_keys(kps_raw, _raw_out=raw_out)
    return raw_out


def percentile_range(values: list[float], p_lo: float = 10.0, p_hi: float = 90.0) -> tuple[float, float]:
    arr = np.array(values)
    return float(np.percentile(arr, p_lo)), float(np.percentile(arr, p_hi))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="output_test/calibration_front_render_log.txt")
    parser.add_argument(
        "--render-root",
        default="output",
        help="root folder that contains per-sample renders or a single renders/ directory",
    )
    parser.add_argument("--p-lo", type=float, default=10.0, dest="p_lo")
    parser.add_argument("--p-hi", type=float, default=90.0, dest="p_hi")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    images = find_front_renders(root, args.render_root)
    print(f"[CalibFront] found {len(images)} front renders")

    log_lines: list[str] = []

    def log(line: str = ""):
        print(line)
        log_lines.append(line)

    log("=" * 70)
    log("Avatar Key Calibration Run (front_render only)")
    log(f"Timestamp  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Render root: {args.render_root}")
    log(f"Images     : {len(images)}")
    log(f"Percentile : p{args.p_lo:.0f} / p{args.p_hi:.0f}")
    log("=" * 70)

    collected: dict[str, list[float]] = {k: [] for k in ALL_RAW_KEYS}
    failures: list[str] = []

    for img in images:
        label = img.relative_to(root)
        raw = extract_raw(img)
        if raw is None:
            log(f"  FAIL  {label}")
            failures.append(str(label))
            continue

        log(f"  OK    {label}")
        for key in ALL_RAW_KEYS:
            raw_value = _coerce_raw_value(raw.get(key))
            if raw_value is None:
                continue
            collected[key].append(raw_value)
            log(f"          {key:<22} {raw_value:+.4f}")

    log()
    log(f"Success: {len(images) - len(failures)}/{len(images)}  Failed: {len(failures)}")
    if failures:
        for failure in failures:
            log(f"  - {failure}")

    log()
    log("=" * 70)
    log("Raw value statistics per key")
    log("=" * 70)
    fmt = (
        f"{'Key':<22} {'n':>3}  {'min':>8} {'p10':>8} {'p50':>8} "
        f"{'p90':>8} {'max':>8}  {'cur_lo':>8} {'cur_hi':>8}"
    )
    log(fmt)
    log("-" * len(fmt))

    all_current = {**SIGNED_KEYS, **MAP01_KEYS}
    for key in ALL_RAW_KEYS:
        vals = collected[key]
        if not vals:
            log(f"  {key:<22} {'0':>3}  (no data)")
            continue

        arr = np.array(vals)
        p10 = float(np.percentile(arr, args.p_lo))
        p90 = float(np.percentile(arr, args.p_hi))
        cur = all_current.get(key)
        cur_lo = f"{cur[0]:+.3f}" if cur else "  obs"
        cur_hi = f"{cur[1]:+.3f}" if cur else "  obs"
        log(
            f"  {key:<22} {len(vals):>3}  "
            f"{arr.min():>8.4f} {p10:>8.4f} {float(np.median(arr)):>8.4f} "
            f"{p90:>8.4f} {arr.max():>8.4f}  {cur_lo:>8} {cur_hi:>8}"
        )

    log()
    log("=" * 70)
    log(f"Recommended lo/hi  (p{args.p_lo:.0f}/p{args.p_hi:.0f} of collected data)")
    log("Paste into compute_avatar_keys in avatar_keys.py")
    log("=" * 70)

    rec: dict[str, tuple[float, float]] = {}
    for key, (cur_lo, cur_hi) in {**SIGNED_KEYS, **MAP01_KEYS}.items():
        vals = collected[key]
        if len(vals) < 3:
            log(
                f"  # {key}: insufficient data ({len(vals)} samples) "
                f"keep current ({cur_lo}, {cur_hi})"
            )
            rec[key] = (cur_lo, cur_hi)
            continue

        lo, hi = percentile_range(vals, args.p_lo, args.p_hi)
        span = hi - lo
        lo_m = round(lo - 0.05 * span, 4)
        hi_m = round(hi + 0.05 * span, 4)
        changed = abs(lo_m - cur_lo) > 0.005 or abs(hi_m - cur_hi) > 0.005
        marker = "  # CHANGED" if changed else ""
        log(f'    "{key}": ({lo_m:.4f}, {hi_m:.4f}),{marker}')
        rec[key] = (lo_m, hi_m)

    log()
    log("=" * 70)
    log("Copy-paste snippet for compute_avatar_keys (only changed lines)")
    log("=" * 70)
    for key, (cur_lo, cur_hi) in {**SIGNED_KEYS, **MAP01_KEYS}.items():
        new_lo, new_hi = rec.get(key, (cur_lo, cur_hi))
        if abs(new_lo - cur_lo) <= 0.005 and abs(new_hi - cur_hi) <= 0.005:
            continue
        if key in SIGNED_KEYS:
            log(f"    {key} = _map_signed(_rv, {new_lo}, {new_hi})  # was ({cur_lo}, {cur_hi})")
        else:
            log(f"    {key} = _map_01(_rv, {new_lo}, {new_hi})  # was ({cur_lo}, {cur_hi})")

    log()
    log("=" * 70)

    out_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n[CalibFront] log saved: {out_path}")


if __name__ == "__main__":
    main()
