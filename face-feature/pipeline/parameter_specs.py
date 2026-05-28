"""
Avatar parameter specifications keyed by template Key_ID.

This module defines Key_ID spec metadata consumed by parameter mapping.
At runtime it is imported through parameter_mapper and contributes to
avatar_parameters / parameter_debug written in pipeline_result.json.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Dict


ParameterSpec = Dict[str, object]


def _spec(
    *,
    value_range: tuple[float, float],
    domain: str,
    source: str | None = None,
    feature: str | None = None,
    description: str,
    enabled: bool = False,
) -> ParameterSpec:
    mapping = "default"
    if enabled:
        mapping = "relative" if value_range == (-1.0, 1.0) else "strength"

    notes = (
        None
        if enabled
        else "Disabled: no reliable measurement from front-view ADF landmarks."
    )

    return {
        "range": value_range,
        "domain": domain,
        "source": source,
        "feature": feature,
        "mapping": mapping,
        "default": 0.0,
        "enabled": enabled,
        "description": description,
        "notes": notes,
    }


PARAMETER_SPECS: dict[str, ParameterSpec] = {
    # ── Eye ───────────────────────────────────────────────────────────────
    "Eye_Width": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_width_ratio", enabled=True,
        description="Horizontal eye width (avg eye_w / face_w).",
    ),
    "Eye_WidthV": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_aspect_ratio", enabled=True,
        description="Vertical eye opening (eye height / eye width).",
    ),
    "Eye_Height": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="ADF landmarks", feature="eye_to_chin_ratio", enabled=True,
        description="Eye vertical position: distance from eye center to chin / face scale.",
    ),
    "Eye_Dist": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_distance_ratio", enabled=True,
        description="Interocular distance / face_w.",
    ),
    "Eye_Rot": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_rot", enabled=True,
        description="Eye tilt (+ = outer corner lower).",
    ),
    "Eye_FrontHeight": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_front_height", enabled=True,
        description="Inner corner y relative to eye midline / eye_h.",
    ),
    "Eye_FrontFlat": _spec(
        value_range=(0.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_front_flat", enabled=True,
        description="Inner eye-corner curve relaxation proxy: inner upper/lower lid gap / eye width.",
    ),
    "Eye_TailHeight": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_tail_height", enabled=True,
        description="Outer corner y relative to eye midline / eye_h.",
    ),
    "Eye_TopLidFlat": _spec(
        value_range=(0.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_top_lid_flat", enabled=True,
        description="Upper eyelid flatness [0,1].",
    ),
    "Eye_LowerLidFlat": _spec(
        value_range=(0.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_lower_lid_flat", enabled=True,
        description="Lower eyelid flatness [0,1].",
    ),
    "Eye_TopLidDown": _spec(
        value_range=(0.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_top_lid_down", enabled=True,
        description="Upper lid droop [0,1].",
    ),
    "Eye_LowerLidUp": _spec(
        value_range=(0.0, 1.0), domain="eye",
        source="FaceFeatureVector", feature="eye_lower_lid_up", enabled=True,
        description="Lower lid upward curve [0,1].",
    ),
    "Eye_PupilWidth": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="Eye_WidthV proxy", feature="eye_width_v", enabled=True,
        description="Pupil width proxy: intentionally reuses Eye_WidthV because ADF cannot measure iris size reliably.",
    ),
    "Eye_PupilWidthV": _spec(
        value_range=(-1.0, 1.0), domain="eye",
        source="Eye_WidthV proxy", feature="eye_width_v", enabled=True,
        description="Pupil height proxy: intentionally reuses Eye_WidthV because ADF cannot measure iris size reliably.",
    ),
    # ── Brow ──────────────────────────────────────────────────────────────
    "Brow_Dist": _spec(
        value_range=(-1.0, 1.0), domain="brow",
        source="FaceFeatureVector", feature="brow_dist_ratio", enabled=True,
        description="Gap between inner brow ends / face_w.",
    ),
    "Brow_Height": _spec(
        value_range=(-1.0, 1.0), domain="brow",
        source="FaceFeatureVector", feature="brow_height_ratio", enabled=True,
        description="Brow elevation: (eye_top_y − brow_mean_y) / face_h.",
    ),
    "Brow_Rot": _spec(
        value_range=(-1.0, 1.0), domain="brow",
        source="FaceFeatureVector", feature="brow_rot", enabled=True,
        description="Brow tilt (+ = outer end lower).",
    ),
    "Brow_Width": _spec(
        value_range=(-1.0, 1.0), domain="brow",
        source="FaceFeatureVector", feature="brow_width_ratio", enabled=True,
        description="Avg brow span / face_w.",
    ),
    "Brow_WidthV": _spec(
        value_range=(-1.0, 1.0), domain="brow",
        description="Brow thickness — disabled (requires pixel analysis).",
    ),
    # ── Nose ──────────────────────────────────────────────────────────────
    "Nose_Height": _spec(
        value_range=(-1.0, 1.0), domain="nose",
        source="renderer/front_depth", feature="nose_protrusion_depth", enabled=True,
        description="Depth-based nose height/protrusion from front render depth; defaults when depth is unavailable.",
    ),
    "Nose_Width": _spec(
        value_range=(0.0, 1.0), domain="nose",
        description="Nose width fixed default 0.65 (no ala landmarks in ADF).",
    ),
    "Nose_UnderNose": _spec(
        value_range=(-1.0, 1.0), domain="nose",
        source="FaceFeatureVector", feature="nose_under_nose_ratio", enabled=True,
        description="Nose-to-upper-lip distance proxy: (mouth_top_y - nose_tip_y) / face_scale.",
    ),
    # ── Mouth ─────────────────────────────────────────────────────────────
    "Mouth_Width": _spec(
        value_range=(-1.0, 1.0), domain="mouth",
        source="FaceFeatureVector", feature="mouth_width_ratio", enabled=True,
        description="Mouth corner-to-corner / face_w.",
    ),
    "Mouth_Height": _spec(
        value_range=(-1.0, 1.0), domain="mouth",
        source="FaceFeatureVector", feature="mouth_height_ratio", enabled=True,
        description="Mouth vertical position relative to eye center; higher value means mouth is higher/closer to eyes.",
    ),
    "Mouth_Corner": _spec(
        value_range=(-1.0, 1.0), domain="mouth",
        source="FaceFeatureVector", feature="mouth_corner_ratio", enabled=True,
        description="Corner lift vs mouth center (+ = corners up).",
    ),
    # ── Face ──────────────────────────────────────────────────────────────
    "Face_JawLine": _spec(
        value_range=(0.0, 1.0), domain="face",
        source="ADF landmarks", feature="jawline_sharpness_composite", enabled=True,
        description="Jawline sharpness/V-line strength from chin angle, chin width, and chin depth.",
    ),
    "Face_Cheek": _spec(
        value_range=(0.0, 1.0), domain="face",
        source="renderer/side_depth or adf/2d_proxy", feature="cheek_prominence_raw", enabled=True,
        description="Cheek fullness: side-depth cheek prominence when available; otherwise 2D contour proxy.",
    ),
    "Face_Roundness": _spec(
        value_range=(0.0, 1.0), domain="face",
        source="ADF landmarks", feature="lower_face_roundness_composite", enabled=True,
        description="Lower-face roundness composite from face width/height, chin angle, and inverse chin depth.",
    ),
    "Face_ChinWidth": _spec(
        value_range=(0.0, 1.0), domain="face",
        source="ADF landmarks", feature="chin_width_ratio", enabled=True,
        description="Chin/jaw width ratio: F1-F3 jaw span divided by F0-F4 face width.",
    ),
}


def get_parameter_spec(key_id: str) -> dict:
    return PARAMETER_SPECS[key_id]


def iter_enabled_specs() -> Iterator[tuple[str, dict]]:
    return (
        (key_id, spec)
        for key_id, spec in PARAMETER_SPECS.items()
        if spec["enabled"]
    )


def iter_all_specs() -> Iterator[tuple[str, dict]]:
    return iter(PARAMETER_SPECS.items())


def apply_specs(
    avatar_keys: "dict[str, float]",
    raw: "dict[str, float] | None" = None,
) -> "tuple[dict[str, float], dict[str, dict]]":
    """
    Clip avatar_keys to each spec's range and build per-key debug metadata.

    Args:
        avatar_keys : normalized key values from compute_avatar_keys()
        raw         : optional pre-normalization measurements from _raw_out

    Returns:
        clipped : {key_id: float}  — values guaranteed within spec range
        debug   : {key_id: {...}}  — value, raw, source, range, enabled, clipped
    """
    clipped: dict[str, float] = {}
    debug: dict[str, dict] = {}
    for key_id, spec in PARAMETER_SPECS.items():
        normalized = float(avatar_keys.get(key_id, spec["default"]))
        lo, hi = spec["range"]
        value = float(max(lo, min(hi, normalized)))
        clipped[key_id] = value

        raw_entry = raw.get(key_id) if raw else None
        if isinstance(raw_entry, dict):
            raw_value  = raw_entry.get("value")
            source     = raw_entry.get("source") or spec.get("source")
            components = {k: v for k, v in raw_entry.items() if k not in ("value", "source")}
        else:
            raw_value  = raw_entry
            source     = spec.get("source")
            components = {}

        entry = {
            "value":       value,
            "raw":         raw_value,
            "source":      source,
            "range":       list(spec["range"]),
            "enabled":     spec["enabled"],
            "clipped":     value != normalized,
            "description": spec["description"],
        }
        entry.update(components)
        debug[key_id] = entry
    return clipped, debug
