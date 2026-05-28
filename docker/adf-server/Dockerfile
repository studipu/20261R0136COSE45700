FROM --platform=linux/amd64 python:3.10-slim

# System dependencies for OpenCV headless + C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# PyTorch CPU-only (amd64 wheels)
RUN pip install --no-cache-dir \
    torch==1.13.1+cpu torchvision==0.14.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Pin numpy < 2 (required for PyTorch 1.13 compat)
RUN pip install --no-cache-dir "numpy<2"

# Install pycocotools FIRST (pre-built wheel, avoids mmpycocotools build issues)
RUN pip install --no-cache-dir pycocotools

# mmcv-full: use pre-built wheel from OpenMMLab (skip mim to avoid mmtrack mess)
RUN pip install --no-cache-dir \
    mmcv-full==1.7.0 \
    -f https://download.openmmlab.com/mmcv/dist/cpu/torch1.13.0/index.html

# mmdet + mmpose (skip heavy optional deps like mmtrack)
RUN pip install --no-cache-dir \
    mmdet==2.28.2 \
    mmpose==0.29.0 \
    --no-deps

# Install actual required deps for mmdet/mmpose (without mmtrack)
# Pin numpy<2 here too — scipy/matplotlib will otherwise pull numpy 2.x
RUN pip install --no-cache-dir \
    "numpy<2" \
    scipy matplotlib terminaltables \
    json-tricks xtcocotools munkres chumpy \
    yapf addict

# anime-face-detector
RUN pip install --no-cache-dir anime-face-detector==0.0.9 --no-deps

# Copy server script
COPY anime_bbox.py /app/anime_bbox.py

WORKDIR /app

EXPOSE 8000

CMD ["python", "anime_bbox.py", "--http-server", "--host", "0.0.0.0", "--port", "8000", "--device", "cpu"]
