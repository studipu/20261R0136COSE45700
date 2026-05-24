#!/usr/bin/env bash
# Texture Generation Pipeline
#
# Usage:
#   ./run_pipeline.sh [input_dir] [output_dir]
#
# Requires:
#   - Python with: google-genai, opencv-python, numpy, Pillow, torch, torchvision
#   - GEMINI_API_KEY set in .env file
#
# Optional:
#   - Set $PYTHON to Python interpreter (default: venv/bin/python3 or python3)

set -e

INPUT_DIR="${1:-input}"
OUTPUT_DIR="${2:-output}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
KANOSAWA_DIR="$SCRIPT_DIR/kanosawa_repo"

# 가상환경이 있으면 우선 사용, 없으면 시스템 python3
if [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
    PYTHON="${PYTHON:-$SCRIPT_DIR/venv/bin/python3}"
else
    PYTHON="${PYTHON:-python3}"
fi

if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: 입력 폴더를 찾을 수 없습니다: $INPUT_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
mkdir -p "$SCRIPT_DIR/debug"

# input 폴더의 이미지 파일 목록 수집
IMAGE_FILES=()
for ext in png jpg jpeg PNG JPG JPEG; do
    while IFS= read -r f; do
        IMAGE_FILES+=("$f")
    done < <(find "$INPUT_DIR" -maxdepth 1 -name "*.${ext}" 2>/dev/null)
done

if [ ${#IMAGE_FILES[@]} -eq 0 ]; then
    echo "ERROR: $INPUT_DIR 에 이미지 파일이 없습니다."
    exit 1
fi

echo "==================================="
echo " Texture Generation Pipeline"
echo "==================================="
echo " Input dir:  $INPUT_DIR"
echo " Output dir: $OUTPUT_DIR"
echo " 처리할 이미지: ${#IMAGE_FILES[@]}개"
echo "==================================="

# 각 이미지 처리
for INPUT_IMAGE in "${IMAGE_FILES[@]}"; do
    # 확장자 제외한 파일명 추출
    BASENAME=$(basename "$INPUT_IMAGE")
    FILENAME="${BASENAME%.*}"

    IMAGE_OUTPUT_DIR="$OUTPUT_DIR/$FILENAME"
    LANDMARKS_JSON="$IMAGE_OUTPUT_DIR/landmarks.json"
    FEATURES_JSON="$IMAGE_OUTPUT_DIR/features.json"

    mkdir -p "$IMAGE_OUTPUT_DIR"

    echo ""
    echo "==================================="
    echo " 처리 중: $BASENAME"
    echo " 출력:    $IMAGE_OUTPUT_DIR"
    echo "==================================="

    # Stage 1: Landmark 추출
    echo "[1/3] Extracting landmarks..."
    $PYTHON "$KANOSAWA_DIR/extract_landmarks.py" \
        "$INPUT_IMAGE" \
        "$SCRIPT_DIR/debug/${FILENAME}_landmark.png" \
        --landmarks_json "$LANDMARKS_JSON" 2>&1 | grep -E "✓|ERROR|Cascade|Face" || true

    # Stage 2: 얼굴 특징 추출 (Gemini)
    echo "[2/3] Extracting face features (Gemini API)..."
    $PYTHON "$SRC_DIR/extract_features.py" \
        --image "$INPUT_IMAGE" \
        --output "$FEATURES_JSON"

    # Stage 3: 텍스처 보정
    echo "[3/3] Adjusting textures..."
    $PYTHON "$SRC_DIR/adjust_texture.py" \
        --features "$FEATURES_JSON" \
        --input_dir "$SCRIPT_DIR/assets/textures" \
        --output_dir "$IMAGE_OUTPUT_DIR"

    echo "✓ 완료: $FILENAME"
done

echo ""
echo "==================================="
echo " ✓ 전체 완료!"
echo " 결과 폴더: $OUTPUT_DIR"
echo "==================================="