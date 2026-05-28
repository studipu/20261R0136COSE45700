"""
Quantitative hairstyle analysis using OpenCV.

Determines hair preset by measuring:
1. Hair length: how far hair pixels extend below the face (relative to face height)
2. Structural features: ponytail (above head), braid (asymmetric), bob (sharp cutoff)

Uses a robust pixel classification that doesn't depend on precise HSV color matching.
"""

import cv2
import numpy as np
import json
import argparse
from pathlib import Path


def is_hair_pixel(r: int, g: int, b: int) -> bool:
    """
    Simple, robust hair pixel classification for brown/dark hair.
    Works across varying lighting conditions.
    """
    lum = (int(r) + int(g) + int(b)) / 3.0

    # Not white/bright (clothing, background, highlights)
    if lum > 170:
        return False

    # Not very dark (black background)
    if lum < 30:
        return False

    # Not skin-like (high R, moderate G, low B, bright)
    if r > 180 and g > 140 and b > 120 and r > g > b:
        return False

    # Hair is typically warm-toned (R >= B for brown hair)
    # Also allow achromatic (black/gray hair where R ≈ G ≈ B)
    max_ch = max(r, g, b)
    min_ch = min(r, g, b)
    chroma = max_ch - min_ch

    if chroma < 20:
        # Achromatic (gray/black) — could be dark hair
        return lum < 120
    else:
        # Chromatic — must be warm (R dominant or G close to R)
        return r >= b

    return False


def count_hair_at_row(img_rgb: np.ndarray, y: int) -> int:
    """Count hair-like pixels in a single row."""
    if y < 0 or y >= img_rgb.shape[0]:
        return 0
    row = img_rgb[y]
    count = 0
    for x in range(row.shape[0]):
        if is_hair_pixel(row[x, 0], row[x, 1], row[x, 2]):
            count += 1
    return count


def measure_hair_profile(img_rgb: np.ndarray, face_top: int, face_bottom: int,
                         face_cx: int) -> dict:
    """
    Measure hair pixel distribution at various depth levels below the face.
    Returns a profile of hair coverage at each depth.
    """
    h, w = img_rgb.shape[:2]
    face_height = face_bottom - face_top
    if face_height <= 0:
        return {"max_depth": 0, "profile": []}

    profile = []
    # Sample from 0.5x above face to 4x below face bottom
    for depth_10 in range(-5, 45):  # -0.5 to 4.5 in 0.1 steps
        depth = depth_10 / 10.0
        y = face_bottom + int(face_height * depth)
        if y < 0 or y >= h:
            continue
        count = count_hair_at_row(img_rgb, y)
        pct = count / w
        profile.append({"depth": depth, "y": y, "count": count, "pct": round(pct, 4)})

    # Find maximum depth where hair coverage exceeds threshold
    threshold = 0.03  # at least 3% of image width
    max_depth = 0.0
    for entry in profile:
        if entry["pct"] >= threshold:
            max_depth = entry["depth"]

    return {"max_depth": round(max_depth, 1), "profile": profile}


def detect_ponytail(img_rgb: np.ndarray, face_top: int, face_bottom: int,
                    face_cx: int) -> bool:
    """Detect ponytail: concentrated hair mass above the head."""
    h, w = img_rgb.shape[:2]
    face_height = face_bottom - face_top

    # Check region above face (1x face height)
    above_start = max(0, face_top - face_height)
    above_count = 0
    above_total = 0
    for y in range(above_start, face_top):
        for x in range(w):
            r, g, b = img_rgb[y, x]
            above_total += 1
            if is_hair_pixel(r, g, b):
                above_count += 1

    if above_total == 0:
        return False

    above_pct = above_count / above_total

    # Check if it's concentrated (not spread across full width)
    if above_pct < 0.1:
        return False

    # Check concentration: count hair columns
    hair_cols = 0
    for x in range(w):
        col_hair = 0
        for y in range(above_start, face_top):
            if is_hair_pixel(*img_rgb[y, x]):
                col_hair += 1
        if col_hair > (face_top - above_start) * 0.3:
            hair_cols += 1

    spread = hair_cols / w
    # Ponytail: hair above head but concentrated in <50% of width
    return above_pct > 0.15 and spread < 0.5


