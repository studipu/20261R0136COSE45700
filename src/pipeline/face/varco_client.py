"""
VARCO 3D API client.

Supports VARCO (NCSoft) and Meshy (PoC fallback) providers for image-to-3D GLB generation.

Usage:
    client = get_client("meshy", api_key="...")
    client.image_to_3d("input.png", "output.glb")
"""

import time
import requests
from pathlib import Path


class VarcoClient:
    """
    VARCO 3D API client (NCSoft).

    Auth: openapi_key header
    Image -> 3D: POST /3d/varco/v1/image-to-3d  (PNG only, multipart/form-data)
    Status:      GET  /inference/result/{requestId}
    On success:  download GLB from model_url (valid for 7 days)
    """

    BASE_URL = "https://openapi.ai.nc.com"
    _PATH_SUBMIT = "/3d/varco/v1/image-to-3d"
    _PATH_STATUS = "/inference/result/{request_id}"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "openapi_key": api_key,
        })

    def image_to_3d(
        self,
        image_path: str,
        output_path: str,
        poll_interval: int = 10,
        timeout: int = 300,
    ) -> str:
        image_path = self._ensure_png(
            image_path,
            Path(output_path).parent / "_inputs",
        )
        request_id = self._submit(image_path)
        glb_url = self._poll_until_done(request_id, poll_interval, timeout)
        return self._download_glb(glb_url, output_path)

    def _ensure_png(self, image_path: str, output_dir: Path) -> str:
        """Normalize VARCO input to an RGBA PNG inside the run output directory."""
        from PIL import Image as PILImage

        p = Path(image_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        png_path = output_dir / f"{p.stem}_normalized.png"
        PILImage.open(image_path).convert("RGBA").save(png_path)
        print(f"[VARCO] normalized input saved: {png_path}")
        return str(png_path)

    def _submit(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            resp = self.session.post(
                f"{self.BASE_URL}{self._PATH_SUBMIT}",
                files={"image": (Path(image_path).name, f, "image/png")},
            )
        resp.raise_for_status()
        data = resp.json()
        request_id = data["requestId"]
        print(f"[VARCO] submitted requestId={request_id}")
        return request_id

    def _poll_until_done(self, request_id: str, poll_interval: int, timeout: int) -> str:
        url = f"{self.BASE_URL}{self._PATH_STATUS.format(request_id=request_id)}"
        elapsed = 0
        while elapsed < timeout:
            resp = self.session.get(url)

            if resp.status_code == 202:
                print(f"[VARCO] processing... ({elapsed}s elapsed)")
            elif resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "succeeded":
                    import json as _json
                    print(f"[VARCO] full response: {_json.dumps(data, indent=2, ensure_ascii=False)}")
                    print(f"[VARCO] done model_url={data['model_url']}")
                    return data["model_url"]
            elif resp.status_code == 500:
                raise RuntimeError(f"[VARCO] task failed: {resp.text}")
            else:
                resp.raise_for_status()

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"[VARCO] requestId={request_id} timed out after {timeout}s")

    def _download_glb(self, url: str, output_path: str) -> str:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[VARCO] GLB saved: {output_path}")
        return output_path


class MeshyClient:
    """
    Meshy API client (PoC / VARCO fallback).
    https://docs.meshy.ai/api-image-to-3d

    Free tier: 200 credits/month (1 GLB = 1 credit).
    """

    BASE_URL = "https://api.meshy.ai/v2"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
        })

    def image_to_3d(self, image_path: str, output_path: str, poll_interval: int = 10, timeout: int = 300) -> str:
        image_url = self._upload_image(image_path)
        task_id = self._create_task(image_url)
        glb_url = self._poll_until_done(task_id, poll_interval, timeout)
        return self._download_glb(glb_url, output_path)

    def _upload_image(self, image_path: str) -> str:
        import base64
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        ext = Path(image_path).suffix.lower().lstrip(".")
        mime_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }.get(ext, f"image/{ext}")
        return f"data:{mime_type};base64,{encoded}"

    def _create_task(self, image_url: str) -> str:
        resp = self.session.post(
            f"{self.BASE_URL}/image-to-3d",
            json={
                "image_url": image_url,
                "enable_pbr": True,
                "ai_model": "meshy-4",
            },
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def _poll_until_done(self, task_id: str, poll_interval: int, timeout: int) -> str:
        elapsed = 0
        while elapsed < timeout:
            resp = self.session.get(f"{self.BASE_URL}/image-to-3d/{task_id}")
            resp.raise_for_status()
            data = resp.json()

            status = data["status"]
            progress = data.get("progress", 0)
            print(f"[Meshy] status={status} progress={progress}%")

            if status == "SUCCEEDED":
                return data["model_urls"]["glb"]
            if status in ("FAILED", "EXPIRED"):
                raise RuntimeError(f"Meshy task failed: {data.get('task_error')}")

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Meshy task {task_id} timed out after {timeout}s")

    def _download_glb(self, url: str, output_path: str) -> str:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[Meshy] GLB saved: {output_path}")
        return output_path


def get_client(provider: str = "varco", api_key: str = "") -> "VarcoClient | MeshyClient":
    """Factory function to get the appropriate 3D API client."""
    if provider == "varco":
        return VarcoClient(api_key)
    return MeshyClient(api_key)
