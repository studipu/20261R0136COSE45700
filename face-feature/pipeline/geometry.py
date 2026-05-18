"""
Geometry helpers and depth-based feature computation.

Pure math utilities used by avatar_keys.py:
  - Normalization: _map_signed, _map_01
  - Angle/line:    _angle_deg, _angle_at, _line_y_at
  - Eye shape:     _lid_flatness
  - Depth:         _sample_depth, _compute_depth_features, _compute_cheek_from_side
"""

import numpy as np

_EPS = 1e-6


def _map_signed(x: float, lo: float, hi: float) -> float:
    """Normalize x to [-1, 1] given [lo, hi] range."""
    return float(max(-1.0, min(1.0, 2.0 * (x - lo) / (hi - lo + _EPS) - 1.0)))


def _map_01(x: float, lo: float, hi: float) -> float:
    """Normalize x to [0, 1] given [lo, hi] range."""
    return float(max(0.0, min(1.0, (x - lo) / (hi - lo + _EPS))))


def _angle_deg(a, b) -> float:
    """Angle of line from a to b in degrees."""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    return float(np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0])))


def _angle_at(a, b, c) -> float:
    """Angle at vertex b in triangle abc, in degrees."""
    a, b, c = np.array(a, dtype=float), np.array(b, dtype=float), np.array(c, dtype=float)
    ba, bc = a - b, c - b
    cosv = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + _EPS)
    return float(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))))


def _line_y_at(a, b, x: float) -> float:
    """Y value on line ab at given x."""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    if abs(b[0] - a[0]) < _EPS:
        return float((a[1] + b[1]) / 2.0)
    t = (x - a[0]) / (b[0] - a[0])
    return float(a[1] + t * (b[1] - a[1]))


def _lid_flatness(corner_a, corner_b, lid_mid, eye_h: float) -> float:
    """
    1 = lid_mid lies exactly on the corner-to-corner line (flat).
    0 = maximum bulge relative to eye_h.
    """
    y_line = _line_y_at(corner_a, corner_b, float(lid_mid[0]))
    bulge  = abs(y_line - float(lid_mid[1])) / max(eye_h, _EPS)
    return float(max(0.0, min(1.0, 1.0 - bulge / 0.9)))


def _sample_depth(depth: np.ndarray, cx: float, cy: float, radius: int = 8) -> "float | None":
    """Median of valid (> 0) depth values in a disk around pixel (cx, cy)."""
    H, W = depth.shape
    x0, x1 = max(0, int(cx) - radius), min(W, int(cx) + radius + 1)
    y0, y1 = max(0, int(cy) - radius), min(H, int(cy) + radius + 1)
    patch = depth[y0:y1, x0:x1]
    valid = patch[patch > 0.0]
    return float(np.median(valid)) if len(valid) > 0 else None


def _compute_depth_features(
    depth: np.ndarray,
    kps: list,
    img_h: int,
    img_w: int,
) -> "tuple[float | None, float | None]":
    """
    Compute nose protrusion from a front-view depth map.
    depth: pyrender float32 (smaller = closer to camera).
    Returns (nose_raw, None) — cheek is computed separately via side-view.
    """
    dH, dW = depth.shape
    sx = dW / max(img_w, 1)
    sy = dH / max(img_h, 1)

    def sd(kx, ky, r=10):
        return _sample_depth(depth, float(kx) * sx, float(ky) * sy, r)

    d_sr = sd(kps[0][0], kps[0][1])
    d_sl = sd(kps[4][0], kps[4][1])
    if d_sr is None or d_sl is None:
        return None, None
    d_side = (d_sr + d_sl) / 2.0

    d_nose = sd(kps[23][0], kps[23][1])
    if d_nose is None or d_side <= 0.0:
        return None, None

    return (d_side - d_nose) / d_side, None


def _compute_cheek_from_side(
    side_depth: np.ndarray,
    kps: list,
    img_h: int,
) -> "float | None":
    """
    Cheek prominence from a side-view depth map.
    Returns ratio > 0 if cheek is wider than forehead.
    """
    H = side_depth.shape[0]
    sy = H / max(img_h, 1)

    def row_spread(fy: float, band: int = 12) -> "float | None":
        r0 = max(0, int(fy * sy) - band)
        r1 = min(H, int(fy * sy) + band + 1)
        strip = side_depth[r0:r1, :]
        valid = strip[strip > 0.0]
        if len(valid) < 20:
            return None
        return float(np.percentile(valid, 95) - np.percentile(valid, 5))

    brow_y  = (kps[6][1] + kps[9][1]) / 2.0
    eye_y   = ((kps[12][1] + kps[15][1]) / 2.0 + (kps[18][1] + kps[21][1]) / 2.0) / 2.0
    mouth_y = (kps[24][1] + kps[26][1]) / 2.0
    cheek_y = (eye_y + mouth_y) / 2.0

    s_cheek = row_spread(cheek_y)
    s_brow  = row_spread(brow_y)
    if s_cheek is None or s_brow is None or s_brow < _EPS:
        return None

    return s_cheek / s_brow - 1.0
