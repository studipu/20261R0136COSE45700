"""눈 ROI 크롭 확대 시각화"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import cv2, numpy as np
from tools.pupil_vis import detect_pupils, visualize, run
from pipeline.feature_extractor import _to_bgr, _run_adf, _ensure_path

def run_zoom(image_path, out_dir="output_test"):
    img_bgr = _to_bgr(image_path)
    img_path, _tmp = _ensure_path(image_path, img_bgr)

    groups, face_bbox, kps = _run_adf(img_bgr, img_path)
    if _tmp:
        try: os.unlink(_tmp)
        except: pass
    if kps is None:
        print("[ERROR] ADF 탐지 실패"); return

    from tools.pupil_vis import detect_pupils, visualize, _detect_pupil_opencv
    r_pupil, l_pupil = detect_pupils(img_bgr, kps)

    # 전체 시각화
    vis = img_bgr.copy()
    for i in [11,12,13]:
        cv2.circle(vis, (int(kps[i][0]),int(kps[i][1])), 3, (0,220,80), -1)
    for i in [14,15,16]:
        cv2.circle(vis, (int(kps[i][0]),int(kps[i][1])), 3, (255,160,0), -1)
    for i in [17,18,19]:
        cv2.circle(vis, (int(kps[i][0]),int(kps[i][1])), 3, (0,220,80), -1)
    for i in [20,21,22]:
        cv2.circle(vis, (int(kps[i][0]),int(kps[i][1])), 3, (255,160,0), -1)

    for pupil, label in [(r_pupil,"R"), (l_pupil,"L")]:
        if pupil is None: continue
        cx, cy = int(pupil["center"][0]), int(pupil["center"][1])
        r = max(int(pupil["radius"]), 2)
        color = (0,0,255) if pupil["method"]=="hough" else \
                (0,180,255) if pupil["method"]=="contour" else (120,120,255)
        cv2.circle(vis, (cx,cy), r, color, 1)
        cv2.circle(vis, (cx,cy), 2, color, -1)
        cv2.circle(vis, (int(pupil["left"][0]),cy), 2, (255,0,200), -1)
        cv2.circle(vis, (int(pupil["right"][0]),cy), 2, (255,0,200), -1)
        cv2.circle(vis, (cx,int(pupil["top"][1])), 2, (200,0,255), -1)
        cv2.circle(vis, (cx,int(pupil["bottom"][1])), 2, (200,0,255), -1)
        cv2.putText(vis, f"{label}({pupil['method'][0]})", (cx+4,cy-4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

    # 눈 영역만 크롭 (양쪽 눈 포함)
    eye_pts = [kps[i] for i in range(11,23)]
    xs = [p[0] for p in eye_pts]; ys = [p[1] for p in eye_pts]
    pad = 40
    H, W = img_bgr.shape[:2]
    ex1 = max(0, int(min(xs)-pad)); ex2 = min(W, int(max(xs)+pad))
    ey1 = max(0, int(min(ys)-pad)); ey2 = min(H, int(max(ys)+pad))

    eye_crop = vis[ey1:ey2, ex1:ex2]
    # 3배 확대
    scale = 3
    eye_crop_big = cv2.resize(eye_crop, (eye_crop.shape[1]*scale, eye_crop.shape[0]*scale),
                              interpolation=cv2.INTER_NEAREST)

    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(image_path))[0]

    full_path = os.path.join(out_dir, f"{stem}_pupil_full.png")
    zoom_path = os.path.join(out_dir, f"{stem}_pupil_zoom.png")
    cv2.imwrite(full_path, vis)
    cv2.imwrite(zoom_path, eye_crop_big)

    print(f"R: method={r_pupil['method'] if r_pupil else 'None'}  "
          f"center={r_pupil['center'] if r_pupil else '-'}  r={r_pupil['radius'] if r_pupil else '-':.1f}")
    print(f"L: method={l_pupil['method'] if l_pupil else 'None'}  "
          f"center={l_pupil['center'] if l_pupil else '-'}  r={l_pupil['radius'] if l_pupil else '-':.1f}")
    print(f"Saved: {full_path}")
    print(f"Saved: {zoom_path}")


if __name__ == "__main__":
    images = sys.argv[1:] if len(sys.argv) > 1 else [
        "input_image/01_original.png",
        "input_image/02_original.png",
        "input_image/03_original.png",
    ]
    for img in images:
        print(f"\n=== {img} ===")
        try:
            run_zoom(img)
        except Exception as e:
            print(f"  ERROR: {e}")
