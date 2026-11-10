"""Check the app image and its remote Chromium service without a vision API."""

import base64
import os
import unittest
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from webdriver_vision import Capture
from webdriver_vision.encode import encode_image


PAGE = """<!doctype html><style>
html,body{margin:0;padding:0}body{height:1800px;background:rgb(20,60,160)}
#target{width:120px;height:80px;background:rgb(200,30,40)}
</style><div id="target"></div>"""
URL = "data:text/html;charset=utf-8," + quote(PAGE)


class ContainerCaptureTests(unittest.TestCase):
    def capture(self, **options):
        return Capture(
            URL, remote_url="http://browser:4444", window_size=(900, 700), **options
        )

    def test_image_excludes_local_files_and_runs_without_root(self):
        self.assertNotEqual(os.getuid(), 0)
        for path in (
            "/app/.env", "/app/.git", "/app/AGENTS.md",
            "/app/webdriver_vision/docker-context-secret.txt",
        ):
            with self.subTest(path=path):
                self.assertFalse(Path(path).exists())

    def test_viewport(self):
        screenshot = self.capture().take()
        with Image.open(BytesIO(screenshot)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertLess(image.height, 1800)
            self.assertEqual(image.getpixel((10, 10))[:3], (200, 30, 40))

    def test_full_document(self):
        screenshot = self.capture(full_page=True).take()
        with Image.open(BytesIO(screenshot)) as image:
            self.assertEqual(image.height, 1800)
            self.assertEqual(image.getpixel((10, 1700))[:3], (20, 60, 160))

    def test_element_and_jpeg_encoding(self):
        screenshot = self.capture().take(selector="#target")
        encoded = encode_image(screenshot, image_format="jpeg", quality=80)
        with Image.open(BytesIO(base64.b64decode(encoded, validate=True))) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (120, 80))
            for actual, expected in zip(image.getpixel((10, 10)), (200, 30, 40)):
                self.assertLessEqual(abs(actual - expected), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
