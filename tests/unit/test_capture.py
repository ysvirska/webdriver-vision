"""Tests for Chrome screenshot capture without starting a browser."""

import base64
import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import (
    InvalidSelectorException,
    NoSuchElementException,
    SessionNotCreatedException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_vision import Capture


class CaptureTests(unittest.TestCase):
    def setUp(self):
        chrome = patch("webdriver_vision.capture.webdriver.Chrome")
        self.chrome = chrome.start()
        self.addCleanup(chrome.stop)
        self.driver = self.chrome.return_value
        self.driver.get_screenshot_as_png.return_value = b"screenshot"

    def test_close_after_successful_capture(self):
        self.assertEqual(Capture("https://example.com").take(), b"screenshot")
        self.driver.quit.assert_called_once_with()

    def test_close_after_setup_navigation_and_screenshot_failures(self):
        for operation in (
            "set_window_size", "set_page_load_timeout", "get", "get_screenshot_as_png"
        ):
            with self.subTest(operation=operation):
                driver = Mock()
                self.chrome.return_value = driver
                error = WebDriverException("Capture failed.")
                getattr(driver, operation).side_effect = error
                with self.assertRaises(WebDriverException) as caught:
                    Capture("https://example.com").take()
                self.assertIs(caught.exception, error)
                driver.quit.assert_called_once_with()

    def test_cleanup_error_does_not_mask_capture_error(self):
        error = WebDriverException("Navigation failed.")
        self.driver.get.side_effect = error
        self.driver.quit.side_effect = WebDriverException("Cleanup failed.")
        with self.assertRaises(WebDriverException) as caught:
            Capture("https://example.com").take()
        self.assertIs(caught.exception, error)
        self.driver.quit.assert_called_once_with()

    def test_cleanup_error_after_success_is_reported(self):
        error = WebDriverException("Cleanup failed.")
        self.driver.quit.side_effect = error
        with self.assertRaises(WebDriverException) as caught:
            Capture("https://example.com").take()
        self.assertIs(caught.exception, error)

    def test_interrupt_closes_browser_and_propagates(self):
        error = KeyboardInterrupt()
        self.driver.get.side_effect = error
        with self.assertRaises(KeyboardInterrupt) as caught:
            Capture("https://example.com").take()
        self.assertIs(caught.exception, error)
        self.driver.quit.assert_called_once_with()

    def test_driver_startup_error_propagates(self):
        error = SessionNotCreatedException("Chrome could not start.")
        self.chrome.side_effect = error
        with self.assertRaises(SessionNotCreatedException) as caught:
            Capture("https://example.com").take()
        self.assertIs(caught.exception, error)
        self.driver.quit.assert_not_called()

    def test_capture_visible_element(self):
        element = self.driver.find_element.return_value
        element.is_displayed.return_value = True
        element.screenshot_as_png = b"element screenshot"
        screenshot = Capture("https://example.com").take(selector="#message")
        self.assertEqual(screenshot, b"element screenshot")
        self.driver.find_element.assert_called_once_with(By.CSS_SELECTOR, "#message")
        self.driver.get_screenshot_as_png.assert_not_called()
        self.driver.quit.assert_called_once_with()

    def test_element_timeout_closes_browser(self):
        error = TimeoutException("Element did not become visible.")
        with patch("webdriver_vision.capture.WebDriverWait") as wait:
            wait.return_value.until.side_effect = error
            with self.assertRaises(TimeoutException) as caught:
                Capture("https://example.com", timeout=0.5).take(selector="#missing")
            wait.assert_called_once_with(self.driver, 0.5)
        self.assertIs(caught.exception, error)
        self.driver.quit.assert_called_once_with()

    def test_element_cannot_be_combined_with_full_page_capture(self):
        with self.assertRaisesRegex(ValueError, "full_page"):
            Capture("https://example.com", full_page=True).take(selector="#message")
        self.chrome.assert_not_called()

    def test_browser_options_and_navigation_order(self):
        for headless in (True, False):
            with self.subTest(headless=headless):
                self.driver.reset_mock()
                Capture(
                    "https://example.com", headless=headless,
                    window_size=(800, 600), timeout=12,
                ).take()
                options = self.chrome.call_args.kwargs["options"]
                self.assertEqual("--headless=new" in options.arguments, headless)
                operations = [call[0] for call in self.driver.method_calls]
                self.assertEqual(operations, [
                    "set_window_size", "set_page_load_timeout", "get",
                    "get_screenshot_as_png", "quit",
                ])
                self.driver.set_window_size.assert_called_once_with(800, 600)
                self.driver.set_page_load_timeout.assert_called_once_with(12)
                self.driver.get.assert_called_once_with("https://example.com")

    def test_window_size_is_copied_from_caller(self):
        window_size = [800, 600]
        capture = Capture("https://example.com", window_size=window_size)
        window_size[0] = 1
        capture.take()
        self.driver.set_window_size.assert_called_once_with(800, 600)

    def test_each_capture_uses_a_fresh_driver(self):
        first, second = Mock(), Mock()
        first.get_screenshot_as_png.return_value = b"first"
        second.get_screenshot_as_png.return_value = b"second"
        self.chrome.side_effect = [first, second]
        capture = Capture("https://example.com")
        self.assertEqual(capture.take(), b"first")
        self.assertEqual(capture.take(), b"second")
        first.quit.assert_called_once_with()
        second.quit.assert_called_once_with()

    def test_full_page_uses_document_dimensions_in_css_pixels(self):
        content = {"x": 0, "y": 0, "width": 885.5, "height": 1800.25}
        screenshot = b"full-page PNG bytes"
        self.driver.execute_cdp_cmd.side_effect = [
            {"cssContentSize": content, "contentSize": {"width": 1771}},
            {"data": base64.b64encode(screenshot).decode("ascii")},
        ]
        self.assertEqual(
            Capture("https://example.com", full_page=True).take(), screenshot
        )
        calls = self.driver.execute_cdp_cmd.call_args_list
        self.assertEqual(calls[0].args, ("Page.getLayoutMetrics", {}))
        self.assertEqual(calls[1].args, (
            "Page.captureScreenshot",
            {
                "format": "png", "fromSurface": True,
                "captureBeyondViewport": True, "clip": {**content, "scale": 1},
            },
        ))
        self.driver.get_screenshot_as_png.assert_not_called()
        self.driver.quit.assert_called_once_with()

    def test_full_page_protocol_errors_close_browser(self):
        error = WebDriverException("Chrome DevTools command failed.")
        for responses in ([error], [{"cssContentSize": {}}, error]):
            with self.subTest(responses=responses):
                self.driver.reset_mock()
                self.driver.execute_cdp_cmd.side_effect = responses
                with self.assertRaises(WebDriverException) as caught:
                    Capture("https://example.com", full_page=True).take()
                self.assertIs(caught.exception, error)
                self.driver.quit.assert_called_once_with()

    def test_invalid_protocol_image_data_closes_browser(self):
        self.driver.execute_cdp_cmd.side_effect = [
            {"cssContentSize": {}}, {"data": "invalid base64!"},
        ]
        with self.assertRaises(ValueError):
            Capture("https://example.com", full_page=True).take()
        self.driver.quit.assert_called_once_with()

    def test_wait_for_missing_then_hidden_element_to_become_visible(self):
        hidden, visible = Mock(), Mock()
        hidden.is_displayed.return_value = False
        visible.is_displayed.return_value = True
        visible.screenshot_as_png = b"visible element"
        self.driver.find_element.side_effect = [
            NoSuchElementException("Not yet in the DOM."), hidden, visible,
        ]
        with patch(
            "webdriver_vision.capture.WebDriverWait",
            side_effect=lambda driver, timeout: WebDriverWait(
                driver, timeout, poll_frequency=0.001
            ),
        ):
            screenshot = Capture("https://example.com").take(selector="#delayed")
        self.assertEqual(screenshot, b"visible element")
        self.assertEqual(self.driver.find_element.call_count, 3)
        self.driver.quit.assert_called_once_with()

    def test_invalid_css_error_propagates_and_closes_browser(self):
        error = InvalidSelectorException("Invalid CSS selector.")
        self.driver.find_element.side_effect = error
        with self.assertRaises(InvalidSelectorException) as caught:
            Capture("https://example.com").take(selector="[")
        self.assertIs(caught.exception, error)
        self.driver.quit.assert_called_once_with()

    def test_reject_invalid_selectors_before_browser_start(self):
        for selector in ("", "  ", 123, []):
            with self.subTest(selector=selector):
                with self.assertRaisesRegex(ValueError, "selector"):
                    Capture("https://example.com").take(selector=selector)
        self.chrome.assert_not_called()

    def test_reject_invalid_settings_before_browser_start(self):
        for settings in (
            {"url": ""}, {"url": "  "}, {"url": None},
            {"headless": "false"}, {"full_page": 1},
            {"window_size": None}, {"window_size": "800,600"},
            {"window_size": [800]}, {"window_size": [True, 600]},
            {"window_size": [800, 0]}, {"timeout": 0},
            {"timeout": True}, {"timeout": "30"},
            {"timeout": float("inf")}, {"timeout": float("nan")},
        ):
            with self.subTest(settings=settings):
                arguments = {"url": "https://example.com", **settings}
                with self.assertRaises(ValueError):
                    Capture(**arguments)
        self.chrome.assert_not_called()

    def test_remote_capture_uses_grid_instead_of_local_chrome(self):
        with patch("webdriver_vision.capture.webdriver.Remote") as remote:
            driver = remote.return_value
            driver.get_screenshot_as_png.return_value = b"remote screenshot"
            result = Capture(
                "https://example.com", remote_url="http://browser:4444"
            ).take()
            self.assertEqual(result, b"remote screenshot")
            self.assertEqual(
                remote.call_args.kwargs["command_executor"], "http://browser:4444"
            )
            self.assertIn("--headless=new", remote.call_args.kwargs["options"].arguments)
            driver.quit.assert_called_once_with()
        self.chrome.assert_not_called()

    def test_remote_capture_failure_closes_session(self):
        with patch("webdriver_vision.capture.webdriver.Remote") as remote:
            driver = remote.return_value
            error = WebDriverException("Remote navigation failed.")
            driver.get.side_effect = error
            driver.quit.side_effect = WebDriverException("Remote cleanup failed.")
            with self.assertRaises(WebDriverException) as caught:
                Capture("https://example.com", remote_url="http://browser:4444").take()
            self.assertIs(caught.exception, error)
            driver.quit.assert_called_once_with()
        self.chrome.assert_not_called()

    def test_remote_full_page_capture_decodes_protocol_response(self):
        with patch("webdriver_vision.capture.webdriver.Remote") as remote:
            driver = remote.return_value
            driver.execute_cdp_cmd.side_effect = [
                {"cssContentSize": {"x": 0, "y": 0, "width": 800, "height": 1800}},
                {"data": base64.b64encode(b"full-page image").decode("ascii")},
            ]
            result = Capture(
                "https://example.com", remote_url="http://browser:4444", full_page=True
            ).take()
            self.assertEqual(result, b"full-page image")
            self.assertEqual(driver.execute_cdp_cmd.call_count, 2)
            driver.quit.assert_called_once_with()

    def test_reject_invalid_remote_url_before_browser_start(self):
        with patch("webdriver_vision.capture.webdriver.Remote") as remote:
            for url in ("", "browser:4444", "ftp://browser", 123):
                with self.subTest(url=url):
                    with self.assertRaisesRegex(ValueError, "browser.remote_url"):
                        Capture("https://example.com", remote_url=url)
            remote.assert_not_called()
        self.chrome.assert_not_called()


if __name__ == "__main__":
    unittest.main()
