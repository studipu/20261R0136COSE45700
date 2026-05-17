"""3-way 비교 이미지 생성: 입력 / 마스터 baseline / 마스터 적용 후"""
import sys, argparse
from PIL import Image, ImageDraw

def make_3way(varco, baseline, after, out):
    W, H = 512, 512
    canvas_w = W * 3 + 40
    canvas_h = H + 60
    canvas = Image.new("RGB", (canvas_w, canvas_h), (240, 240, 245))
    draw = ImageDraw.Draw(canvas)
    labels = [("Input (target)", varco), ("Master baseline", baseline), ("Master AFTER apply", after)]
    for i, (lab, path) in enumerate(labels):
        img = Image.open(path).convert("RGB").resize((W, H))
        canvas.paste(img, (i * (W + 20) + 10, 50))
        draw.rectangle((i*(W+20)+10, 10, i*(W+20)+10+W, 45), fill=(40, 40, 60))
        draw.text((i*(W+20)+25, 18), lab, fill=(255, 255, 255))
    canvas.save(out)
    print(f"✓ Comparison saved: {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input")
    p.add_argument("--baseline")
    p.add_argument("--after")
    p.add_argument("--out")
    args = p.parse_args()
    make_3way(args.input, args.baseline, args.after, args.out)
