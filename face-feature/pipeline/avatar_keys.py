"""
Avatar key computation — ADF 28-pt landmarks → 29 Key_IDs.

All keys are normalized to [-1, 1] or [0, 1] via _map_signed / _map_01.
lo/hi calibration ranges were derived from 26 anime face images (5th–95th percentile).

Keys with structural limitations (fixed/proxy values):
  Eye_TopLidDown / Eye_LowerLidUp : proxy (ADF 3-pt lid insufficient)
  Brow_WidthV                     : 0.0   (no brow thickness in ADF)
  Nose_Width                      : 0.5   (no ala landmarks in ADF)
  Face_Cheek                      : 0.0 when no side depth available
"""

import numpy as np

from .geometry import (
    _EPS,
    _map_signed, _map_signed_asym, _map_01,
    _angle_at,
    _lid_flatness,
    _compute_depth_features,
    _map_01 as map_01,
)


def compute_avatar_keys(
    kps: list,
    manual: "dict | None" = None,
    _raw_out: "dict | None" = None,
    depth: "np.ndarray | None" = None,
    img_shape: "tuple | None" = None,
) -> dict[str, float]:
    """
    Compute all 29 avatar Key_IDs from ADF 28-pt keypoints.

    kps       : list of 28 (x, y) tuples, image coordinates (y down).
    manual    : optional pupil points {R_PL, R_PR, L_PL, L_PR, R_PT, R_PB, L_PT, L_PB}.
    _raw_out  : if provided, raw (un-normalized) values are written here.
    depth     : optional pyrender depth array (float32, smaller = closer).
    img_shape : (H, W) required when depth is provided.
    """
    def p(i):
        return np.array(kps[i], dtype=float)

    def d(a, b):
        return float(np.linalg.norm(np.array(a, dtype=float) - np.array(b, dtype=float)))

    def mid(a, b):
        return (np.array(a, dtype=float) + np.array(b, dtype=float)) / 2.0

    # ── Section 2: face scale ─────────────────────────────────────────────
    F0, F1, F2, F3, F4 = [p(i) for i in range(5)]
    face_width        = d(F0, F4)
    lower_face_height = d(mid(F0, F4), F2)
    face_scale        = max(0.75 * face_width + 0.25 * lower_face_height, _EPS)

    # ── Section 3: eye points (kp11-22) ──────────────────────────────────
    R_eye_left    = p(11);  R_eye_mid_u = p(12);  R_eye_right   = p(13)
    R_eye_left_l  = p(14);  R_eye_mid_l = p(15);  R_eye_right_l = p(16)
    L_eye_left    = p(17);  L_eye_mid_u = p(18);  L_eye_right   = p(19)
    L_eye_left_l  = p(20);  L_eye_mid_l = p(21);  L_eye_right_l = p(22)

    R_left_corner  = mid(R_eye_left,  R_eye_left_l)
    R_right_corner = mid(R_eye_right, R_eye_right_l)
    L_left_corner  = mid(L_eye_left,  L_eye_left_l)
    L_right_corner = mid(L_eye_right, L_eye_right_l)

    R_inner = R_right_corner
    R_outer = R_left_corner
    L_inner = L_left_corner
    L_outer = L_right_corner

    R_eye_w = d(R_left_corner, R_right_corner)
    L_eye_w = d(L_left_corner, L_right_corner)

    R_eye_h = max(float(
        max(R_eye_left_l[1], R_eye_mid_l[1], R_eye_right_l[1])
        - min(R_eye_left[1], R_eye_mid_u[1], R_eye_right[1])
    ), _EPS)
    L_eye_h = max(float(
        max(L_eye_left_l[1], L_eye_mid_l[1], L_eye_right_l[1])
        - min(L_eye_left[1], L_eye_mid_u[1], L_eye_right[1])
    ), _EPS)

    R_center   = mid(R_left_corner, R_right_corner)
    L_center   = mid(L_left_corner, L_right_corner)
    eye_center = mid(R_center, L_center)

    # ── Section 4: Eye keys ───────────────────────────────────────────────
    _rv = (R_eye_w + L_eye_w) / 2.0 / face_scale
    Eye_Width = _map_signed(_rv, 0.2284, 0.2664)
    if _raw_out is not None: _raw_out["Eye_Width"] = _rv

    _rv = (R_eye_h + L_eye_h) / 2.0 / face_scale
    Eye_WidthV = _map_signed(_rv, 0.1049, 0.2258)
    if _raw_out is not None: _raw_out["Eye_WidthV"] = _rv

    face_mid_y = float((mid(F0, F4)[1] + F2[1]) / 2.0)
    _rv = (face_mid_y - float(eye_center[1])) / face_scale
    Eye_Height = _map_signed(_rv, 0.2633, 0.3186)
    if _raw_out is not None: _raw_out["Eye_Height"] = _rv

    _rv = d(R_inner, L_inner) / face_scale
    Eye_Dist = _map_signed(_rv, 0.3466, 0.3925)
    if _raw_out is not None: _raw_out["Eye_Dist"] = _rv

    # outer_y - inner_y: positive = outer lower (drooping tail), negative = outer higher (upward tail)
    # Both eyes use same semantic direction to avoid mirror-sign cancellation
    R_rot_slope = (float(R_outer[1]) - float(R_inner[1])) / max(R_eye_w, _EPS)
    L_rot_slope = (float(L_outer[1]) - float(L_inner[1])) / max(L_eye_w, _EPS)
    _rv = (R_rot_slope + L_rot_slope) / 2.0
    Eye_Rot = float(max(-1.0, min(1.0, _rv / 0.35)))
    if _raw_out is not None: _raw_out["Eye_Rot"] = _rv

    R_mid_y = float(R_center[1])
    L_mid_y = float(L_center[1])
    _rv = (
        ((R_mid_y - float(R_inner[1])) / R_eye_h
         + (L_mid_y - float(L_inner[1])) / L_eye_h) / 2.0
    )
    Eye_FrontHeight = _map_signed(_rv, -0.1349, 0.0697)
    if _raw_out is not None: _raw_out["Eye_FrontHeight"] = _rv

    _rv = (
        ((R_mid_y - float(R_outer[1])) / R_eye_h
         + (L_mid_y - float(L_outer[1])) / L_eye_h) / 2.0
    )
    Eye_TailHeight = _map_signed(_rv, -0.0697, 0.1349)
    if _raw_out is not None: _raw_out["Eye_TailHeight"] = _rv

    R_front_angle = _angle_at(R_eye_mid_u, R_inner, R_eye_mid_l)
    L_front_angle = _angle_at(L_eye_mid_u, L_inner, L_eye_mid_l)
    _rv = (R_front_angle + L_front_angle) / 2.0
    Eye_FrontFlat = _map_01(_rv, 40.4647, 83.5102)
    if _raw_out is not None: _raw_out["Eye_FrontFlat"] = _rv

    Eye_TopLidFlat = float(
        (_lid_flatness(R_left_corner, R_right_corner, R_eye_mid_u, R_eye_h)
         + _lid_flatness(L_left_corner, L_right_corner, L_eye_mid_u, L_eye_h)) / 2.0
    )
    Eye_LowerLidFlat = float(
        (_lid_flatness(R_left_corner, R_right_corner, R_eye_mid_l, R_eye_h)
         + _lid_flatness(L_left_corner, L_right_corner, L_eye_mid_l, L_eye_h)) / 2.0
    )
    if _raw_out is not None:
        _raw_out["Eye_TopLidFlat"]   = Eye_TopLidFlat
        _raw_out["Eye_LowerLidFlat"] = Eye_LowerLidFlat

    R_center_opening = d(R_eye_mid_u, R_eye_mid_l) / max(R_eye_w, _EPS)
    L_center_opening = d(L_eye_mid_u, L_eye_mid_l) / max(L_eye_w, _EPS)
    opening = (R_center_opening + L_center_opening) / 2.0
    if _raw_out is not None: _raw_out["Eye_TopLidDown"] = opening
    Eye_TopLidDown = float(max(0.0, min(1.0, (0.35 - opening) / 0.25)))
    Eye_LowerLidUp = Eye_TopLidDown

    if manual and all(k in manual for k in ("R_PL", "R_PR", "L_PL", "L_PR")):
        pupil_w_raw = (
            d(manual["R_PL"], manual["R_PR"]) / max(R_eye_w, _EPS)
            + d(manual["L_PL"], manual["L_PR"]) / max(L_eye_w, _EPS)
        ) / 2.0
        Eye_PupilWidth = _map_signed(pupil_w_raw, 0.25, 0.80)
    else:
        Eye_PupilWidth = 0.0

    if manual and all(k in manual for k in ("R_PT", "R_PB", "L_PT", "L_PB")):
        pupil_h_raw = (
            d(manual["R_PT"], manual["R_PB"]) / max(R_eye_h, _EPS)
            + d(manual["L_PT"], manual["L_PB"]) / max(L_eye_h, _EPS)
        ) / 2.0
        Eye_PupilWidthV = _map_signed(pupil_h_raw, 0.25, 0.80)
    else:
        Eye_PupilWidthV = Eye_PupilWidth

    # ── Section 5: Brow keys (kp5-10) ────────────────────────────────────
    R_brow_outer = p(5);  R_brow_mid = p(6);  R_brow_inner = p(7)
    L_brow_inner = p(8);  L_brow_mid = p(9);  L_brow_outer = p(10)

    R_brow_w = d(R_brow_outer, R_brow_inner)
    L_brow_w = d(L_brow_inner, L_brow_outer)

    _rv = d(R_brow_inner, L_brow_inner) / face_scale
    Brow_Dist = _map_signed(_rv, 0.2577, 0.4451)
    if _raw_out is not None: _raw_out["Brow_Dist"] = _rv

    _rv = ((R_center[1] - R_brow_mid[1]) + (L_center[1] - L_brow_mid[1])) / 2.0 / face_scale
    Brow_Height = _map_signed(_rv, 0.1950, 0.3920)
    if _raw_out is not None: _raw_out["Brow_Height"] = _rv

    # outer_y - inner_y: same semantic direction for both brows (mirror-sign fix)
    R_brow_slope = (float(R_brow_outer[1]) - float(R_brow_inner[1])) / max(R_brow_w, _EPS)
    L_brow_slope = (float(L_brow_outer[1]) - float(L_brow_inner[1])) / max(L_brow_w, _EPS)
    _rv = (R_brow_slope + L_brow_slope) / 2.0
    Brow_Rot = float(max(-1.0, min(1.0, _rv / 0.50)))
    if _raw_out is not None: _raw_out["Brow_Rot"] = _rv

    _rv = (R_brow_w + L_brow_w) / 2.0 / face_scale
    Brow_Width = _map_signed(_rv, 0.2056, 0.3709)
    if _raw_out is not None: _raw_out["Brow_Width"] = _rv

    Brow_WidthV = 0.0

    # ── Section 6: Nose keys (kp23) ───────────────────────────────────────
    N         = p(23)
    mouth_ctr = mid(p(24), p(26))
    eye_y     = float(eye_center[1])
    mouth_y   = float(mouth_ctr[1])

    _rv = (float(N[1]) - eye_y) / max(mouth_y - eye_y, _EPS)
    Nose_Height = _map_signed(_rv, 0.4484, 0.5830)
    if _raw_out is not None: _raw_out["Nose_Height"] = _rv
    Nose_Width = 0.5

    _rv = (float(p(25)[1]) - float(N[1])) / face_scale
    Nose_UnderNose = _map_signed(_rv, 0.1294, 0.1920)
    if _raw_out is not None: _raw_out["Nose_UnderNose"] = _rv

    # ── Section 7: Mouth keys (kp24-27) ──────────────────────────────────
    M_L = p(24);  M_U = p(25);  M_R = p(26);  M_D = p(27)
    M_C          = mid(M_U, M_D)
    M_corner_mid = mid(M_L, M_R)

    _rv = d(M_L, M_R) / face_scale
    Mouth_Width = _map_signed_asym(
        _rv, 0.1980, 0.3520, pivot=0.48, gamma_lo=0.72, gamma_hi=1.75
    )
    if _raw_out is not None: _raw_out["Mouth_Width"] = _rv

    _rv = float(M_corner_mid[1] - eye_center[1]) / face_scale
    Mouth_Height = -_map_signed(_rv, 0.2615, 0.3920)
    if _raw_out is not None: _raw_out["Mouth_Height"] = _rv

    _rv = (float(M_C[1]) - float((M_L[1] + M_R[1]) / 2.0)) / face_scale
    Mouth_Corner = _map_signed(_rv, 0.0099, 0.0594)
    if _raw_out is not None: _raw_out["Mouth_Corner"] = _rv

    # ── Section 8: Face keys (kp0-4) ─────────────────────────────────────
    jaw_width        = d(F1, F3)
    chin_width_ratio = jaw_width / max(face_width, _EPS)
    chin_angle       = _angle_at(F1, F2, F3)
    jaw_mid          = mid(F1, F3)
    chin_depth       = d(jaw_mid, F2)
    chin_depth_ratio = chin_depth / max(face_width, _EPS)
    width_height_ratio = face_width / max(lower_face_height, _EPS)

    angle_score = float(max(0.0, min(1.0, (130.0 - chin_angle)      / (130.0 - 60.0))))
    width_score = float(max(0.0, min(1.0, (0.55 - chin_width_ratio) / (0.55 - 0.25))))
    depth_score = float(max(0.0, min(1.0, (chin_depth_ratio - 0.08) / (0.25 - 0.08))))
    Face_JawLine = float(max(0.0, min(1.0,
        0.5 * angle_score + 0.3 * width_score + 0.2 * depth_score
    )))

    _rv = float((face_width - jaw_width) / max(face_width, _EPS))
    Face_Cheek = _map_01(_rv, 0.2293, 0.2872)
    if _raw_out is not None: _raw_out["Face_Cheek"] = _rv

    _r_wh = _map_01(width_height_ratio, 1.0, 1.8)
    _r_ca = _map_01(chin_angle, 80.0, 140.0)
    _r_cd = 1.0 - _map_01(chin_depth_ratio, 0.08, 0.25)
    Face_Roundness = float(max(0.0, min(1.0, 0.45 * _r_wh + 0.35 * _r_ca + 0.20 * _r_cd)))

    _rv = chin_width_ratio
    Face_ChinWidth = _map_01(_rv, 0.7128, 0.7707)
    if _raw_out is not None: _raw_out["Face_ChinWidth"] = _rv

    if _raw_out is not None:
        _raw_out["Face_JawLine"]   = Face_JawLine
        _raw_out["Face_Roundness"] = {
            "value": Face_Roundness,
            "width_height": round(_r_wh, 4),
            "chin_angle":   round(_r_ca, 4),
            "chin_depth":   round(_r_cd, 4),
        }

    # ── Depth override ────────────────────────────────────────────────────
    if depth is not None and img_shape is not None:
        ih, iw = img_shape
        _d_nose, _ = _compute_depth_features(depth, kps, ih, iw)
        if _d_nose is not None:
            Nose_Height = _map_signed(_d_nose, 0.02, 0.11)
            if _raw_out is not None: _raw_out["Nose_Height"] = _d_nose

    return {
        "Eye_Width":        Eye_Width,
        "Eye_WidthV":       Eye_WidthV,
        "Eye_Height":       Eye_Height,
        "Eye_Dist":         Eye_Dist,
        "Eye_Rot":          Eye_Rot,
        "Eye_FrontHeight":  Eye_FrontHeight,
        "Eye_FrontFlat":    Eye_FrontFlat,
        "Eye_TailHeight":   Eye_TailHeight,
        "Eye_TopLidFlat":   Eye_TopLidFlat,
        "Eye_LowerLidFlat": Eye_LowerLidFlat,
        "Eye_TopLidDown":   Eye_TopLidDown,
        "Eye_LowerLidUp":   Eye_LowerLidUp,
        "Eye_PupilWidth":   Eye_PupilWidth,
        "Eye_PupilWidthV":  Eye_PupilWidthV,
        "Brow_Dist":        Brow_Dist,
        "Brow_Height":      Brow_Height,
        "Brow_Rot":         Brow_Rot,
        "Brow_Width":       Brow_Width,
        "Brow_WidthV":      Brow_WidthV,
        "Nose_Height":      Nose_Height,
        "Nose_Width":       Nose_Width,
        "Nose_UnderNose":   Nose_UnderNose,
        "Mouth_Width":      Mouth_Width,
        "Mouth_Height":     Mouth_Height,
        "Mouth_Corner":     Mouth_Corner,
        "Face_JawLine":     Face_JawLine,
        "Face_Cheek":       Face_Cheek,
        "Face_Roundness":   Face_Roundness,
        "Face_ChinWidth":   Face_ChinWidth,
    }
