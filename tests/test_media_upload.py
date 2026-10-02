import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image

from backend.admin_auth import require_admin_key
from backend.settings import Settings
from tests.db_support import isolated_database
from tests.http_support import order_api


def image_bytes(image_format: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (12, 8), color=(180, 40, 90)).save(output, format=image_format)
    return output.getvalue()


class ProductImageUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.settings = Settings(
            _env_file=None,
            app_env="development",
            media_dir=Path(self.temp_dir.name),
            media_base_url="/media",
        )
        self.settings_patch = patch("backend.routers.media.Settings", return_value=self.settings)
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    @staticmethod
    def upload(base: str, content: bytes, content_type: str) -> tuple[int, dict[str, str]]:
        request = Request(
            base + "/admin/uploads/products",
            data=content,
            headers={"content-type": content_type},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_accepts_and_reencodes_only_supported_raster_formats(self):
        with isolated_database() as engine, order_api(engine) as (base, _):
            for image_format, content_type, extension in (
                ("JPEG", "image/jpeg", ".jpg"),
                ("PNG", "image/png", ".png"),
                ("WEBP", "image/webp", ".webp"),
            ):
                with self.subTest(image_format=image_format):
                    status, body = self.upload(base, image_bytes(image_format), content_type)
                    self.assertEqual(status, 201)
                    image_url = body["image_url"]
                    self.assertRegex(image_url, rf"^/media/products/[0-9a-f]{{32}}{extension}$")
                    saved_path = Path(self.temp_dir.name) / image_url.removeprefix("/media/")
                    with Image.open(saved_path) as saved:
                        self.assertEqual(saved.format, image_format)

    def test_rejects_mime_spoofing_and_oversized_content(self):
        with isolated_database() as engine, order_api(engine) as (base, _):
            status, _ = self.upload(base, b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/png")
            self.assertEqual(status, 400)
            status, _ = self.upload(base, image_bytes("PNG"), "image/jpeg")
            self.assertEqual(status, 415)
            # Oversized upload: server rejects mid-stream. On Windows the
            # connection can reset before the HTTP 413 response is received.
            try:
                status, _ = self.upload(base, b"x" * (5 * 1024 * 1024 + 1), "image/png")
                self.assertEqual(status, 413)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                pass  # Server correctly closed the connection during upload.
            # The critical assertion: no file must have been written to disk.
            product_dir = Path(self.temp_dir.name) / "products"
            saved = list(product_dir.glob("*")) if product_dir.exists() else []
            self.assertEqual(saved, [])

    def test_disables_uploads_in_production_without_persistent_media(self):
        self.settings = Settings(
            _env_file=None,
            app_env="production",
            media_dir=Path(self.temp_dir.name),
            media_persistent_storage=False,
        )
        with isolated_database() as engine, order_api(engine) as (base, _), patch(
            "backend.routers.media.Settings", return_value=self.settings
        ):
            status, _ = self.upload(base, image_bytes("PNG"), "image/png")
            self.assertEqual(status, 503)


if __name__ == "__main__":
    unittest.main()