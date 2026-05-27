from google import genai
from google.genai import types
from dotenv import load_dotenv
import cv2
import numpy as np
import os
import json
from pathlib import Path

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def sample_iris_colors(image_path: str, landmarks_path: str) -> dict | None:
    """landmark 기반으로 홍채 5방향 색상을 직접 픽셀 샘플링.

    Returns None if landmarks are unreliable (eye too small, asymmetric,
    or sampled colors have very low saturation).
    """
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    with open(landmarks_path) as f:
        lm_data = json.load(f)
    # Pick the largest face if multiple detected
    if len(lm_data) > 1:
        lm_entry = max(lm_data, key=lambda f: f["bbox"][2] * f["bbox"][3])
    else:
        lm_entry = lm_data[0]
    lm = lm_entry["landmarks"]

    eyes = [
        {
            "cx": int(lm[14][0]), "cy": int(lm[14][1]),
            "rx": int(abs(lm[12][0] - lm[10][0]) / 2),
            "ry": int(abs(lm[13][1] - lm[11][1]) / 2),
        },
        {
            "cx": int(lm[19][0]), "cy": int(lm[19][1]),
            "rx": int(abs(lm[17][0] - lm[15][0]) / 2),
            "ry": int(abs(lm[18][1] - lm[16][1]) / 2),
        },
    ]

    # Validate eye dimensions — skip if either eye region is too small
    # or too asymmetric (indicates landmark misdetection from hair occlusion)
    min_radius = 12
    for eye in eyes:
        if eye["rx"] < min_radius or eye["ry"] < min_radius:
            print(f"  홍채 샘플링 건너뜀: 눈 영역 너무 작음 (rx={eye['rx']}, ry={eye['ry']})")
            return None
    ratio = max(eyes[0]["rx"], eyes[1]["rx"]) / max(min(eyes[0]["rx"], eyes[1]["rx"]), 1)
    if ratio > 2.5:
        print(f"  홍채 샘플링 건너뜀: 눈 크기 비대칭 ({ratio:.1f}x)")
        return None

    def sample_sector(img_rgb, cx, cy, rx, ry, angle_start, angle_end, r_min=0.2, r_max=0.8):
        """부채꼴 영역에서 지배적인 색상 추출 (흰색 하이라이트 제외)"""
        h, w = img_rgb.shape[:2]
        pixels = []
        for py in range(max(0, cy - ry), min(h, cy + ry)):
            for px in range(max(0, cx - rx), min(w, cx + rx)):
                nx = (px - cx) / rx
                ny = (py - cy) / ry
                r = np.sqrt(nx*nx + ny*ny)
                if r < r_min or r > r_max:
                    continue
                angle = np.degrees(np.arctan2(-ny, nx)) % 360
                # 각도 범위 체크 (wrap around 처리)
                if angle_start <= angle_end:
                    if not (angle_start <= angle <= angle_end):
                        continue
                else:  # wrap around (예: 315~45)
                    if not (angle >= angle_start or angle <= angle_end):
                        continue
                p = img_rgb[py, px]
                if max(p) < 230:  # 흰색 하이라이트 제외
                    pixels.append(p)

        if not pixels:
            return [128, 128, 128]

        # 가장 채도 높은 픽셀 선택
        best = max(pixels, key=lambda p: max(p) - min(p))
        return [int(best[0]), int(best[1]), int(best[2])]

    def sample_center(img_rgb, cx, cy, rx, ry, r_max=0.3):
        """중앙 원형 영역에서 지배적인 색상 추출"""
        h, w = img_rgb.shape[:2]
        pixels = []
        for py in range(max(0, cy - ry), min(h, cy + ry)):
            for px in range(max(0, cx - rx), min(w, cx + rx)):
                nx = (px - cx) / rx
                ny = (py - cy) / ry
                if nx*nx + ny*ny > r_max*r_max:
                    continue
                p = img_rgb[py, px]
                if max(p) < 230:
                    pixels.append(p)
        if not pixels:
            return [128, 128, 128]
        best = max(pixels, key=lambda p: max(p) - min(p))
        return [int(best[0]), int(best[1]), int(best[2])]

    all_samples = []
    for eye in eyes:
        cx, cy, rx, ry = eye["cx"], eye["cy"], eye["rx"], eye["ry"]
        all_samples.append({
            "top":    sample_sector(img_rgb, cx, cy, rx, ry,  30, 150),
            "bottom": sample_sector(img_rgb, cx, cy, rx, ry, 210, 330),
            "left":   sample_sector(img_rgb, cx, cy, rx, ry, 150, 210),
            "right":  sample_sector(img_rgb, cx, cy, rx, ry, 330,  30),
            "center": sample_center(img_rgb, cx, cy, rx, ry),
        })

    result = {}
    for key in ["top", "bottom", "center"]:
        result[key] = [
            int((all_samples[0][key][c] + all_samples[1][key][c]) / 2)
            for c in range(3)
        ]

    # left/right는 좌우 눈이 이미지에서 반전되어 있으므로 swap
    # all_samples[0] = 왼쪽 눈 (이미지상 왼쪽 = 캐릭터 오른쪽)
    # all_samples[1] = 오른쪽 눈 (이미지상 오른쪽 = 캐릭터 왼쪽)
    result["left"]  = [
        int((all_samples[0]["right"][c] + all_samples[1]["left"][c]) / 2)
        for c in range(3)
    ]
    result["right"] = [
        int((all_samples[0]["left"][c] + all_samples[1]["right"][c]) / 2)
        for c in range(3)
    ]

    return {
        "iris_top_color":    result["top"],
        "iris_bottom_color": result["bottom"],
        "iris_left_color":   result["left"],
        "iris_right_color":  result["right"],
        "iris_center_color": result["center"],
    }

