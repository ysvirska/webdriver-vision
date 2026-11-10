"""Tests for command-line orchestration without Chrome or API requests."""

import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from urllib3.exceptions import MaxRetryError

from selenium.common.exceptions import (
    InvalidSelectorException, TimeoutException, WebDriverException,
)

from webdriver_vision.__main__ import main
from webdriver_vision.client import (
    AIClientError, AIHTTPError, AIResponseError, AITimeoutError,
)
from webdriver_vision.config import ConfigurationError


class CLITests(unittest.TestCase):
    def setUp(self):
        for name in ("load_config", "AIClient", "Capture"):
            patcher = patch(f"webdriver_vision.__main__.{name}")
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.load_config.return_value = {}
        self.Capture.return_value.take.return_value = b"screenshot"
        self.client = self.AIClient.from_settings.return_value
        self.client.analyze.return_value = "No visible errors."

    def run_cli(self, *arguments):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = main(list(arguments))
            except SystemExit as error:
                code = error.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_default_workflow_prints_only_report(self):
        self.assertEqual(
            self.run_cli("--url", "https://example.com"),
            (0, "No visible errors.\n", ""),
        )
        self.load_config.assert_called_once_with("config.yaml")
        self.AIClient.from_settings.assert_called_once_with({})
        self.Capture.assert_called_once_with(
            "https://example.com", headless=True, window_size=(1920, 1080),
            full_page=False, timeout=30, remote_url=None,
        )
        self.Capture.return_value.take.assert_called_once_with(selector=None)
        self.client.analyze.assert_called_once_with(b"screenshot")

    def test_use_browser_and_screenshot_settings_from_yaml(self):
        self.load_config.return_value = {
            "browser": {"headless": False, "window_size": [800, 600]},
            "screenshot": {"full_page": True},
        }
        code, _, _ = self.run_cli(
            "--url", "https://example.com", "--config", "custom.yaml"
        )
        self.assertEqual(code, 0)
        self.load_config.assert_called_once_with("custom.yaml")
        self.Capture.assert_called_once_with(
            "https://example.com", headless=False, window_size=[800, 600],
            full_page=True, timeout=30, remote_url=None,
        )

    def test_command_line_flags_override_yaml_including_false(self):
        self.load_config.return_value = {
            "browser": {"headless": False, "window_size": [800, 600]},
            "screenshot": {"full_page": True},
        }
        code, _, _ = self.run_cli(
            "--url", "https://example.com", "--headless", "--no-full-page",
            "--window-size", "640", "480", "--capture-timeout", "5",
            "--selector", "#alert",
        )
        self.assertEqual(code, 0)
        self.Capture.assert_called_once_with(
            "https://example.com", headless=True, window_size=[640, 480],
            full_page=False, timeout=5, remote_url=None,
        )
        self.Capture.return_value.take.assert_called_once_with(selector="#alert")

    def test_invalid_api_settings_prevent_browser_start(self):
        self.AIClient.from_settings.side_effect = ConfigurationError("ai.model is required.")
        code, stdout, stderr = self.run_cli("--url", "https://example.com")
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Error:", stderr)
        self.Capture.assert_not_called()

    def test_reject_invalid_arguments_before_loading_config(self):
        for arguments in (
            [], ["--url", ""], ["--url", "example.com"],
            ["--url", "file:///tmp/page.html"], ["--url", "https://bad host"],
            ["--url", "http://example.com:wrong"], ["--url", "https://["],
            ["--url", "https://example.com", "--window-size", "0", "600"],
            ["--url", "https://example.com", "--window-size", "800", "-1"],
            ["--url", "https://example.com", "--capture-timeout", "nan"],
            ["--url", "https://example.com", "--capture-timeout", "inf"],
            ["--url", "https://example.com", "--capture-timeout", "0"],
            ["--url", "https://example.com", "--selector", "  "],
            ["--url", "https://example.com", "--remote-url", "invalid"],
        ):
            with self.subTest(arguments=arguments):
                code, stdout, stderr = self.run_cli(*arguments)
                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertIn("error:", stderr)
        self.load_config.assert_not_called()
        self.Capture.assert_not_called()

    def test_file_and_yaml_errors_do_not_start_browser(self):
        for error, message in (
            (FileNotFoundError("private path"), "not found"),
            (PermissionError("private path"), "Could not read"),
            (UnicodeError("private contents"), "UTF-8"),
            (ConfigurationError("Invalid YAML."), "Invalid YAML"),
        ):
            with self.subTest(error=error):
                self.load_config.side_effect = error
                code, stdout, stderr = self.run_cli("--url", "https://example.com")
                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertIn(message, stderr)
                self.assertNotIn("private", stderr)
        self.Capture.assert_not_called()

    def test_conflicting_element_and_full_page_options_do_not_start_browser(self):
        for settings, flags in (
            ({}, ["--full-page"]),
            ({"screenshot": {"full_page": True}}, []),
        ):
            with self.subTest(settings=settings):
                self.load_config.return_value = settings
                code, stdout, stderr = self.run_cli(
                    "--url", "https://example.com", "--selector", "#target", *flags
                )
                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertIn("cannot be combined", stderr)
        self.Capture.assert_not_called()

    def test_http_status_messages_are_actionable(self):
        for status, hint in (
            (301, "ai.api_url"), (400, "endpoint"), (401, "AI_API_KEY"),
            (403, "model access"), (429, "quota"), (503, "try again later"),
        ):
            with self.subTest(status=status):
                self.client.analyze.side_effect = AIHTTPError(status)
                code, stdout, stderr = self.run_cli("--url", "https://example.com")
                self.assertEqual(code, 1)
                self.assertEqual(stdout, "")
                self.assertIn(str(status), stderr)
                self.assertIn(hint, stderr)

    def test_api_errors_are_reported_without_private_details(self):
        for error, message in (
            (AITimeoutError("private key"), "ai.timeout"),
            (AIResponseError("private response"), "invalid or incomplete"),
            (AIClientError("private URL"), "connectivity"),
        ):
            with self.subTest(error=error):
                self.client.analyze.side_effect = error
                code, stdout, stderr = self.run_cli("--url", "https://example.com")
                self.assertEqual(code, 1)
                self.assertEqual(stdout, "")
                self.assertIn(message, stderr)
                self.assertNotIn("private", stderr)
                self.assertNotIn("Traceback", stderr)

    def test_browser_errors_are_reported_without_stack_traces(self):
        for error, message in (
            (TimeoutException("private URL"), "timed out"),
            (InvalidSelectorException("private selector"), "Invalid CSS selector"),
            (WebDriverException("private stack trace"), "ChromeDriver"),
            (MaxRetryError(None, "private URL"), "remote-url"),
        ):
            with self.subTest(error=error):
                self.Capture.return_value.take.side_effect = error
                code, stdout, stderr = self.run_cli("--url", "https://example.com")
                self.assertEqual(code, 1)
                self.assertEqual(stdout, "")
                self.assertIn(message, stderr)
                self.assertNotIn("private", stderr)
        self.client.analyze.assert_not_called()

    def test_remote_url_from_config_can_be_overridden_by_flag(self):
        self.load_config.return_value = {"browser": {"remote_url": "http://grid:4444"}}
        for flags, expected in (
            ([], "http://grid:4444"),
            (["--remote-url", "http://other-grid:4444"], "http://other-grid:4444"),
        ):
            with self.subTest(flags=flags):
                code, _, _ = self.run_cli("--url", "https://example.com", *flags)
                self.assertEqual(code, 0)
                self.assertEqual(self.Capture.call_args.kwargs["remote_url"], expected)

    def test_image_error_is_reported_without_details(self):
        self.client.analyze.side_effect = ValueError("private image details")
        self.assertEqual(
            self.run_cli("--url", "https://example.com"),
            (1, "", "Error: Screenshot processing failed.\n"),
        )

    def test_interrupt_returns_130(self):
        self.Capture.return_value.take.side_effect = KeyboardInterrupt()
        self.assertEqual(
            self.run_cli("--url", "https://example.com"),
            (130, "", "Error: Interrupted.\n"),
        )
        self.client.analyze.assert_not_called()

    def test_help_does_not_load_configuration_or_start_browser(self):
        stdout = StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as caught:
            main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("--selector", stdout.getvalue())
        self.load_config.assert_not_called()
        self.Capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
