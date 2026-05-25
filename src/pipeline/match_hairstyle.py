"""
Match uploaded image against hair preset thumbnails using Gemini visual comparison.
"""

import argparse
import json
from pathlib import Path
from extract_features import match_hairstyle_preset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to uploaded image")
    parser.add_argument("--thumbnails", required=True, help="Directory containing hair-01.png through hair-05.png")
    parser.add_argument("--output", required=True, help="Path to write JSON result")
    args = parser.parse_args()

    print(f"헤어 프리셋 매칭 중: {args.image}")
    result = match_hairstyle_preset(args.image, args.thumbnails)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"매칭 결과: {json.dumps(result, ensure_ascii=False)}")
