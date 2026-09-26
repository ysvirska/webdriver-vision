"""Tests for Chrome screenshot capture without starting a browser."""

import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import (
    SessionNotCreatedException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By

from webdriver_vision import Capture


class CaptureCleanupTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
