"""Tests for vision API requests using in-memory images and mocked HTTP."""

import json
import unittest
from io import BytesIO
from unittest.mock import patch

import requests
from PIL import Image

from webdriver_vision import AIClient
from webdriver_vision.client import AIClientError, AIHTTPError, AITimeoutError


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


if __name__ == "__main__":
    unittest.main()
