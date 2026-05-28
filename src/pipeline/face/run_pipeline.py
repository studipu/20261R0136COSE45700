"""
Full pipeline orchestrator: Image -> 3D GLB -> Multi-view Render -> Feature Extraction.

Stages:
  2. Generate GLB with VARCO/Meshy API (or use existing GLB)
  3. Render multi-view images (front/left/right) with depth maps
  4. Extract facial features (prefer front render, fallback to original image)
  5. Select template (cute/slim/mature)
  6. Map initial slider values

CLI:
    python run_pipeline.py --image <path> --output-dir <dir> \
        [--provider varco|meshy] [--api-key <key>] \
        [--skip-3d] [--existing-glb <path>]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure this directory is on sys.path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from parameter_specs import apply_specs
from pupil_detector import extract_features_with_pupils
from template_selector import select_template
from varco_client import get_client


class Stage4ExtractionError(RuntimeError):
    def __init__(self, message: str, feature_debug: dict):
        super().__init__(message)
        self.feature_debug = feature_debug


def _stage2_generate_glb(
    image_path: str,
    out: Path,
    provider: str,
    api_key: str,
    skip_3d: bool,
    existing_glb: str | None,
) -> str | None:
    """Generate or locate a GLB file. Returns None if skip_3d and no GLB exists."""
    if skip_3d and not existing_glb:
        print("[Stage 2] skip-3d: no GLB generation")
        return None

    if skip_3d and existing_glb:
        if not Path(existing_glb).exists():
            raise FileNotFoundError(f"GLB file not found: {existing_glb}")
        print(f"[Stage 2] using existing GLB: {existing_glb}")
        return existing_glb

    if existing_glb and Path(existing_glb).exists():
        print(f"[Stage 2] using existing GLB: {existing_glb}")
        return existing_glb

    print(f"[Stage 2] generating GLB... (provider={provider})")
    client = get_client(provider, api_key)
    glb_path = str(out / "avatar.glb")
    client.image_to_3d(image_path, glb_path)
    print(f"[Stage 2] GLB saved: {glb_path}")
    return glb_path


def _stage3_render(glb_path: str | None, out: Path) -> tuple[dict, dict]:
    """Render multi-view images from GLB. Returns ({}, {}) if no GLB or on failure."""
    if glb_path is None:
        print("[Stage 3] no GLB, skipping rendering")
        return {}, {}

    render_dir = out / "renders"
    expected = {k: render_dir / f"{k}.png" for k in ("front", "left", "right")}
    if all(p.is_file() for p in expected.values()):
        print("[Stage 3] renders exist, skipping re-render")
        render_paths = {k: str(v) for k, v in expected.items()}
        return {}, render_paths

    try:
        # Import renderer here to avoid import errors when pyrender isn't installed
        from renderer import render_multiview

        print("[Stage 3] rendering multiview images...")
        renders = render_multiview(glb_path, str(render_dir))
        render_paths = {k: str(render_dir / f"{k}.png") for k in renders}
        print(f"[Stage 3] render complete: {list(render_paths.keys())}")
        return renders, render_paths
    except Exception as exc:
        print(f"[Stage 3] rendering failed ({exc}), falling back to original image")
        return {}, {}


def _stage4_extract(image_path: str, render_paths: dict) -> tuple:
    """Try front render first (depth files auto-loaded), then fall back to original."""
    print("[Stage 4] feature extraction (prefer front render, fallback to original)...")

    feature_debug = {
        "original": None,
        "front_render": None,
        "selected": None,
        "failures": [],
    }

    # Try front render first (depth map will be auto-loaded from same directory)
    front_render_path = render_paths.get("front")
    if front_render_path is None:
        feature_debug["failures"].append({"source": "front_render", "error": "front render missing"})
    else:
        try:
            feature_vector, avatar_keys, raw_out = extract_features_with_pupils(front_render_path)
            if feature_vector is None:
                raise ValueError("face not detected")
            feature_debug["front_render"] = feature_vector.to_dict()
            feature_debug["selected"] = "front_render"
            print(f"[Stage 4] front_render extracted: {feature_vector.to_dict()}")
            return feature_vector, avatar_keys, raw_out, "front_render", feature_debug
        except Exception as exc:
            error_message = str(exc) or exc.__class__.__name__
            feature_debug["failures"].append({"source": "front_render", "error": error_message})
            print(f"[Stage 4] front_render failed: {error_message}")

    # Fallback to original image
    try:
        feature_vector, avatar_keys, raw_out = extract_features_with_pupils(image_path)
        if feature_vector is None:
            raise ValueError("face not detected")
        feature_debug["original"] = feature_vector.to_dict()
        feature_debug["selected"] = "original"
        print(f"[Stage 4] original extracted: {feature_vector.to_dict()}")
        return feature_vector, avatar_keys, raw_out, "original", feature_debug
    except Exception as exc:
        error_message = str(exc) or exc.__class__.__name__
        feature_debug["failures"].append({"source": "original", "error": error_message})
        print(f"[Stage 4] original failed: {error_message}")

    failure_text = ", ".join(
        f"{item['source']}: {item['error']}" for item in feature_debug["failures"]
    ) or "no failure details"
    raise Stage4ExtractionError(
        "Stage 4 feature extraction failed for both original and front_render. "
        f"Details: {failure_text}",
        feature_debug,
    )


def run_pipeline(
    image_path: str,
    output_dir: str,
    provider: str = "meshy",
    api_key: str = "",
    skip_3d: bool = False,
    existing_glb: str | None = None,
) -> dict:
    """
    Run the full pipeline from image input to template selection.

    Returns a dict with status "ok" or "failed_stage4".
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Stage 2: GLB generation
    glb_path = _stage2_generate_glb(
        image_path, out, provider, api_key, skip_3d, existing_glb
    )

    # Stage 3: Render multi-view
    renders, render_paths = _stage3_render(glb_path, out)

    # Stage 4: Feature extraction
    try:
        fv, avatar_keys, raw_out, feature_source, feature_debug = _stage4_extract(image_path, render_paths)
    except Stage4ExtractionError as exc:
        output = {
            "status": "failed_stage4",
            "error": str(exc),
            "glb_path": glb_path,
            "renders": render_paths,
            "feature_vector": None,
            "feature_source": None,
            "feature_debug": exc.feature_debug,
            "avatar_parameters": None,
            "parameter_debug": None,
            "template": None,
            "confidence": None,
            "all_scores": None,
            "slider_init": None,
        }
        result_path = out / "pipeline_result.json"
        result_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"[Pipeline] result saved: {result_path}")
        return output

    # Stage 5: Template selection
    result = select_template(fv)

    # Stage 6: Slider initialization
    avatar_parameters, parameter_debug = apply_specs(avatar_keys, raw=raw_out)
    print(
        f"[Stage 5] template={result.template_name} "
        f"confidence={result.confidence:.3f} "
        f"scores={result.all_scores}"
    )
    print(f"[Stage 6] slider init={result.slider_init}")

    output = {
        "status": "ok",
        "glb_path": glb_path,
        "renders": render_paths,
        "feature_vector": fv.to_dict(),
        "feature_source": feature_source,
        "feature_debug": feature_debug,
        "avatar_parameters": avatar_parameters,
        "parameter_debug": parameter_debug,
        "template": result.template_name,
        "confidence": result.confidence,
        "all_scores": result.all_scores,
        "slider_init": result.slider_init,
    }

    result_path = out / "pipeline_result.json"
    result_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"[Pipeline] result saved: {result_path}")

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Full avatar pipeline: Image -> 3D -> Render -> Feature Extraction"
    )
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument(
        "--provider", default="meshy", choices=["varco", "meshy"],
        help="3D API provider (default: meshy)"
    )
    parser.add_argument("--api-key", default="", help="API key for the provider")
    parser.add_argument(
        "--skip-3d", action="store_true",
        help="Skip 3D generation and rendering (use original image only)"
    )
    parser.add_argument(
        "--existing-glb", default=None,
        help="Path to existing GLB file (skip generation, still render)"
    )
    args = parser.parse_args()

    # Resolve api-key from args or environment
    api_key = args.api_key or os.environ.get("VARCO_API_KEY", "")
    provider = args.provider or os.environ.get("VARCO_PROVIDER", "meshy")

    if not os.path.isfile(args.image):
        print(f"[Pipeline] Error: image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    result = run_pipeline(
        image_path=args.image,
        output_dir=args.output_dir,
        provider=provider,
        api_key=api_key,
        skip_3d=args.skip_3d,
        existing_glb=args.existing_glb,
    )

    print(f"\n[Pipeline] Done. status={result['status']}")
    if result["status"] == "ok":
        print(f"  template: {result['template']}")
        print(f"  confidence: {result['confidence']:.3f}")
        if result.get("glb_path"):
            print(f"  glb: {result['glb_path']}")
    else:
        print(f"  error: {result.get('error', 'unknown')}")


if __name__ == "__main__":
    main()
