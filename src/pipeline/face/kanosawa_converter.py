"""
Kanosawa CFA 24-point → ADF 28-point landmark converter.

When the ADF server is unavailable (macOS, no WSL), the texture pipeline
already extracts kanosawa 24-point landmarks.  This module converts them
to the ADF 28-point format so the same avatar-key computation pipeline
can run without modification.

Kanosawa CFA 24-point layout (checkpoint_landmark_191116):
   0: face contour right  (image-left,  smaller x)
   1: chin bottom
   2: face contour left   (image-right, larger  x)
   3: right eyebrow outer
   4: right eyebrow center
   5: right eyebrow inner
   6: left  eyebrow inner
   7: left  eyebrow center
   8: left  eyebrow outer
   9: nose tip
  10: right eye outer corner
  11: right eye top
  12: right eye inner corner
  13: right eye bottom
  14: right eye center (pupil)      ← bonus, not in ADF
  15: left  eye inner corner
  16: left  eye top
  17: left  eye outer corner
  18: left  eye bottom
  19: left  eye center (pupil)      ← bonus, not in ADF
  20: mouth left  corner
  21: mouth top   center
  22: mouth right corner
  23: mouth bottom center

ADF 28-point layout:
   0-4:   face contour  [left_edge, left_jaw, chin, right_jaw, right_edge]
   5-7:   right brow    [outer, mid, inner]
   8-10:  left  brow    [inner, mid, outer]
  11-16:  right eye     upper(outer,mid,inner) + lower(outer,mid,inner)
  17-22:  left  eye     upper(inner,mid,outer) + lower(inner,mid,outer)
  23:     nose tip
  24-27:  mouth         [left_corner, top, right_corner, bottom]
"""

from __future__ import annotations

import json
from pathlib import Path


