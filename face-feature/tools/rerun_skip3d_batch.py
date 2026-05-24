"""
Re-run full pipeline outputs using existing per-sample GLBs.

This script is intended for avatar_keys / feature-mapping iterations where
Stage 2 (2D -> 3D generation) must remain fixed and only Stage 3+ should be
recomputed.

Usage:
    python tools/rerun_skip3d_batch.py
    python tools/rerun_skip3d_batch.py --output-root output_full_28_rerun_v2
    python tools/rerun_skip3d_batch.py --output-root output_full_28_rerun_v2 --with-debug
    python tools/rerun_skip3d_batch.py --ids 004 014 021 024 028 --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


# Existing completed samples in output_full_28.
# 004 is explicitly pinned to 004.png because the legacy batch-run output
# collided on stem-only folder naming; the current GLB/render pair matches
# the PNG input, not 004.jpeg.
DEFAULT_SAMPLE_MAP: dict[str, str] = {
    "001": "001.png",
    "002": "002.png",
    "003": "003.jpg",
    "004": "004.png",
    "007": "007.png",
    "009": "009.png",
    "010": "010.jpg",
    "011": "011.jpg",
    "012": "012.png",
    "013": "013.png",
    "014": "014.png",
    "015": "015.png",
    "016": "016.png",
    "017": "017.png",
    "018": "018.png",
    "019": "019.png",
    "020": "020.png",
    "021": "021.png",
    "022": "022.png",
    "023": "023.png",
    "024": "024.png",
    "025": "025.png",
    "026": "026.png",
    "027": "027.png",
    "028": "028.png",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--glb-root",
        default="output_full_28",
        help="Folder containing per-sample avatar.glb outputs.",
    )
    parser.add_argument(
        "--output-root",
        default="output_full_28_rerun_v1",
        help="Destination root for rerun outputs.",
    )
    parser.add_argument(
        "--debug-root",
        default=None,
        help=(
            "Destination root for per-sample debug outputs. "
            "Defaults to <output-root>_debug when --with-debug is set."
        ),
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        default=None,
        help="Optional subset of sample ids to rerun (e.g. 004 014 024).",
    )
    parser.add_argument(
        "--with-debug",
        action="store_true",
        help="Also save original-image landmarks_debug.png for each sample.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands only without executing them.",
    )
    return parser.parse_args()


def _resolve_root(base_root: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path

    # Accept either project-root-relative ("face-feature/output_x") or
    # face-feature-root-relative ("output_x") paths.
    if path.parts and path.parts[0] == base_root.name:
        return base_root.parent / path
    return base_root / path


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    glb_root = _resolve_root(root, args.glb_root)
    output_root = _resolve_root(root, args.output_root)
    debug_root = _resolve_root(
        root,
        args.debug_root if args.debug_root else f"{args.output_root}_debug"
    ) if args.with_debug else None
    main_py = root / "main.py"

    selected_ids = args.ids if args.ids else list(DEFAULT_SAMPLE_MAP.keys())

    failures: list[str] = []
    commands: list[tuple[str, list[str], list[str] | None]] = []

    for sample_id in selected_ids:
        image_name = DEFAULT_SAMPLE_MAP.get(sample_id)
        if not image_name:
            failures.append(f"{sample_id}: unknown sample id")
            continue

        image_path = root / "input_image" / image_name
        glb_path = glb_root / sample_id / "avatar.glb"
        sample_output = output_root / sample_id
        debug_output = debug_root / sample_id if debug_root else None

        if not image_path.is_file():
            failures.append(f"{sample_id}: missing image {image_path}")
            continue
        if not glb_path.is_file():
            failures.append(f"{sample_id}: missing GLB {glb_path}")
            continue

        run_cmd = [
            sys.executable,
            str(main_py),
            "--output",
            str(sample_output),
            "run",
            "--image",
            str(image_path),
            "--skip-3d",
            "--glb",
            str(glb_path),
        ]
        debug_cmd = None
        if debug_output is not None:
            debug_cmd = [
                sys.executable,
                str(main_py),
                "--output",
                str(debug_output),
                "debug",
                "--image",
                str(image_path),
            ]
        commands.append((sample_id, run_cmd, debug_cmd))

    if failures:
        print("[rerun-skip3d] configuration issues:")
        for failure in failures:
            print(f"  - {failure}")
        if not commands:
            return 1
        print("[rerun-skip3d] proceeding with valid samples only.")

    print(f"[rerun-skip3d] samples: {len(commands)}")
    print(f"[rerun-skip3d] glb root: {glb_root}")
    print(f"[rerun-skip3d] output root: {output_root}")
    if debug_root is not None:
        print(f"[rerun-skip3d] debug root: {debug_root}")

    for sample_id, cmd, debug_cmd in commands:
        print(" ".join(f'"{part}"' if " " in part else part for part in cmd))
        if debug_cmd is not None:
            print(
                "[debug] " +
                " ".join(f'"{part}"' if " " in part else part for part in debug_cmd)
            )
        if args.dry_run:
            continue
        result = subprocess.run(cmd, cwd=root)
        if result.returncode != 0:
            print(
                f"[rerun-skip3d] sample {sample_id} failed "
                f"with exit code {result.returncode}"
            )
            return result.returncode
        if debug_cmd is not None:
            debug_result = subprocess.run(debug_cmd, cwd=root)
            if debug_result.returncode != 0:
                print(
                    f"[rerun-skip3d] sample {sample_id} debug failed "
                    f"with exit code {debug_result.returncode}"
                )
                return debug_result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
