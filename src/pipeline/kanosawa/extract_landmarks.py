"""Anime face landmark 추출 — cascade 완화 + manual bbox fallback 지원."""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from torchvision import transforms
import cv2
from PIL import Image, ImageDraw, ImageFont
from CFA import CFA

NUM_LANDMARK = 24
IMG_WIDTH = 128
CKPT = os.path.join(os.path.dirname(__file__), 'checkpoint_landmark_191116.pth.tar')
CASCADE = os.path.join(os.path.dirname(__file__), 'lbpcascade_animeface.xml')

def detect_or_manual(img_bgr, manual_bbox=None):
    """1차 cascade 시도 → 실패하면 manual bbox 또는 전체 이미지 사용."""
    face_detector = cv2.CascadeClassifier(CASCADE)
    # 완화된 파라미터로 시도
    for sf, mn in [(1.05, 3), (1.05, 2), (1.1, 1), (1.2, 1)]:
        faces = face_detector.detectMultiScale(img_bgr, scaleFactor=sf, minNeighbors=mn, minSize=(40, 40))
        if len(faces) > 0:
            print(f"  Cascade succeeded with sf={sf}, mn={mn}: {len(faces)} faces")
            return faces
    if manual_bbox:
        print(f"  Cascade failed, using manual bbox: {manual_bbox}")
        return [manual_bbox]
    # 마지막 fallback: 이미지 중앙을 얼굴로 가정
    h, w = img_bgr.shape[:2]
    bbox = (w // 6, h // 8, w * 2 // 3, h * 5 // 8)
    print(f"  Cascade failed, using center fallback: {bbox}")
    return [bbox]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("output_image")
    p.add_argument("--bbox", help="manual bbox 'x,y,w,h'")
    p.add_argument("--landmarks_json", help="save landmarks to json")
    args = p.parse_args()
    
    img_bgr = cv2.imread(args.input)
    if img_bgr is None:
        print(f"ERROR: cannot read {args.input}")
        sys.exit(1)
    print(f"Input shape: {img_bgr.shape}")
    
    manual_bbox = None
    if args.bbox:
        manual_bbox = tuple(map(int, args.bbox.split(',')))
    
    faces = detect_or_manual(img_bgr, manual_bbox)
    
    landmark_detector = CFA(output_channel_num=NUM_LANDMARK + 1, checkpoint_name=CKPT).cpu()
    landmark_detector.eval()
    normalize = transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    to_tensor = transforms.Compose([transforms.ToTensor(), normalize])
    
    img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)
    all_landmarks = []
    
    for fi, (x_, y_, w_, h_) in enumerate(faces):
        x = max(x_ - w_ / 8, 0)
        rx = min(x_ + w_ * 9 / 8, img.width)
        y = max(y_ - h_ / 4, 0)
        by = min(y_ + h_, img.height)
        w = rx - x
        h = by - y
        draw.rectangle((x, y, x + w, y + h), outline=(0, 0, 255), width=3)
        
        crop = img.crop((x, y, x + w, y + h)).resize((IMG_WIDTH, IMG_WIDTH), Image.BICUBIC)
        inp = to_tensor(crop).unsqueeze(0)
        with torch.no_grad():
            heatmaps = landmark_detector(inp)[-1].numpy()[0]
        
        face_lms = []
        for i in range(NUM_LANDMARK):
            hm = cv2.resize(heatmaps[i], (IMG_WIDTH, IMG_WIDTH), interpolation=cv2.INTER_CUBIC)
            ly, lx = np.unravel_index(np.argmax(hm), hm.shape)
            gx = x + lx * w / IMG_WIDTH
            gy = y + ly * h / IMG_WIDTH
            face_lms.append([float(gx), float(gy)])
            # 작은 점 + 번호
            r = 4
            draw.ellipse((gx - r, gy - r, gx + r, gy + r), fill=(255, 0, 0), outline=(0, 0, 0))
            draw.text((gx + 6, gy - 8), str(i), fill=(0, 200, 0))
        all_landmarks.append({"bbox": [float(x), float(y), float(w), float(h)],
                              "landmarks": face_lms})
    
    img.save(args.output_image)
    print(f"\n✓ Saved annotated image: {args.output_image}")
    
    if args.landmarks_json:
        with open(args.landmarks_json, 'w') as f:
            json.dump(all_landmarks, f, indent=2)
        print(f"✓ Saved landmarks JSON: {args.landmarks_json}")
    
    # 좌표 출력
    for fi, fd in enumerate(all_landmarks):
        print(f"\nFace {fi}: bbox={fd['bbox']}")
        for i, (lx, ly) in enumerate(fd['landmarks']):
            print(f"  [{i:2d}] ({lx:6.1f}, {ly:6.1f})")


if __name__ == "__main__":
    main()