def _mid(a: list, b: list) -> list:
    return [(a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0]


def _mirror_point(pt: list, center_x: float) -> list:
    """Mirror a point horizontally around center_x."""
    return [2.0 * center_x - pt[0], pt[1]]


def _repair_landmarks(k: list) -> list:
    """
    Detect and repair common kanosawa landmark errors caused by
    hair occlusion or cascade fallback.

    Repairs:
    1. Asymmetric eyes — mirror the better-detected eye
    2. Misordered brows — fix outer-inside-inner anomalies
    3. Off-center nose — recompute from eye midpoints
    4. Degenerate mouth — estimate from chin/jaw
    """
    k = [list(p) for p in k]  # deep copy

    # Face center x from jaw/chin
    center_x = (k[0][0] + k[2][0]) / 2.0

    # ── 1. Eye symmetry repair ────────────────────────────────────────
    r_eye_w = abs(k[12][0] - k[10][0])
    l_eye_w = abs(k[17][0] - k[15][0])
    eye_ratio = max(r_eye_w, l_eye_w) / max(min(r_eye_w, l_eye_w), 1.0)

    if eye_ratio > 1.8:
        if r_eye_w > l_eye_w:
            # Right eye is better — mirror to left
            l_center_x = (k[15][0] + k[17][0]) / 2.0
            r_center_x = (k[10][0] + k[12][0]) / 2.0
            for ri, li in [(10, 17), (11, 16), (12, 15), (13, 18), (14, 19)]:
                offset_x = k[ri][0] - r_center_x
                offset_y = k[ri][1] - ((k[10][1] + k[12][1]) / 2.0)
                l_base_y = (k[15][1] + k[17][1]) / 2.0
                k[li] = [l_center_x - offset_x, l_base_y + offset_y]
        else:
            # Left eye is better — mirror to right
            l_center_x = (k[15][0] + k[17][0]) / 2.0
            r_center_x = (k[10][0] + k[12][0]) / 2.0
            for ri, li in [(10, 17), (11, 16), (12, 15), (13, 18), (14, 19)]:
                offset_x = k[li][0] - l_center_x
                offset_y = k[li][1] - ((k[15][1] + k[17][1]) / 2.0)
                r_base_y = (k[10][1] + k[12][1]) / 2.0
                k[ri] = [r_center_x - offset_x, r_base_y + offset_y]
        print(f"[kanosawa_repair] Eye asymmetry {eye_ratio:.1f}x → mirrored better eye")

    # ── 2. Brow ordering repair ───────────────────────────────────────
    # Right brow: k[3] outer (smaller x) → k[5] inner (larger x)
    if k[3][0] > k[5][0]:
        k[3], k[5] = k[5], k[3]
    # Left brow: k[6] inner (smaller x) → k[8] outer (larger x)
    if k[6][0] > k[8][0]:
        k[6], k[8] = k[8], k[6]
    # If left brow outer is inside eye region, estimate from right brow
    r_brow_span = k[5][0] - k[3][0]
    if k[8][0] < k[6][0] + r_brow_span * 0.3:
        k[8] = _mirror_point(k[3], center_x)
        k[7] = _mirror_point(k[4], center_x)
        k[6] = _mirror_point(k[5], center_x)
        print("[kanosawa_repair] Left brow misordered → mirrored from right")

    # ── 3. Nose position repair ───────────────────────────────────────
    r_inner_x = k[12][0]
    l_inner_x = k[15][0]
    nose_expected_x = (r_inner_x + l_inner_x) / 2.0
    if abs(k[9][0] - nose_expected_x) > abs(l_inner_x - r_inner_x) * 0.5:
        # Nose is outside the interocular region — recompute
        eye_bottom_y = max(k[13][1], k[18][1])
        k[9] = [nose_expected_x, eye_bottom_y + (k[1][1] - eye_bottom_y) * 0.3]
        print("[kanosawa_repair] Nose off-center → repositioned between eyes")

    # ── 4. Degenerate mouth repair ────────────────────────────────────
    mouth_xs = [k[i][0] for i in (20, 21, 22, 23)]
    mouth_spread = max(mouth_xs) - min(mouth_xs)
    if mouth_spread < 10.0:
        # Mouth points collapsed — estimate from face geometry
        nose_y = k[9][1]
        chin_y = k[1][1]
        mouth_y = nose_y + (chin_y - nose_y) * 0.45
        mouth_half_w = abs(k[12][0] - k[10][0]) * 0.6  # ~60% of eye width
        k[20] = [center_x - mouth_half_w, mouth_y]
        k[21] = [center_x, mouth_y - 3.0]
        k[22] = [center_x + mouth_half_w, mouth_y]
        k[23] = [center_x, mouth_y + 5.0]
        print("[kanosawa_repair] Mouth degenerate → estimated from face geometry")

    return k


def kanosawa_to_adf(landmarks_24: list) -> list:
    """
    Convert kanosawa 24-point landmarks to ADF 28-point format.

    Key difference: kanosawa face contour points (0, 2) are at JAW level,
    but ADF face edges (0, 4) are at the WIDEST face point (temple/cheek).
    We estimate face edges from brow/eye outer endpoints, and map
    kanosawa jaw points to ADF jaw slots (1, 3).

    Eye corner points are duplicated for upper/lower lid endpoints
    (corners are where upper and lower lids meet — geometrically identical).

    Args:
        landmarks_24: list of 24 [x, y] pairs.

    Returns:
        list of 28 [x, y] pairs in ADF format.
    """
    k = _repair_landmarks(landmarks_24)
    adf: list = [None] * 28

    # ── Face contour: 3 → 5 ───────────────────────────────────────────
    # Kanosawa k[0], k[2] = jaw points → ADF[1], ADF[3]
    # ADF[0], ADF[4] = face edges (wider) → estimate from brow/eye outers
    adf[1] = list(k[0])                  # right jaw  (image left)
    adf[2] = list(k[1])                  # chin
    adf[3] = list(k[2])                  # left  jaw  (image right)

    # Estimate face edges from outermost feature points
    right_x = min(k[3][0], k[10][0])     # right brow outer or eye outer
    left_x  = max(k[8][0], k[17][0])     # left  brow outer or eye outer
    feature_span = left_x - right_x
    margin = feature_span * 0.08         # face slightly wider than features

    # Face edges at roughly brow-to-eye level
    brow_y = (k[4][1] + k[7][1]) / 2.0  # avg brow center y
    chin_y = k[1][1]
    edge_y = brow_y + (chin_y - brow_y) * 0.20

    adf[0] = [right_x - margin, edge_y]  # right face edge (image left)
    adf[4] = [left_x + margin, edge_y]   # left  face edge (image right)

    # ── Brows: direct 3+3 ─────────────────────────────────────────────
    adf[5] = list(k[3])                  # right brow outer
    adf[6] = list(k[4])                  # right brow mid
    adf[7] = list(k[5])                  # right brow inner
    adf[8] = list(k[6])                  # left  brow inner
    adf[9] = list(k[7])                  # left  brow mid
    adf[10] = list(k[8])                 # left  brow outer

    # ── Right eye: 5 → 6 (corner duplication) ─────────────────────────
    adf[11] = list(k[10])                # upper outer  = outer corner
    adf[12] = list(k[11])                # upper mid    = top
    adf[13] = list(k[12])                # upper inner  = inner corner
    adf[14] = list(k[10])                # lower outer  = outer corner (same)
    adf[15] = list(k[13])                # lower mid    = bottom
    adf[16] = list(k[12])                # lower inner  = inner corner (same)

    # ── Left eye: 5 → 6 (corner duplication) ──────────────────────────
    adf[17] = list(k[15])                # upper inner  = inner corner
    adf[18] = list(k[16])                # upper mid    = top
    adf[19] = list(k[17])                # upper outer  = outer corner
    adf[20] = list(k[15])                # lower inner  = inner corner (same)
    adf[21] = list(k[18])                # lower mid    = bottom
    adf[22] = list(k[17])                # lower outer  = outer corner (same)

    # ── Nose ───────────────────────────────────────────────────────────
    adf[23] = list(k[9])                 # nose tip

    # ── Mouth: direct 4 → 4 ───────────────────────────────────────────
    adf[24] = list(k[20])                # left  corner
    adf[25] = list(k[21])                # top   center
    adf[26] = list(k[22])                # right corner
    adf[27] = list(k[23])                # bottom center

    return adf


def kanosawa_pupil_centers(landmarks_24: list) -> dict | None:
    """
    Extract pupil center coordinates from kanosawa landmarks.

    Kanosawa indices 14 (right eye center) and 19 (left eye center)
    provide a direct pupil position estimate.  Returns a manual dict
    compatible with ``pupil_detector.detect_pupils()`` output format,
    or None if the points look degenerate.
    """
    k = landmarks_24
    r_center = k[14]
    l_center = k[19]

    # Estimate radius from eye dimensions
    r_eye_w = abs(k[12][0] - k[10][0])
    r_eye_h = abs(k[13][1] - k[11][1])
    l_eye_w = abs(k[17][0] - k[15][0])
    l_eye_h = abs(k[18][1] - k[16][1])

    if r_eye_w < 2 or l_eye_w < 2:
        return None

    r_radius = min(r_eye_w, r_eye_h) * 0.35
    l_radius = min(l_eye_w, l_eye_h) * 0.35

    return {
        "R_PL": (r_center[0] - r_radius, r_center[1]),
        "R_PR": (r_center[0] + r_radius, r_center[1]),
        "R_PT": (r_center[0], r_center[1] - r_radius),
        "R_PB": (r_center[0], r_center[1] + r_radius),
        "L_PL": (l_center[0] - l_radius, l_center[1]),
        "L_PR": (l_center[0] + l_radius, l_center[1]),
        "L_PT": (l_center[0], l_center[1] - l_radius),
        "L_PB": (l_center[0], l_center[1] + l_radius),
    }


def load_kanosawa_landmarks(json_path: str) -> list | None:
    """
    Load kanosawa landmarks from JSON file produced by extract_landmarks.py.

    Returns the first face's 24-point landmark list, or None on failure.
    """
    try:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        if not data or not isinstance(data, list):
            return None
        # Take the first (or largest) face
        if len(data) == 1:
            return data[0].get("landmarks")
        # Multiple faces: pick the one with largest bounding-box area
        best = max(data, key=lambda f: f["bbox"][2] * f["bbox"][3])
        return best.get("landmarks")
    except Exception as exc:
        print(f"[kanosawa_converter] Failed to load {json_path}: {exc}")
        return None
