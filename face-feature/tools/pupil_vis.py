"""
OpenCV pupil detection visualization.
ADF 28-point landmarks -> eye ROI crop -> HoughCircles / dark-region fallback
-> visualize pupil center + left/right/top/bottom points

Usage:
  python tools/pupil_vis.py input_image/01_original.png
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import cv2
import numpy as np
from PIL import Image
from pipeline.feature_extractor import _to_bgr, _run_adf, _ensure_path

_EPS = 1e-6

# ADF eye keypoint indices
# right_eye: 11(UL) 12(UM) 13(UR) / 14(LL) 15(LM) 16(LR)
# left_eye:  17(UL) 18(UM) 19(UR) / 20(LL) 21(LM) 22(LR)

def _detect_pupil_opencv(img_bgr, eye_kps_upper, eye_kps_lower, pad=0.5):
    """
    eye_kps_upper: 3개 상단 랜드마크 [(x,y), ...]
    eye_kps_lower: 3개 하단 랜드마크 [(x,y), ...]
    Returns: dict with center, left, right, top, bottom  (image coords)
             or None on failure
    """
    all_pts = eye_kps_upper + eye_kps_lower
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)

    eye_w = x2 - x1 + _EPS
    eye_h = y2 - y1 + _EPS
    px = eye_w * pad
    py = eye_h * pad

    H, W = img_bgr.shape[:2]
    rx1 = max(0, int(x1 - px))
    ry1 = max(0, int(y1 - py))
    rx2 = min(W, int(x2 + px))
    ry2 = min(H, int(y2 + py))

    if rx2 - rx1 < 4 or ry2 - ry1 < 4:
        return None

    roi = img_bgr[ry1:ry2, rx1:rx2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # CLAHE로 대비 강화
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    gray = clahe.apply(gray)

    rh, rw = gray.shape
    min_r = max(2, int(min(eye_w, eye_h) * 0.15))
    max_r = max(min_r + 2, int(min(eye_w, eye_h) * 0.45))

    # ── 1차: HoughCircles ─────────────────────────────────────────────────
    circles = cv2.HoughCircles(
        cv2.GaussianBlur(gray, (3, 3), 0),
        cv2.HOUGH_GRADIENT, dp=1,
        minDist=rw,
        param1=40, param2=15,
        minRadius=min_r, maxRadius=max_r,
    )

    if circles is not None:
        c = circles[0][0]
        cx_r, cy_r, r = float(c[0]), float(c[1]), float(c[2])
        cx = cx_r + rx1
        cy = cy_r + ry1
        return dict(
            center=(cx, cy),
            left=(cx - r, cy),
            right=(cx + r, cy),
            top=(cx, cy - r),
            bottom=(cx, cy + r),
            radius=r,
            method="hough",
        )

    # ── 2차: 어두운 영역 centroid ─────────────────────────────────────────
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, dark = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # eye bbox 안에 중심이 있는 contour만 필터
        candidates = []
        for cnt in contours:
            M = cv2.moments(cnt)
            if M["m00"] < 4:
                continue
            cx_r = M["m10"] / M["m00"]
            cy_r = M["m01"] / M["m00"]
            # ROI 내에서 eye bbox 범위 확인
            ex1, ex2 = x1 - rx1, x2 - rx1
            ey1, ey2 = y1 - ry1, y2 - ry1
            if ex1 <= cx_r <= ex2 and ey1 <= cy_r <= ey2:
                candidates.append((cv2.contourArea(cnt), cx_r, cy_r, cnt))
        if candidates:
            candidates.sort(key=lambda t: -t[0])
            _, cx_r, cy_r, cnt = candidates[0]
            _, enc_r = cv2.minEnclosingCircle(cnt)
            r = float(enc_r) * 0.5
            cx = cx_r + rx1
            cy = cy_r + ry1
            return dict(
                center=(cx, cy),
                left=(cx - r, cy),
                right=(cx + r, cy),
                top=(cx, cy - r),
                bottom=(cx, cy + r),
                radius=r,
                method="contour",
            )

    # ── 3차: fallback — eye bbox 중심 ─────────────────────────────────────
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    r = min(eye_w, eye_h) * 0.2
    return dict(
        center=(cx, cy),
        left=(cx - r, cy),
        right=(cx + r, cy),
        top=(cx, cy - r),
        bottom=(cx, cy + r),
        radius=r,
        method="fallback",
    )


def detect_pupils(img_bgr, kps):
    """
    kps: ADF 28-point list of (x,y)
    Returns (r_pupil, l_pupil) each is dict or None
    """
    r_upper = [kps[11], kps[12], kps[13]]
    r_lower = [kps[14], kps[15], kps[16]]
    l_upper = [kps[17], kps[18], kps[19]]
    l_lower = [kps[20], kps[21], kps[22]]

    r_pupil = _detect_pupil_opencv(img_bgr, r_upper, r_lower)
    l_pupil = _detect_pupil_opencv(img_bgr, l_upper, l_lower)
    return r_pupil, l_pupil


def build_manual(r_pupil, l_pupil):
    """pupil dict → compute_avatar_keys의 manual 딕셔너리"""
    if r_pupil is None or l_pupil is None:
        return None
    return {
        "R_PL": r_pupil["left"],
        "R_PR": r_pupil["right"],
        "R_PT": r_pupil["top"],
        "R_PB": r_pupil["bottom"],
        "L_PL": l_pupil["left"],
        "L_PR": l_pupil["right"],
        "L_PT": l_pupil["top"],
        "L_PB": l_pupil["bottom"],
    }


def visualize(img_bgr, kps, r_pupil, l_pupil, out_path):
    vis = img_bgr.copy()

    # ADF 눈 랜드마크 (상: 초록, 하: 파랑)
    for i in [11, 12, 13]:
        cv2.circle(vis, (int(kps[i][0]), int(kps[i][1])), 3, (0, 220, 80), -1)
    for i in [14, 15, 16]:
        cv2.circle(vis, (int(kps[i][0]), int(kps[i][1])), 3, (255, 160, 0), -1)
    for i in [17, 18, 19]:
        cv2.circle(vis, (int(kps[i][0]), int(kps[i][1])), 3, (0, 220, 80), -1)
    for i in [20, 21, 22]:
        cv2.circle(vis, (int(kps[i][0]), int(kps[i][1])), 3, (255, 160, 0), -1)

    # 눈동자
    for pupil, label in [(r_pupil, "R"), (l_pupil, "L")]:
        if pupil is None:
            continue
        cx, cy = int(pupil["center"][0]), int(pupil["center"][1])
        r = int(pupil["radius"])
        method = pupil["method"]
        color = (0, 0, 255) if method == "hough" else \
                (0, 180, 255) if method == "contour" else (100, 100, 255)

        cv2.circle(vis, (cx, cy), max(r, 2), color, 1)      # 홍채 원
        cv2.circle(vis, (cx, cy), 2, color, -1)              # 중심점
        cv2.circle(vis, (int(pupil["left"][0]),   cy), 2, (255, 0, 200), -1)
        cv2.circle(vis, (int(pupil["right"][0]),  cy), 2, (255, 0, 200), -1)
        cv2.circle(vis, (cx, int(pupil["top"][1])),    2, (200, 0, 255), -1)
        cv2.circle(vis, (cx, int(pupil["bottom"][1])), 2, (200, 0, 255), -1)

        cv2.putText(vis, f"{label}({method[0]})", (cx + 4, cy - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)

    cv2.imwrite(out_path, vis)
    print(f"Saved: {out_path}")


def run(image_path, out_dir="output_test"):
    img_bgr = _to_bgr(image_path)
    img_path, _tmp = _ensure_path(image_path, img_bgr)

    print("ADF 랜드마크 추출 중...")
    groups, face_bbox, kps = _run_adf(img_bgr, img_path)
    if _tmp:
        try: os.unlink(_tmp)
        except: pass
    if kps is None:
        print("[ERROR] ADF 탐지 실패")
        return

    print("눈동자 검출 중...")
    r_pupil, l_pupil = detect_pupils(img_bgr, kps)
    print(f"  R: {r_pupil['method'] if r_pupil else 'None'}  center={r_pupil['center'] if r_pupil else '-'}")
    print(f"  L: {l_pupil['method'] if l_pupil else 'None'}  center={l_pupil['center'] if l_pupil else '-'}")

    manual = build_manual(r_pupil, l_pupil)
    if manual:
        from pipeline.feature_extractor import compute_avatar_keys, _map_signed
        keys = compute_avatar_keys(kps, manual=manual)
        print(f"  Eye_PupilWidth  = {keys['Eye_PupilWidth']:.4f}")
        print(f"  Eye_PupilWidthV = {keys['Eye_PupilWidthV']:.4f}")

    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(image_path))[0]
    out_path = os.path.join(out_dir, f"{stem}_pupil.png")
    visualize(img_bgr, kps, r_pupil, l_pupil, out_path)


if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else "input_image/01_original.png"
    run(img)
