"""Tests for vision API requests using in-memory images and mocked HTTP."""

import base64
import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import requests
from PIL import Image

from webdriver_vision import AIClient
from webdriver_vision.client import (
    DEFAULT_PROMPT, AIClientError, AIHTTPError, AIResponseError, AITimeoutError,
)
from webdriver_vision.config import ConfigurationError


class AIClientTests(unittest.TestCase):
    def setUp(self):
        post = patch("webdriver_vision.client.requests.post")
        self.post = post.start()
        self.addCleanup(post.stop)
        self.client = AIClient(
            "https://api.example.invalid/v1/chat/completions",
            "test-key", "test-model", timeout=0.5,
        )
        with Image.new("RGB", (4, 3), "red") as image, BytesIO() as buffer:
            image.save(buffer, "PNG")
            self.screenshot = buffer.getvalue()

    def response(self, document, status_code=200):
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(document).encode("utf-8")
        response._content_consumed = True
        self.post.return_value = response
        return response

    def test_map_connect_and_read_timeouts(self):
        for error in (requests.ConnectTimeout, requests.ReadTimeout):
            with self.subTest(error=error):
                self.post.side_effect = error("private transport details")
                with self.assertRaises(AITimeoutError) as caught:
                    self.client.analyze(self.screenshot)
                self.assertEqual(str(caught.exception), "Vision API request timed out.")

    def test_map_connection_failure_without_transport_details(self):
        self.post.side_effect = requests.ConnectionError("private URL and credentials")
        with self.assertRaises(AIClientError) as caught:
            self.client.analyze(self.screenshot)
        self.assertEqual(str(caught.exception), "Could not connect to the vision API.")

    def test_map_other_transport_errors(self):
        self.post.side_effect = requests.RequestException("private transport details")
        with self.assertRaises(AIClientError) as caught:
            self.client.analyze(self.screenshot)
        self.assertEqual(str(caught.exception), "Vision API request failed.")

    def test_http_errors_include_status_without_response_body(self):
        for status_code in (301, 401, 403, 429, 500, 503):
            with self.subTest(status_code=status_code):
                self.response({"error": "private provider details"}, status_code)
                with self.assertRaises(AIHTTPError) as caught:
                    self.client.analyze(self.screenshot)
                self.assertEqual(caught.exception.status_code, status_code)
                self.assertEqual(
                    str(caught.exception), f"Vision API returned HTTP {status_code}."
                )

    def test_close_http_error_response(self):
        response = self.response({"error": "denied"}, 401)
        with patch.object(response, "close", wraps=response.close) as close:
            with self.assertRaises(AIHTTPError):
                self.client.analyze(self.screenshot)
            close.assert_called_once_with()

    def test_do_not_retry_failed_request(self):
        self.post.side_effect = requests.ReadTimeout("timed out")
        with self.assertRaises(AITimeoutError):
            self.client.analyze(self.screenshot)
        self.post.assert_called_once()

    def test_send_prompt_model_and_png_data_url(self):
        self.response({"choices": [{"message": {"content": "  No visible errors.  "}}]})
        self.assertEqual(self.client.analyze(self.screenshot), "No visible errors.")
        self.post.assert_called_once()
        self.assertEqual(self.post.call_args.args, (self.client.api_url,))
        options = self.post.call_args.kwargs
        self.assertEqual(options["timeout"], 0.5)
        self.assertFalse(options["allow_redirects"])
        self.assertEqual(options["json"]["model"], "test-model")
        message, = options["json"]["messages"]
        self.assertEqual(message["role"], "user")
        text, image = message["content"]
        self.assertEqual(text, {"type": "text", "text": DEFAULT_PROMPT})
        self.assertEqual(image["type"], "image_url")
        prefix, encoded = image["image_url"]["url"].split(",", 1)
        self.assertEqual(prefix, "data:image/png;base64")
        with BytesIO(base64.b64decode(encoded, validate=True)) as buffer:
            with Image.open(buffer) as decoded:
                self.assertEqual(decoded.format, "PNG")
                self.assertEqual(decoded.size, (4, 3))
                self.assertEqual(decoded.getpixel((0, 0)), (255, 0, 0, 255))
        prepared = requests.Request(
            "POST", self.client.api_url, auth=options["auth"]
        ).prepare()
        self.assertEqual(prepared.headers["Authorization"], "Bearer test-key")

    def test_jpeg_payload_matches_encoded_image(self):
        self.client.image_format = "jpeg"
        self.client.quality = 70
        self.response({"choices": [{"message": {"content": "Report"}}]})
        self.client.analyze(self.screenshot)
        content = self.post.call_args.kwargs["json"]["messages"][0]["content"]
        prefix, encoded = content[1]["image_url"]["url"].split(",", 1)
        self.assertEqual(prefix, "data:image/jpeg;base64")
        with BytesIO(base64.b64decode(encoded, validate=True)) as buffer:
            with Image.open(buffer) as decoded:
                self.assertEqual(decoded.format, "JPEG")
                self.assertEqual(decoded.size, (4, 3))

    def test_unicode_prompt_and_report(self):
        self.client.prompt = "Check the café page."
        report = "The café heading overlaps the button."
        self.response({"choices": [{"message": {"content": report}}]})
        self.assertEqual(self.client.analyze(self.screenshot), report)
        content = self.post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertEqual(content[0]["text"], self.client.prompt)

    def test_close_successful_response(self):
        response = self.response({"choices": [{"message": {"content": "Report"}}]})
        with patch.object(response, "close", wraps=response.close) as close:
            self.client.analyze(self.screenshot)
            close.assert_called_once_with()

    def test_invalid_json_is_reported_without_body_and_response_is_closed(self):
        response = self.response({})
        response._content = b"private provider error page"
        with patch.object(response, "close", wraps=response.close) as close:
            with self.assertRaises(AIResponseError) as caught:
                self.client.analyze(self.screenshot)
            self.assertEqual(str(caught.exception), "Vision API returned invalid JSON.")
            close.assert_called_once_with()

    def test_reject_missing_or_non_text_reports(self):
        documents = [None, [], {}, {"choices": []}, {"choices": None}]
        for choice in (None, {}, {"message": None}, {"message": {}}):
            documents.append({"choices": [choice]})
        for report in (None, "", "  ", [], 123, {"text": "Report"}):
            documents.append({"choices": [{"message": {"content": report}}]})
        for document in documents:
            with self.subTest(document=document):
                self.response(document)
                with self.assertRaises(AIResponseError):
                    self.client.analyze(self.screenshot)

    def test_reject_incomplete_completion(self):
        for reason in ("length", "content_filter", "tool_calls"):
            with self.subTest(reason=reason):
                self.response({"choices": [{
                    "message": {"content": "Partial report"}, "finish_reason": reason,
                }]})
                with self.assertRaisesRegex(AIResponseError, "incomplete"):
                    self.client.analyze(self.screenshot)

    def test_return_first_complete_choice(self):
        self.response({"choices": [
            {"message": {"content": "First report"}, "finish_reason": "stop"},
            {"message": {"content": "Second report"}, "finish_reason": "stop"},
        ]})
        self.assertEqual(self.client.analyze(self.screenshot), "First report")

    def test_reject_invalid_images_before_request(self):
        for image, error in ((b"invalid image", ValueError), (None, TypeError)):
            with self.subTest(image=image):
                with self.assertRaises(error):
                    self.client.analyze(image)
        self.post.assert_not_called()

    def test_from_settings_requires_endpoint_credentials_and_model(self):
        ai = {"api_url": self.client.api_url, "api_key": "test-key", "model": "test-model"}
        for field in ai:
            with self.subTest(field=field):
                partial = {key: value for key, value in ai.items() if key != field}
                with self.assertRaisesRegex(ConfigurationError, field):
                    AIClient.from_settings({"ai": partial})
        self.post.assert_not_called()

    def test_from_settings_preserves_input_and_loads_optional_fields(self):
        settings = {
            "ai": {
                "api_url": self.client.api_url, "api_key": "test-key",
                "model": "custom-model", "timeout": 12, "prompt": "Custom prompt",
            },
            "screenshot": {"format": "jpeg", "quality": 70},
        }
        original = json.dumps(settings)
        client = AIClient.from_settings(settings)
        self.assertEqual(client.model, "custom-model")
        self.assertEqual(client.timeout, 12)
        self.assertEqual(client.prompt, "Custom prompt")
        self.assertEqual((client.image_format, client.quality), ("jpeg", 70))
        self.assertEqual(json.dumps(settings), original)

    def test_from_config_uses_environment_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text(
                f"ai:\n  api_url: {self.client.api_url}\n"
                "  api_key: ${AI_API_KEY}\n  model: test-model\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"AI_API_KEY": "environment-key"}):
                client = AIClient.from_config(path)
        self.response({"choices": [{"message": {"content": "Report"}}]})
        client.analyze(self.screenshot)
        prepared = requests.Request(
            "POST", client.api_url, auth=self.post.call_args.kwargs["auth"]
        ).prepare()
        self.assertEqual(prepared.headers["Authorization"], "Bearer environment-key")

    def test_reject_header_injection_and_embedded_url_credentials(self):
        for api_key in ("key\nheader", "key with space", "café"):
            with self.subTest(api_key=api_key):
                with self.assertRaises(ConfigurationError):
                    AIClient(self.client.api_url, api_key, "test-model")
        with self.assertRaisesRegex(ConfigurationError, "credentials"):
            AIClient("https://user:password@example.com/v1", "test-key", "test-model")
        self.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
