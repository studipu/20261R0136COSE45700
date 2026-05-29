"""
OpenCV-based pupil detection for anime face images.

ADF 28-pt keypoints → eye ROI crop → HoughCircles → contour fallback
→ manual dict for compute_avatar_keys()

Public API:
    detect_pupils(img_bgr, kps) -> dict | None
    extract_features_with_pupils(image, min_confidence) -> (FaceFeatureVector | None, dict | None, dict | None)
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np

from feature_extractor import (
    _to_bgr, _run_adf, _ensure_path,
    _compute_features, FaceFeatureVector,
)
from avatar_keys import compute_avatar_keys
from geometry import _compute_cheek_from_side, _map_01

_EPS = 1e-6


def _detect_pupil_one(img_bgr: np.ndarray, upper_kps: list, lower_kps: list, pad: float = 0.5) -> "dict | None":
    """
    단일 눈 영역에서 눈동자(홍채) 검출.
    upper_kps: ADF 상단 lid 3점, lower_kps: ADF 하단 lid 3점
    Returns dict(center, left, right, top, bottom, radius) or None
    """
    all_pts = upper_kps + lower_kps
    xs = [p[0] for p in all_pts]; ys = [p[1] for p in all_pts]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    eye_w = x2 - x1 + _EPS
    eye_h = y2 - y1 + _EPS

    H, W = img_bgr.shape[:2]
    rx1 = max(0, int(x1 - eye_w * pad))
    ry1 = max(0, int(y1 - eye_h * pad))
    rx2 = min(W, int(x2 + eye_w * pad))
    ry2 = min(H, int(y2 + eye_h * pad))
    if rx2 - rx1 < 4 or ry2 - ry1 < 4:
        return None

    roi  = img_bgr[ry1:ry2, rx1:rx2]
    gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(
               cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY))

    min_r = max(2, int(min(eye_w, eye_h) * 0.15))
    max_r = max(min_r + 2, int(min(eye_w, eye_h) * 0.45))

    # ── 1차: HoughCircles ─────────────────────────────────────────────────
    circles = cv2.HoughCircles(
        cv2.GaussianBlur(gray, (3, 3), 0), cv2.HOUGH_GRADIENT,
        dp=1, minDist=rx2 - rx1,
        param1=40, param2=15,
        minRadius=min_r, maxRadius=max_r,
    )
    if circles is not None:
        c = circles[0][0]
        cx, cy, r = float(c[0]) + rx1, float(c[1]) + ry1, float(c[2])
        return _make_result(cx, cy, r)

    # ── 2차: 어두운 영역 contour centroid ────────────────────────────────
    _, dark = cv2.threshold(
        cv2.GaussianBlur(gray, (5, 5), 0), 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_r_allowed = min(eye_w, eye_h) * 0.55  # 눈 크기의 55% 이상이면 오검출
    if contours:
        candidates = []
        for cnt in contours:
            M = cv2.moments(cnt)
            if M["m00"] < 4:
                continue
            cx_r, cy_r = M["m10"] / M["m00"], M["m01"] / M["m00"]
            if (x1 - rx1) <= cx_r <= (x2 - rx1) and (y1 - ry1) <= cy_r <= (y2 - ry1):
                candidates.append((cv2.contourArea(cnt), cx_r, cy_r, cnt))
        if candidates:
            _, cx_r, cy_r, cnt = max(candidates, key=lambda t: t[0])
            _, enc_r = cv2.minEnclosingCircle(cnt)
            r = float(enc_r) * 0.5
            if r <= max_r_allowed:
                return _make_result(cx_r + rx1, cy_r + ry1, r)

    # 검출 실패 — None 반환하여 compute_avatar_keys가 proxy로 fallback
    return None


def _make_result(cx, cy, r):
    return {
        "center": (cx, cy),
        "left":   (cx - r, cy),
        "right":  (cx + r, cy),
        "top":    (cx, cy - r),
        "bottom": (cx, cy + r),
        "radius": r,
    }


def detect_pupils(img_bgr: np.ndarray, kps: list) -> "dict | None":
    """
    ADF 28-pt kps에서 양쪽 눈동자 검출.
    Returns manual dict {R_PL, R_PR, R_PT, R_PB, L_PL, L_PR, L_PT, L_PB} or None.
    """
    r = _detect_pupil_one(img_bgr, list(kps[11:14]), list(kps[14:17]))
    l = _detect_pupil_one(img_bgr, list(kps[17:20]), list(kps[20:23]))
    if r is None or l is None:
        return None
    return {
        "R_PL": r["left"],  "R_PR": r["right"],
        "R_PT": r["top"],   "R_PB": r["bottom"],
        "L_PL": l["left"],  "L_PR": l["right"],
        "L_PT": l["top"],   "L_PB": l["bottom"],
    }


def extract_features_with_pupils(
    image,
    min_confidence: float = 0.4,
) -> "tuple[FaceFeatureVector | None, dict | None, dict | None]":
    """
    feature_extractor.extract_features_full의 drop-in 대체.
    ADF 검출 + OpenCV 눈동자 검출을 한 번에 실행.
    Eye_TopLidDown can use OpenCV pupil center; Eye_PupilWidth/V remain Eye_WidthV proxies.
    """
    img_bgr        = _to_bgr(image)
    img_path, _tmp = _ensure_path(image, img_bgr)
    groups, _, kps_raw = _run_adf(img_bgr, img_path)
    if _tmp:
        try: os.unlink(_tmp)
        except OSError: pass
    if groups is None:
        return None, None, None

    depth = None
    _side_cheek_raw = None
    from pathlib import Path
    if isinstance(image, str):
        parent = Path(image).parent
        stem   = Path(image).stem
        front_d = parent / (stem + "_depth.npy")
        if front_d.is_file():
            depth = np.load(str(front_d)).astype(np.float32)
        ld, rd = parent / "left_depth.npy", parent / "right_depth.npy"
        _side_raws = []
        for sp in (ld, rd):
            if sp.is_file():
                sd_arr = np.load(str(sp)).astype(np.float32)
                r = _compute_cheek_from_side(sd_arr, kps_raw, img_bgr.shape[0])
                if r is not None and r >= 0.15:
                    _side_raws.append(r)
        _side_cheek_raw = float(sum(_side_raws) / len(_side_raws)) if _side_raws else None

    fv     = _compute_features(groups)
    manual = detect_pupils(img_bgr, kps_raw)
    raw_out: dict = {}
    avatar_keys = compute_avatar_keys(kps_raw, manual=manual, _raw_out=raw_out, depth=depth, img_shape=img_bgr.shape[:2])

    face_cheek_2d_raw = raw_out.get("Face_Cheek")

    if _side_cheek_raw is not None:
        avatar_keys["Face_Cheek"] = 0.0
        raw_out["Face_Cheek"] = {"value": _side_cheek_raw, "source": "renderer/depth"}
    else:
        raw_out["Face_Cheek"] = {"value": face_cheek_2d_raw, "source": "adf/2d_proxy"}

    return fv, avatar_keys, raw_out
