"""
24 landmark + 색상 segmentation 하이브리드 측정값 추출

Landmark 매핑 (시각 검증으로 확정):
  [ 0]  왼쪽 얼굴 외곽 (관자놀이~광대)
  [ 1]  턱 끝 / 아래
  [ 2]  오른쪽 얼굴 외곽
  [ 3,4,5]  왼쪽 눈썹 (외→안)
  [ 6,7,8]  오른쪽 눈썹 (안→외)
  [ 9]    얼굴 중심 보조 (위치 가변, 사용 X)
  [10,11,12,13,14]  왼쪽 눈 (외/위/안/아래/중심)
  [15,16,17,18,19]  오른쪽 눈 (안/위/외/아래/중심)
  [20,21,22,23]   입 가운데 4점 (좌·중·우·아래)
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import cv2
from PIL import Image
import torch
from torchvision import transforms
from CFA import CFA

NUM_LANDMARK = 24
IMG_WIDTH = 128
CKPT = os.path.join(os.path.dirname(__file__), 'checkpoint_landmark_191116.pth.tar')
CASCADE = os.path.join(os.path.dirname(__file__), 'lbpcascade_animeface.xml')

# Landmark index 정의
L = {
    "face_left":   0,   "face_chin":  1,   "face_right":  2,
    "browL_out":   3,   "browL_top":  4,   "browL_in":    5,
    "browR_in":    6,   "browR_top":  7,   "browR_out":   8,
    "eyeL_out":   10,   "eyeL_top":  11,   "eyeL_in":    12,
    "eyeL_bot":   13,   "eyeL_ctr":  14,
    "eyeR_in":    15,   "eyeR_top":  16,   "eyeR_out":   17,
    "eyeR_bot":   18,   "eyeR_ctr":  19,
    "mouth_l":    20,   "mouth_c":   21,   "mouth_r":    22,   "mouth_bot": 23,
}

def detect_face_and_landmarks(img_bgr):
    fd = cv2.CascadeClassifier(CASCADE)
    faces = []
    for sf, mn in [(1.05, 3), (1.05, 2), (1.1, 1)]:
        faces = fd.detectMultiScale(img_bgr, scaleFactor=sf, minNeighbors=mn, minSize=(40, 40))
        if len(faces) > 0:
            break
    if len(faces) == 0:
        h, w = img_bgr.shape[:2]
        faces = [(w // 6, h // 8, w * 2 // 3, h * 5 // 8)]

    detector = CFA(output_channel_num=NUM_LANDMARK + 1, checkpoint_name=CKPT).cpu()
    detector.eval()
    norm = transforms.Normalize(mean=[0.5]*3, std=[0.5]*3)
    to_tensor = transforms.Compose([transforms.ToTensor(), norm])
    img_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

    x_, y_, w_, h_ = faces[0]
    x = max(x_ - w_ / 8, 0)
    rx = min(x_ + w_ * 9 / 8, img_pil.width)
    y = max(y_ - h_ / 4, 0)
    by = min(y_ + h_, img_pil.height)
    w, h = rx - x, by - y
    crop = img_pil.crop((x, y, x + w, y + h)).resize((IMG_WIDTH, IMG_WIDTH), Image.BICUBIC)
    inp = to_tensor(crop).unsqueeze(0)
    with torch.no_grad():
        heatmaps = detector(inp)[-1].numpy()[0]
    landmarks = []
    for i in range(NUM_LANDMARK):
        hm = cv2.resize(heatmaps[i], (IMG_WIDTH, IMG_WIDTH), interpolation=cv2.INTER_CUBIC)
        ly, lx = np.unravel_index(np.argmax(hm), hm.shape)
        gx = x + lx * w / IMG_WIDTH
        gy = y + ly * h / IMG_WIDTH
        landmarks.append((float(gx), float(gy)))
    bbox = (float(x), float(y), float(w), float(h))
    return bbox, landmarks


def dist(p, q):
    return float(np.hypot(q[0] - p[0], q[1] - p[1]))


def measure(img_bgr, landmarks, bbox):
    """24 landmark + 부가 색상 정보 → 측정값 dict"""
    P = lambda name: landmarks[L[name]]
    M = {}

    face_w = dist(P("face_left"), P("face_right"))   # 정규화 단위

    # ---- Eye (10 metrics from landmarks) ----
    M["eyeL_width"]  = dist(P("eyeL_out"), P("eyeL_in")) / face_w
    M["eyeR_width"]  = dist(P("eyeR_out"), P("eyeR_in")) / face_w
    M["eye_width"]   = (M["eyeL_width"] + M["eyeR_width"]) / 2

    M["eyeL_height"] = dist(P("eyeL_top"), P("eyeL_bot")) / face_w
    M["eyeR_height"] = dist(P("eyeR_top"), P("eyeR_bot")) / face_w
    M["eye_widthV"]  = (M["eyeL_height"] + M["eyeR_height"]) / 2

    # eye_dist = 두 눈 안쪽 끝 거리
    M["eye_dist"]    = dist(P("eyeL_in"), P("eyeR_in")) / face_w

    # eye_height = 얼굴 중심선 기준 눈 높이
    face_top = min(P("browL_top")[1], P("browR_top")[1])
    face_bot = P("face_chin")[1]
    eye_y = (P("eyeL_ctr")[1] + P("eyeR_ctr")[1]) / 2
    M["eye_y_norm"]  = (eye_y - face_top) / (face_bot - face_top + 1e-6)

    # eye_rot = 좌우 눈 각도 (눈꼬리 기울기)
    dx = P("eyeR_out")[0] - P("eyeL_out")[0]
    dy = P("eyeR_out")[1] - P("eyeL_out")[1]
    M["eye_rot_deg"] = float(np.degrees(np.arctan2(dy, dx)))

    # ---- Brow ----
    M["browL_width"] = dist(P("browL_out"), P("browL_in")) / face_w
    M["browR_width"] = dist(P("browR_out"), P("browR_in")) / face_w
    M["brow_width"]  = (M["browL_width"] + M["browR_width"]) / 2
    M["brow_dist"]   = dist(P("browL_in"), P("browR_in")) / face_w
    brow_y = (P("browL_top")[1] + P("browR_top")[1]) / 2
    M["brow_y_norm"] = (brow_y - face_top) / (face_bot - face_top + 1e-6)
    # brow_rot — 두 눈썹 끝 각도
    dxb = P("browR_out")[0] - P("browL_out")[0]
    dyb = P("browR_out")[1] - P("browL_out")[1]
    M["brow_rot_deg"] = float(np.degrees(np.arctan2(dyb, dxb)))

    # ---- Mouth (4 landmarks + 색상 segmentation으로 보강) ----
    M["mouth_width"]  = dist(P("mouth_l"), P("mouth_r")) / face_w
    mouth_y = (P("mouth_l")[1] + P("mouth_r")[1]) / 2
    M["mouth_y_norm"] = (mouth_y - face_top) / (face_bot - face_top + 1e-6)
    # mouth_corner: 입꼬리 좌·우 평균 vs 가운데 y차이
    corner_y = (P("mouth_l")[1] + P("mouth_r")[1]) / 2
    M["mouth_corner_dy"] = float(P("mouth_c")[1] - corner_y) / face_w  # 양수=입꼬리 올라감

    # ---- Face contour (3 landmarks) ----
    M["face_width"]   = float(face_w)   # 절대 픽셀 (정규화 안 함)
    M["face_height"]  = float(face_bot - face_top)
    M["chin_x_offset"] = float(P("face_chin")[0] - (P("face_left")[0] + P("face_right")[0]) / 2) / face_w
    
    # ---- Color-based augmentation (HSV) ----
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    H, S, V = img_hsv[:,:,0], img_hsv[:,:,1], img_hsv[:,:,2]

    # 입술 (빨강/분홍): H 0~15 또는 H 165~179
    lip_mask = (((H < 15) | (H > 165)) & (S > 60) & (V > 60)).astype(np.uint8)
    # bbox 안 + 입 부근(아래 1/3)
    x, y, w, h = bbox
    yy_min = int(y + h * 0.55)
    yy_max = int(y + h * 0.95)
    xx_min = int(x + w * 0.20)
    xx_max = int(x + w * 0.80)
    lip_roi = lip_mask[yy_min:yy_max, xx_min:xx_max]
    if lip_roi.sum() > 30:
        ys, xs = np.where(lip_roi > 0)
        M["lip_width_px"]  = float(xs.max() - xs.min())
        M["lip_height_px"] = float(ys.max() - ys.min())
        M["lip_width_norm"]  = M["lip_width_px"] / face_w
        M["lip_height_norm"] = M["lip_height_px"] / face_w
    else:
        M["lip_width_px"] = M["lip_height_px"] = M["lip_width_norm"] = M["lip_height_norm"] = 0.0
    
    return M


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("output_json")
    p.add_argument("--annotated", help="optional annotated image output")
    args = p.parse_args()

    img = cv2.imread(args.input)
    if img is None:
        print(f"ERROR: cannot read {args.input}")
        sys.exit(1)
    print(f"Input: {args.input} ({img.shape})")

    bbox, lms = detect_face_and_landmarks(img)
    M = measure(img, lms, bbox)

    out = {
        "input": args.input,
        "image_size": [int(img.shape[1]), int(img.shape[0])],
        "bbox": list(bbox),
        "landmarks": [list(l) for l in lms],
        "measurements": M,
    }
    with open(args.output_json, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n=== Measurements ({len(M)}) ===")
    for k, v in M.items():
        print(f"  {k:25s}: {v:.4f}")
    print(f"\n✓ Saved: {args.output_json}")


if __name__ == "__main__":
    main()
