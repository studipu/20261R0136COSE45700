"""CPU-friendly version of example.py for sandbox testing."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from torchvision import transforms
import cv2
from PIL import Image, ImageDraw
from CFA import CFA

# 파라미터
NUM_LANDMARK = 24
IMG_WIDTH = 128
CKPT = os.path.join(os.path.dirname(__file__), 'checkpoint_landmark_191116.pth.tar')
CASCADE = os.path.join(os.path.dirname(__file__), 'lbpcascade_animeface.xml')
INPUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'test.png')
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else 'output.png'

print(f"Input: {INPUT}")
print(f"Output: {OUTPUT}")

# 모델 로드 (CPU)
face_detector = cv2.CascadeClassifier(CASCADE)
landmark_detector = CFA(output_channel_num=NUM_LANDMARK + 1, checkpoint_name=CKPT).cpu()
landmark_detector.eval()

# transform
normalize = transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
to_tensor = transforms.Compose([transforms.ToTensor(), normalize])

# 이미지 읽기
img_bgr = cv2.imread(INPUT)
if img_bgr is None:
    print(f"ERROR: cannot read {INPUT}")
    sys.exit(1)

faces = face_detector.detectMultiScale(img_bgr)
print(f"Faces detected: {len(faces)}")

img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
draw = ImageDraw.Draw(img)
all_landmarks = []

for fi, (x_, y_, w_, h_) in enumerate(faces):
    # 얼굴 영역 약간 확장
    x = max(x_ - w_ / 8, 0)
    rx = min(x_ + w_ * 9 / 8, img.width)
    y = max(y_ - h_ / 4, 0)
    by = y_ + h_
    w = rx - x
    h = by - y
    draw.rectangle((x, y, x + w, y + h), outline=(0, 0, 255), width=3)

    # crop + transform
    crop = img.crop((x, y, x + w, y + h)).resize((IMG_WIDTH, IMG_WIDTH), Image.BICUBIC)
    inp = to_tensor(crop).unsqueeze(0)  # CPU
    with torch.no_grad():
        heatmaps = landmark_detector(inp)[-1].numpy()[0]

    # landmark 좌표 추출
    face_lms = []
    for i in range(NUM_LANDMARK):
        hm = cv2.resize(heatmaps[i], (IMG_WIDTH, IMG_WIDTH), interpolation=cv2.INTER_CUBIC)
        ly, lx = np.unravel_index(np.argmax(hm), hm.shape)
        gx = x + lx * w / IMG_WIDTH
        gy = y + ly * h / IMG_WIDTH
        face_lms.append((float(gx), float(gy)))
        draw.ellipse((gx - 3, gy - 3, gx + 3, gy + 3), fill=(255, 0, 0))
        draw.text((gx + 4, gy - 5), str(i), fill=(255, 255, 0))
    all_landmarks.append(face_lms)
    print(f"\nFace {fi}: bbox=({x:.0f},{y:.0f},{w:.0f},{h:.0f}), 24 landmarks:")
    for i, (lx, ly) in enumerate(face_lms):
        print(f"  [{i:2d}] ({lx:6.1f}, {ly:6.1f})")

img.save(OUTPUT)
print(f"\n✓ Saved {OUTPUT}")