def detect_asymmetry(img_rgb: np.ndarray, face_bottom: int, face_cx: int) -> float:
    """Measure left/right asymmetry of hair below face (for braid detection)."""
    h, w = img_rgb.shape[:2]
    left_count = 0
    right_count = 0

    for y in range(face_bottom, h):
        for x in range(w):
            if is_hair_pixel(*img_rgb[y, x]):
                if x < face_cx:
                    left_count += 1
                else:
                    right_count += 1

    total = left_count + right_count
    if total < 100:
        return 0.0
    return abs(left_count - right_count) / total


def classify_preset(max_depth: float, has_ponytail: bool, asymmetry: float,
                    gemini_style: str = "", gemini_length: str = "") -> dict:
    """
    Classify into hair preset by combining:
    - OpenCV measurements (max_depth, ponytail, braid) — reliable for quantitative features
    - Gemini classification (style, length) — reliable for qualitative features

    Strategy:
    - OpenCV is definitive when it has strong signal (very long hair, ponytail, braid)
    - Gemini disambiguates when OpenCV can't (e.g., hair-01 vs hair-02 from front view)
    """
    has_braid = asymmetry > 0.35
    gemini_style = gemini_style.lower().replace("-", "_").replace(" ", "_")
    gemini_length = gemini_length.lower()

    scores = {
        "hair-01": 0.0,  # long straight
        "hair-02": 0.0,  # short bob
        "hair-03": 0.0,  # ponytail
        "hair-04": 0.0,  # very long straight
        "hair-05": 0.0,  # short braid
    }

    # === OpenCV structural features (highest priority) ===
    if has_ponytail:
        scores["hair-03"] += 5.0

    if has_braid:
        scores["hair-05"] += 4.0

    # === OpenCV length measurement ===
    if max_depth > 2.0:
        # Very long hair visible below body → definitively hair-04
        scores["hair-04"] += 5.0
    elif max_depth > 1.0:
        # Long hair visible → likely hair-04
        scores["hair-04"] += 3.0
        scores["hair-01"] += 1.0
    elif max_depth <= 0.5:
        # Hair not visible below face → could be short OR long (hidden behind body)
        # Defer to Gemini for disambiguation
        pass

    # === Gemini style classification (disambiguator) ===
    if gemini_style:
        style_map = {
            "long_straight": "hair-01",
            "straight": "hair-01",
            "short_bob": "hair-02",
            "bob": "hair-02",
            "ponytail": "hair-03",
            "very_long_straight": "hair-04",
            "short_braid": "hair-05",
            "braid": "hair-05",
            "twin_tails": "hair-03",
        }
        matched = style_map.get(gemini_style)
        if matched:
            # Gemini style weight: high when OpenCV is ambiguous, low when OpenCV is definitive
            opencv_definitive = max_depth > 2.0 or has_ponytail or has_braid
            gemini_weight = 2.0 if opencv_definitive else 4.0
            scores[matched] += gemini_weight

    if gemini_length:
        length_map = {
            "short": ["hair-02", "hair-05"],
            "medium": ["hair-03", "hair-01"],
            "long": ["hair-01", "hair-04"],
            "very_long": ["hair-04"],
        }
        targets = length_map.get(gemini_length, [])
        for t in targets:
            opencv_definitive = max_depth > 2.0 or has_ponytail or has_braid
            scores[t] += 1.0 if opencv_definitive else 2.0

    # If no signal at all, default to hair-01 (most common)
    if sum(scores.values()) == 0:
        scores["hair-01"] = 1.0

    # Find best match
    best_id = max(scores, key=lambda k: scores[k])
    best_score = scores[best_id]
    total = sum(scores.values())
    confidence = best_score / total if total > 0 else 0

    return {
        "matched_preset": best_id,
        "confidence": round(float(confidence), 3),
        "scores": {k: round(float(v), 2) for k, v in scores.items()},
        "max_depth": float(max_depth),
        "has_ponytail": bool(has_ponytail),
        "has_braid": bool(has_braid),
        "asymmetry": round(float(asymmetry), 3),
    }