def match_hairstyle_preset(image_path: str, thumbnails_dir: str) -> dict:
    """업로드된 이미지를 5개 프리셋 썸네일과 직접 시각 비교하여 가장 유사한 프리셋 선택."""
    import time

    image_bytes = Path(image_path).read_bytes()
    ext = Path(image_path).suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp", ".bmp": "image/bmp"}
    mime_type = mime_map.get(ext, "image/png")

    # Load preset thumbnails
    preset_ids = ["hair-01", "hair-02", "hair-03", "hair-04", "hair-05"]
    thumbnail_parts = []
    for pid in preset_ids:
        thumb_path = Path(thumbnails_dir) / f"{pid}.png"
        if not thumb_path.exists():
            print(f"  [HairMatch] Thumbnail not found: {thumb_path}")
            return {"matched_preset": None, "confidence": 0.0, "reason": "thumbnails not found"}
        thumbnail_parts.append(types.Part.from_bytes(data=thumb_path.read_bytes(), mime_type="image/png"))

    prompt = """You are given 6 images:
- Image 1 (first): The uploaded character image to match
- Images 2-6: Five hair preset thumbnails in order: hair-01, hair-02, hair-03, hair-04, hair-05

Each preset has a DISTINCT hairstyle:
- hair-01: Medium-long straight hair with side-swept bangs, reaches mid-chest/shoulders. NOT past the elbows.
- hair-02: Short bob cut, hair barely reaches the chin/jaw. Clearly short.
- hair-03: High ponytail tied up on top, with an ahoge (antenna hair). Hair is pulled back.
- hair-04: VERY long straight hair, reaches waist or below. Significantly longer than hair-01. Past the elbows.
- hair-05: Short hair with a side braid on one side. Short overall length with braided element.

CRITICAL: The thumbnails show 3/4 side views, but the uploaded image may be from any angle.
Use BOTH the thumbnail images AND the text descriptions above to determine the best match.
The KEY differentiator between hair-01 and hair-04 is LENGTH:
- If hair reaches mid-chest or shoulders → hair-01
- If hair reaches waist/hips or below the elbows → hair-04

Do NOT match by color — all presets have the same brown color. Focus ONLY on hairstyle shape and length.

Reply ONLY in JSON format. No explanation, no markdown, no extra text.

{
  "matched_preset": "hair-01 or hair-02 or hair-03 or hair-04 or hair-05",
  "confidence": 0.0 to 1.0,
  "reason": "brief explanation of why this preset matches"
}
"""

    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        *thumbnail_parts,
        prompt,
    ]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                print(f"  [HairMatch] API error (attempt {attempt+1}/{max_retries}): {e}")
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [HairMatch] All retries failed: {e}")
                return {"matched_preset": None, "confidence": 0.0, "reason": str(e)}

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [HairMatch] Failed to parse response: {raw}")
        return {"matched_preset": None, "confidence": 0.0, "reason": "parse error"}

    print(f"  [HairMatch] Matched: {result.get('matched_preset')} (confidence: {result.get('confidence')}, reason: {result.get('reason')})")
    return result


