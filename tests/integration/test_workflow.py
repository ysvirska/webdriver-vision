"""Exercise the CLI with real encoding, configuration, and local HTTP requests."""

import base64
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

import yaml
from PIL import Image

from webdriver_vision.__main__ import main


class VisionHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        body = b"""<!doctype html><style>
        html,body{margin:0;padding:0}body{height:1800px;background:rgb(20,60,160)}
        #target{width:120px;height:80px;background:rgb(200,30,40)}
        #delayed{display:none;width:90px;height:60px;background:rgb(20,190,40)}
        </style><div id="target"></div><div id="delayed"></div>
        <script>setTimeout(()=>document.querySelector('#delayed').style.display='block',200)</script>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.received.append({
            "path": self.path,
            "authorization": self.headers.get("Authorization"),
            "payload": payload,
        })
        body = self.server.response_body
        self.send_response(self.server.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Location", "/redirected-endpoint")
        self.end_headers()
        self.wfile.write(body)


class LocalVisionServer(ThreadingHTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), VisionHandler)
        self.received = []
        self.status_code = 200
        self.response_body = json.dumps({"choices": [{
            "message": {"content": "Local test report."}, "finish_reason": "stop",
        }]}).encode("utf-8")


class WorkflowFixture(unittest.TestCase):
    def setUp(self):
        self.server = LocalVisionServer()
        self.addCleanup(self.server.server_close)
        worker = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01}, daemon=True,
        )
        worker.start()
        self.addCleanup(worker.join)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config_path = Path(directory.name) / "config.yaml"
        environment = patch.dict(os.environ, {
            "AI_API_KEY": "integration-test-key",
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.write_config()

    def write_config(self, image_format="png", full_page=False):
        self.settings = {
            "browser": {"headless": True, "window_size": [900, 700]},
            "screenshot": {"format": image_format, "quality": 80, "full_page": full_page},
            "ai": {
                "api_url": f"{self.url}/v1/chat/completions",
                "api_key": "${AI_API_KEY}", "model": "test-model",
                "prompt": "Check the test page.", "timeout": 5,
            },
        }
        self.config_path.write_text(yaml.safe_dump(self.settings), encoding="utf-8")

    def run_cli(self, *flags):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main([
                "--url", f"{self.url}/fixture", "--config", str(self.config_path),
                *flags,
            ])
        return code, stdout.getvalue(), stderr.getvalue()

    def received_image(self):
        self.assertEqual(len(self.server.received), 1)
        request, = self.server.received
        self.assertEqual(request["path"], "/v1/chat/completions")
        self.assertEqual(request["authorization"], "Bearer integration-test-key")
        payload = request["payload"]
        self.assertEqual(payload["model"], "test-model")
        message, = payload["messages"]
        self.assertEqual(message["role"], "user")
        text, image = message["content"]
        self.assertEqual(text, {"type": "text", "text": "Check the test page."})
        prefix, encoded = image["image_url"]["url"].split(",", 1)
        return prefix, base64.b64decode(encoded, validate=True)


class WorkflowTests(WorkflowFixture):
    def setUp(self):
        super().setUp()
        chrome = patch("webdriver_vision.capture.webdriver.Chrome")
        self.chrome = chrome.start()
        self.addCleanup(chrome.stop)
        self.driver = self.chrome.return_value
        with Image.new("RGBA", (16, 12), (0, 0, 255, 128)) as image, BytesIO() as buffer:
            image.save(buffer, "PNG")
            self.source = buffer.getvalue()
        self.driver.get_screenshot_as_png.return_value = self.source

    def test_page_capture_to_report_over_http(self):
        self.assertEqual(self.run_cli(), (0, "Local test report.\n", ""))
        prefix, data = self.received_image()
        self.assertEqual(prefix, "data:image/png;base64")
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.size, (16, 12))
            self.assertEqual(image.getpixel((0, 0)), (0, 0, 255, 128))
        self.driver.get.assert_called_once_with(f"{self.url}/fixture")
        self.driver.quit.assert_called_once_with()

    def test_element_capture_to_jpeg_report_over_http(self):
        self.write_config(image_format="jpeg")
        element = self.driver.find_element.return_value
        element.is_displayed.return_value = True
        element.screenshot_as_png = self.source
        self.assertEqual(
            self.run_cli("--selector", "#target"), (0, "Local test report.\n", "")
        )
        prefix, data = self.received_image()
        self.assertEqual(prefix, "data:image/jpeg;base64")
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (16, 12))
            for actual, expected in zip(image.getpixel((0, 0)), (127, 127, 255)):
                self.assertLessEqual(abs(actual - expected), 3)
        self.driver.get_screenshot_as_png.assert_not_called()
        self.driver.quit.assert_called_once_with()

    def test_authentication_failure_keeps_private_details_out_of_output(self):
        self.server.status_code = 401
        self.server.response_body = b'{"error":"private provider body"}'
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stdout), (1, ""))
        self.assertIn("HTTP 401", stderr)
        self.assertIn("AI_API_KEY", stderr)
        self.assertNotIn("integration-test-key", stderr)
        self.assertNotIn("private provider body", stderr)
        self.driver.quit.assert_called_once_with()

    def test_invalid_config_prevents_capture_and_http_request(self):
        del self.settings["ai"]["model"]
        self.config_path.write_text(yaml.safe_dump(self.settings), encoding="utf-8")
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("ai.model is required", stderr)
        self.chrome.assert_not_called()
        self.assertEqual(self.server.received, [])

    def test_invalid_json_response_is_handled(self):
        self.server.response_body = b"not JSON"
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stdout), (1, ""))
        self.assertIn("invalid or incomplete", stderr)
        self.driver.quit.assert_called_once_with()

    def test_http_redirect_is_not_followed(self):
        self.server.status_code = 302
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stdout), (1, ""))
        self.assertIn("redirects are not followed", stderr)
        self.assertEqual(len(self.server.received), 1)
        self.driver.quit.assert_called_once_with()


@unittest.skipUnless(
    os.environ.get("WEBDRIVER_VISION_BROWSER_TESTS") == "1",
    "Set WEBDRIVER_VISION_BROWSER_TESTS=1 to run real Chrome tests.",
)
class BrowserWorkflowTests(WorkflowFixture):
    def test_delayed_element_capture_to_report(self):
        self.write_config(image_format="jpeg")
        code, stdout, stderr = self.run_cli("--selector", "#delayed")
        self.assertEqual((code, stdout), (0, "Local test report.\n"), stderr)
        prefix, data = self.received_image()
        self.assertEqual(prefix, "data:image/jpeg;base64")
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.size, (90, 60))
            for actual, expected in zip(image.getpixel((10, 10)), (20, 190, 40)):
                self.assertLessEqual(abs(actual - expected), 3)

    def test_full_document_capture_to_report(self):
        self.write_config(full_page=True)
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stdout), (0, "Local test report.\n"), stderr)
        prefix, data = self.received_image()
        self.assertEqual(prefix, "data:image/png;base64")
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.height, 1800)
            self.assertEqual(image.getpixel((10, 1700))[:3], (20, 60, 160))


if __name__ == "__main__":
    unittest.main()