def _face_bbox_from_adf(adf_landmarks: list) -> "tuple[int,int,int,int] | None":
    """Extract face bounding box from ADF 28-point landmarks."""
    if not adf_landmarks or len(adf_landmarks) < 5:
        return None
    lm = np.array(adf_landmarks)
    return (
        int(np.min(lm[:, 1])),  # face_top
        int(np.max(lm[:, 1])),  # face_bottom
        int(np.min(lm[:, 0])),  # face_left
        int(np.max(lm[:, 0])),  # face_right
    )


def analyze_hairstyle(image_path: str, landmarks_path: str = None,
                      features_path: str = None,
                      face_keys_path: str = None) -> dict:
    """Main analysis: combines OpenCV measurements with Gemini classification."""
    img = cv2.imread(image_path)
    if img is None:
        return {"matched_preset": None, "confidence": 0, "reason": "failed to load image"}
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img_rgb.shape[:2]

    # Determine face bounding box — prefer ADF face-keys, fall back to kanosawa
    face_top = face_bottom = face_left = face_right = None

    if face_keys_path and Path(face_keys_path).exists():
        with open(face_keys_path) as f:
            fk_data = json.load(f)
        bbox = _face_bbox_from_adf(fk_data.get("adf_landmarks"))
        if bbox:
            face_top, face_bottom, face_left, face_right = bbox

    if face_top is None and landmarks_path and Path(landmarks_path).exists():
        with open(landmarks_path) as f:
            lm_data = json.load(f)
        if lm_data and lm_data[0].get("landmarks"):
            landmarks = lm_data[0]["landmarks"]
            lm_array = np.array(landmarks)
            face_top = int(np.min(lm_array[:, 1]))
            face_bottom = int(np.max(lm_array[:, 1]))
            face_left = int(np.min(lm_array[:, 0]))
            face_right = int(np.max(lm_array[:, 0]))

    if face_top is None:
        return {"matched_preset": None, "confidence": 0, "reason": "no face landmarks found"}

    face_cx = (face_left + face_right) // 2
    face_height = face_bottom - face_top

    print(f"  Face: T={face_top} B={face_bottom} H={face_height} cx={face_cx}")

    # Measure hair length profile
    profile = measure_hair_profile(img_rgb, face_top, face_bottom, face_cx)
    max_depth = profile["max_depth"]
    print(f"  Hair max depth: {max_depth}x face height")

    # Log key profile points
    for entry in profile.get("profile", []):
        if entry["depth"] in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
            print(f"    depth {entry['depth']:.1f}x (y={entry['y']}): {entry['count']} px ({entry['pct']*100:.1f}%)")

    # Detect structural features
    has_ponytail = detect_ponytail(img_rgb, face_top, face_bottom, face_cx)
    asymmetry = detect_asymmetry(img_rgb, face_bottom, face_cx)
    print(f"  Ponytail: {has_ponytail}, Asymmetry: {asymmetry:.3f}")

    # Load Gemini features if available
    gemini_style = ""
    gemini_length = ""
    if features_path and Path(features_path).exists():
        with open(features_path) as f:
            features = json.load(f)
        general = features.get("general", {})
        gemini_style = general.get("hair_style", "")
        gemini_length = general.get("hair_length", "")
        print(f"  Gemini: style={gemini_style}, length={gemini_length}")

    # Classify using combined signals
    result = classify_preset(max_depth, has_ponytail, asymmetry, gemini_style, gemini_length)
    result["reason"] = (
        f"max_depth={max_depth}, ponytail={has_ponytail}, "
        f"asymmetry={asymmetry:.3f}, gemini={gemini_style}/{gemini_length}"
    )

    print(f"  Match: {result['matched_preset']} (confidence={result['confidence']})")
    print(f"  Scores: {result['scores']}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--landmarks", default=None, help="Kanosawa landmarks JSON")
    parser.add_argument("--face-keys", default=None, help="ADF face-keys JSON (preferred over landmarks)")
    parser.add_argument("--features", default=None, help="Gemini features JSON (optional)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    print(f"헤어스타일 분석 중: {args.image}")
    result = analyze_hairstyle(args.image, args.landmarks, args.features,
                               face_keys_path=getattr(args, 'face_keys', None))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"분석 결과: {json.dumps(result, ensure_ascii=False)}")
