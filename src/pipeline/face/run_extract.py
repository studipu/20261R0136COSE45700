"""Face feature extraction CLI wrapper.

Called by the Next.js API route:
    python run_extract.py --image <path> --output <path>

Writes a JSON file with avatar_parameters, template, confidence, etc.

When the ADF server is unavailable, falls back to kanosawa 24-point
landmarks (--landmarks flag) converted to ADF 28-point format.
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pupil_detector import extract_features_with_pupils
from parameter_specs import apply_specs, PARAMETER_SPECS
from template_selector import select_template
from avatar_keys import compute_avatar_keys, apply_gemini_face_corrections
from feature_extractor import _compute_features, _to_bgr, ADF_KP_GROUPS
from kanosawa_converter import (
    kanosawa_to_adf,
    kanosawa_pupil_centers,
    load_kanosawa_landmarks,
)

# Kanosawa landmarks are less precise than ADF (24-pt vs 28-pt, weaker model).
# Damping compresses avatar keys towards neutral to avoid extreme values.
_KANOSAWA_DAMPING = 0.55


def _apply_kanosawa_damping(avatar_keys: dict) -> dict:
    """Compress avatar keys towards each parameter's range midpoint."""
    result = avatar_keys.copy()
    for key_id, spec in PARAMETER_SPECS.items():
        if key_id not in result:
            continue
        lo, hi = spec["range"]
        neutral = (lo + hi) / 2.0
        result[key_id] = neutral + (result[key_id] - neutral) * _KANOSAWA_DAMPING
    return result


def _run_kanosawa_fallback(image_path: str, landmarks_path: str):
    """
    Fallback pipeline using kanosawa 24-pt landmarks when ADF is unavailable.

    Returns (fv, avatar_keys, raw_out) matching extract_features_with_pupils().
    """
    kano_lms = load_kanosawa_landmarks(landmarks_path)
    if kano_lms is None or len(kano_lms) < 24:
        print("[FacePipeline] Kanosawa landmarks invalid or missing")
        return None, None, None

    # Convert to ADF 28-point format (includes landmark repair)
    adf_kps = kanosawa_to_adf(kano_lms)
    print(f"[FacePipeline] Converted kanosawa 24-pt → ADF 28-pt")

    # Build groups dict (same structure as feature_extractor._run_adf)
    lm_px = [(float(p[0]), float(p[1])) for p in adf_kps]
    groups = {r: [lm_px[i] for i in idx] for r, idx in ADF_KP_GROUPS.items()}

    # Compute FaceFeatureVector (for template selection)
    fv = _compute_features(groups)

    # Use kanosawa eye-center points as pupil estimate
    manual = kanosawa_pupil_centers(kano_lms)

    # Compute avatar keys
    img_bgr = _to_bgr(image_path)
    raw_out: dict = {}
    avatar_keys = compute_avatar_keys(
        lm_px, manual=manual, _raw_out=raw_out, img_shape=img_bgr.shape[:2],
    )

    # Dampen values — kanosawa is less precise than ADF
    avatar_keys = _apply_kanosawa_damping(avatar_keys)

    # 2D input: preserve contour-based Face_Cheek value
    raw_out["Face_Cheek"] = {"value": raw_out.get("Face_Cheek"), "source": "2d_contour"}

    return fv, avatar_keys, raw_out


def main():
    parser = argparse.ArgumentParser(description="Extract face features → avatar keys")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--features", default=None,
                        help="Optional Gemini features.json for face shape correction")
    parser.add_argument("--landmarks", default=None,
                        help="Optional kanosawa landmarks.json as ADF fallback")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        result = {"status": "error", "error": f"이미지 파일을 찾을 수 없습니다: {args.image}"}
        with open(args.output, "w") as f:
            json.dump(result, f, ensure_ascii=False)
        return

    # Try ADF first
    fv, avatar_keys, raw_out = extract_features_with_pupils(args.image)

    # Fallback to kanosawa if ADF failed and landmarks are provided
    if fv is None and args.landmarks and os.path.isfile(args.landmarks):
        print("[FacePipeline] ADF unavailable, falling back to kanosawa landmarks")
        fv, avatar_keys, raw_out = _run_kanosawa_fallback(args.image, args.landmarks)

    if fv is None:
        result = {"status": "error", "error": "얼굴을 감지하지 못했습니다"}
    else:
        # Gemini 얼굴 형태 보정 적용 (features.json이 제공된 경우)
        if args.features and os.path.isfile(args.features):
            try:
                with open(args.features, "r", encoding="utf-8") as f:
                    gemini_features = json.load(f)
                avatar_keys = apply_gemini_face_corrections(avatar_keys, gemini_features)
                print(f"[FacePipeline] Gemini face corrections applied")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[FacePipeline] Gemini features read failed, skipping correction: {e}")

        avatar_parameters, parameter_debug = apply_specs(avatar_keys, raw=raw_out)
        tmpl = select_template(fv)
        result = {
            "status": "ok",
            "feature_vector": fv.to_dict(),
            "avatar_parameters": avatar_parameters,
            "parameter_debug": parameter_debug,
            "template": tmpl.template_name,
            "confidence": tmpl.confidence,
            "all_scores": tmpl.all_scores,
            "slider_init": tmpl.slider_init,
        }

    with open(args.output, "w") as f:
        json.dump(result, f, ensure_ascii=False)

    print(f"[FacePipeline] Result written to {args.output} (status: {result['status']})")


if __name__ == "__main__":
    main()
