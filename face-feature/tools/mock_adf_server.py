"""
Mock ADF server for testing face-keys pipeline on macOS.

Returns fixed 28-point landmarks for any input image,
enabling end-to-end pipeline verification without the full
anime-face-detector stack (which requires Linux/WSL).

Usage:
    python mock_adf_server.py --port 8000
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Fixed 28-point landmarks (typical anime face, 512x512 image scale)
MOCK_LANDMARKS = {
    "x1": 120.0, "y1": 80.0, "x2": 400.0, "y2": 420.0,
    "score": 0.95,
    "keypoints": [
        # 0-4: face contour [left_edge, left_jaw, chin, right_jaw, right_edge]
        [140.0, 260.0], [180.0, 380.0], [260.0, 410.0], [340.0, 380.0], [380.0, 260.0],
        # 5-7: right brow [outer→inner]
        [160.0, 190.0], [190.0, 185.0], [220.0, 192.0],
        # 8-10: left brow [inner→outer]
        [290.0, 192.0], [320.0, 185.0], [350.0, 190.0],
        # 11-16: right eye upper(11,12,13) + lower(14,15,16)
        [170.0, 220.0], [195.0, 210.0], [220.0, 218.0],
        [170.0, 235.0], [195.0, 240.0], [220.0, 233.0],
        # 17-22: left eye upper(17,18,19) + lower(20,21,22)
        [290.0, 218.0], [315.0, 210.0], [340.0, 220.0],
        [290.0, 233.0], [315.0, 240.0], [340.0, 235.0],
        # 23: nose tip
        [260.0, 310.0],
        # 24-27: mouth [left_corner, top_center, right_corner, bottom_center]
        [230.0, 350.0], [260.0, 342.0], [290.0, 350.0], [260.0, 365.0],
    ],
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") != "/detect":
            self.send_response(404)
            self.end_headers()
            return

        # Read and discard request body
        length = int(self.headers.get("Content-Length", "0"))
        if length > 0:
            self.rfile.read(length)

        payload = json.dumps(MOCK_LANDMARKS).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        print(f"[mock-adf] {format % args}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"ready http://{args.host}:{args.port}")
    print("[mock-adf] Mock ADF server running (fixed landmarks for testing)")
    server.serve_forever()
