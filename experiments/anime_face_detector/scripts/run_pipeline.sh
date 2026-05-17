#!/usr/bin/env bash
# Auto-apply face shape from input 3D asset to master VRM
#
# Usage:
#   ./run_pipeline.sh <input_glb> <master_vrm> <output_dir>
#
# Requires:
#   - Blender 4.2+ in PATH (or set $BLENDER)
#   - Python with: torch, torchvision, numpy<2, opencv-python, Pillow
#   - VRM Add-on for Blender enabled
#
# Optional:
#   - Set $BLENDER to Blender exec path
#   - Set $PYTHON to Python interpreter (default: python3)

set -e

INPUT_GLB="${1:?input GLB/VRM required}"
MASTER_VRM="${2:?master VRM required}"
OUTDIR="${3:?output dir required}"

BLENDER="${BLENDER:-blender}"
PYTHON="${PYTHON:-python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
KANO_DIR="$EXP_DIR/kanosawa_repo"

mkdir -p "$OUTDIR"

echo "==================================="
echo " Auto Face Apply Pipeline"
echo "==================================="
echo " Input GLB:   $INPUT_GLB"
echo " Master VRM:  $MASTER_VRM"
echo " Output dir:  $OUTDIR"
echo "==================================="

# Stage 1: Render input front
echo ""
echo "[1/5] Rendering input front view..."
"$BLENDER" --background --python "$SCRIPT_DIR/render_front.py" -- \
    --input "$INPUT_GLB" \
    --output "$OUTDIR/input_front.png" 2>&1 | grep -E "✓|ERROR|Bbox|Face center" || true

# Stage 2: Render master baseline (한 번만 — 캐시 가능)
if [ ! -f "$OUTDIR/master_baseline.png" ] || [ "$REGEN_BASELINE" = "1" ]; then
    echo ""
    echo "[2/5] Rendering master baseline..."
    "$BLENDER" --background --python "$SCRIPT_DIR/render_front.py" -- \
        --input "$MASTER_VRM" \
        --output "$OUTDIR/master_baseline.png" \
        --vrm 2>&1 | grep -E "✓|ERROR|Bbox|Face center" || true
else
    echo ""
    echo "[2/5] Master baseline cached, skipping."
fi

# Stage 3: Measure both
echo ""
echo "[3/5] Extracting landmarks + measurements..."
$PYTHON "$KANO_DIR/measure_face.py" "$OUTDIR/input_front.png" "$OUTDIR/input_measure.json" 2>&1 | grep -v "WARNING\|warn\|UserWarning\|RequestsDep" | tail -5
$PYTHON "$KANO_DIR/measure_face.py" "$OUTDIR/master_baseline.png" "$OUTDIR/master_measure.json" 2>&1 | grep -v "WARNING\|warn\|UserWarning\|RequestsDep" | tail -5

# Stage 4: Compute sliders
echo ""
echo "[4/5] Computing slider values..."
$PYTHON "$KANO_DIR/compute_sliders.py" \
    "$OUTDIR/master_measure.json" \
    "$OUTDIR/input_measure.json" \
    "$OUTDIR/sliders.json" 2>&1 | tail -32

# Stage 5: Apply to master + render
echo ""
echo "[5/5] Applying sliders to master + rendering..."
"$BLENDER" --background --python "$SCRIPT_DIR/apply_sliders.py" -- \
    --master "$MASTER_VRM" \
    --sliders "$OUTDIR/sliders.json" \
    --output "$OUTDIR/master_result.png" 2>&1 | grep -E "✓|ERROR|=|Applied|Face mesh" || true

# Stage 6: Comparison image
echo ""
echo "[+] Building comparison image..."
$PYTHON "$SCRIPT_DIR/make_comparison.py" \
    --input "$OUTDIR/input_front.png" \
    --baseline "$OUTDIR/master_baseline.png" \
    --after "$OUTDIR/master_result.png" \
    --out "$OUTDIR/comparison.png"

echo ""
echo "==================================="
echo " ✓ Done!"
echo "  Input:       $OUTDIR/input_front.png"
echo "  Baseline:    $OUTDIR/master_baseline.png"
echo "  Result:      $OUTDIR/master_result.png"
echo "  Sliders:     $OUTDIR/sliders.json"
echo "  Comparison:  $OUTDIR/comparison.png"
echo "==================================="
