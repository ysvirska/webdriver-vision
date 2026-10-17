"""Tests for command-line orchestration without Chrome or API requests."""

import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from webdriver_vision.__main__ import main
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
            code = main(list(arguments))
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
            full_page=False, timeout=30,
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
            full_page=True, timeout=30,
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
            full_page=False, timeout=5,
        )
        self.Capture.return_value.take.assert_called_once_with(selector="#alert")

    def test_invalid_api_settings_prevent_browser_start(self):
        self.AIClient.from_settings.side_effect = ConfigurationError("ai.model is required.")
        code, stdout, stderr = self.run_cli("--url", "https://example.com")
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Error:", stderr)
        self.Capture.assert_not_called()

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