def extract_face_features(image_path: str, landmarks_path: str = None) -> dict:
    image_bytes = Path(image_path).read_bytes()
    ext = Path(image_path).suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime_type = mime_map.get(ext, "image/png")

    prompt = """
Analyze this Japanese anime-style character image.
Reply ONLY in JSON format. No explanation, no markdown, no extra text.

{
  "face": {
    "skin_tone": [R, G, B],
    "skin_shading_intensity": 0.0~1.0,
    "blush_present": true/false,
    "blush_color": [R, G, B],
    "blush_opacity": 0.0~1.0,
    "blush_position": "cheek_high/cheek_center/cheek_low",
    "markings": [
      {
        "type": "one of: mole/star/teardrop/triangle/diamond/line/tattoo/scar/other",
        "color": [R, G, B],
        "size": "one of: tiny/small/medium/large",
        "side": "left/right/center",
        "reference": "one of: left_eye/right_eye/nose/mouth/left_cheek/right_cheek/forehead/chin",
        "offset_x": "one of: far_left/left/center/right/far_right",
        "offset_y": "one of: far_above/above/same/below/far_below (use same if at same height as reference, NOT center)"
      }
    ]
  },
  "eyebrow": {
    "color": [R, G, B],
    "shape": "arch/straight/down",
    "thickness": "thin/medium/thick",
    "opacity": 0.0~1.0,
    "has_gradient": true/false
  },
  "eyeline": {
    "eyeliner_color": [R, G, B],
    "eyeliner_thickness": "thin/medium/thick",
    "has_eyelid_crease": true/false,
    "eyelid_crease_depth": "shallow/medium/deep",
    "eyelid_crease_color": [R, G, B],
    "lash_intensity": "light/medium/heavy",
    "eyeshadow_present": true/false,
    "eyeshadow_color": [R, G, B],
    "eyeshadow_opacity": 0.0~1.0,
    "eyeshadow_position": "lid_only/lid_and_crease/under_eye/full"
  },
  "pupil": {
    "iris_top_color": [R, G, B],
    "iris_bottom_color": [R, G, B],
    "iris_left_color": [R, G, B],
    "iris_right_color": [R, G, B],
    "iris_center_color": [R, G, B],
    "pupil_color": [R, G, B],
    "pupil_size_ratio": 0.0~1.0,
    "top_shadow_ratio": 0.0~1.0,
"highlights": []
  },
  "general": {
    "hair_color": [R, G, B],
    "hair_style": "one of: long_straight/short_bob/ponytail/very_long_straight/short_braid/twin_tails/other",
    "hair_length": "one of: short/medium/long/very_long",
    "bangs_style": "one of: full/side_swept/curtain/none",
    "overall_style": "soft/sharp/cute/mature",
    "face_shape": "one of: oval/round/heart/square/oblong",
    "chin_shape": "one of: pointed/round/square/wide",
    "jaw_prominence": "one of: soft/moderate/defined/strong"
  }
}

Rules:
- RGB values: integers 0~255
- Ratios: floats 0.0~1.0
- blush is a soft, diffuse color on cheeks — handled separately in blush fields, NOT in markings
- markings: ONLY hard-edged, clearly distinct features such as:
  * mole: a tiny sharply defined dot, NOT a soft color area
  * star/teardrop/triangle/diamond: geometric symbols drawn on the face
  * tattoo/scar: visible markings on skin
- mole must be: very small, sharply defined, single dot — NOT a soft diffuse area
- circle type does NOT exist — use mole for dots
- markings: empty array [] if none present
- Do NOT include blush/flush/soft cheek color as a marking
- Do NOT include eyeshadow or soft gradient areas as markings
- reference: the nearest facial landmark to the marking
- offset_x: horizontal position relative to reference (far_left=far to the left side of face)
- offset_y: vertical position relative to reference (above=slightly above, far_above=much higher)
- eyeshadow is a soft diffuse color on the eyelid area, NOT the eyeliner
- top_shadow_ratio: how much darker the top of the iris is compared to the bottom
  * 0.0 = no shadow (top and bottom same brightness)
  * 0.5 = moderate shadow (top noticeably darker)
  * 1.0 = very strong shadow (top much darker than bottom)
  * Sample the top 20% and bottom 20% of the iris and compare their brightness
- iris colors: CRITICAL - divide the iris into a 3x3 grid (like a numpad):
  +---+---+---+
  | 7 | 8 | 9 |
  +---+---+---+
  | 4 | 5 | 6 |
  +---+---+---+
  | 1 | 2 | 3 |
  +---+---+---+
  Sample ONLY these 5 cells and report the DOMINANT color in each cell (not average):
  * iris_top_color:    cell 8 (top center)
  * iris_left_color:   cell 4 (middle left)
  * iris_center_color: cell 5 (center, around pupil)
  * iris_right_color:  cell 6 (middle right)
  * iris_bottom_color: cell 2 (bottom center)
  * DOMINANT color = the most visually prominent color in that cell, not an average
  * Each cell will likely have a different hue in anime characters
  * anime irises frequently have totally different hues top vs bottom (e.g. purple top, teal/cyan bottom)
  * if a cell looks teal, report teal. if it looks purple, report purple. do NOT blend them
- grid_col: 0=left third, 1=center third, 2=right third of the iris
- grid_row: 0=top third, 1=middle third, 2=bottom third of the iris
- highlights: always return empty array []
- eyeshadow_color: dominant shadow color if present, [0,0,0] if not
- position must be chosen from the exact list provided
"""

    import time
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt
                ]
            )
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 15 * (attempt + 1)  # 15, 30, 45, 60초
                print(f"  API 오류 (시도 {attempt+1}/{max_retries}): {e}")
                print(f"  {wait}초 후 재시도...")
                time.sleep(wait)
            else:
                raise

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    features = json.loads(raw)

    # pupil 색상: OpenCV 직접 샘플링 시도 (랜드마크 신뢰성 검증 후 적용)
    if landmarks_path and Path(landmarks_path).exists():
        iris_colors = sample_iris_colors(image_path, landmarks_path)
        if iris_colors is not None:
            features["pupil"].update(iris_colors)
            print("  홍채 색상: OpenCV 직접 샘플링 완료")
        else:
            print("  홍채 색상: 랜드마크 불안정 → Gemini 추출값 유지")

    return features


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent

    parser = argparse.ArgumentParser()
    parser.add_argument("--image",   default=str(PROJECT_ROOT / "test_face.png"))
    parser.add_argument("--output",  default=str(PROJECT_ROOT / "features.json"))
    args = parser.parse_args()

    print(f"이미지 분석 중: {args.image}\n")
    # landmarks.json 경로 추정 (output 폴더 기준)
    import os
    landmarks_path = os.path.join(os.path.dirname(args.output), "landmarks.json")
    features = extract_face_features(args.image, landmarks_path)

    print("추출된 특징:")
    print(json.dumps(features, indent=2, ensure_ascii=False))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2, ensure_ascii=False)
    print(f"\n{args.output} 저장 완료")