"""Tests for reading configuration files."""

import tempfile
import unittest
from pathlib import Path

from webdriver_vision.config import ConfigurationError, load_config


class LoadConfigTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "config.yaml"

    def write_config(self, content):
        self.path.write_text(content, encoding="utf-8")
        return self.path

    def test_load_nested_settings(self):
        self.write_config(
            "browser:\n  headless: true\n  window_size: [1920, 1080]\n"
            "ai:\n  timeout: 30\n"
        )
        self.assertEqual(
            load_config(self.path),
            {
                "browser": {"headless": True, "window_size": [1920, 1080]},
                "ai": {"timeout": 30},
            },
        )

    def test_accept_string_path(self):
        self.write_config("ai: {model: test-model}\n")
        self.assertEqual(load_config(str(self.path))["ai"]["model"], "test-model")

    def test_load_utf8_text(self):
        self.write_config("ai:\n  prompt: Check the café page.\n")
        self.assertEqual(load_config(self.path)["ai"]["prompt"], "Check the café page.")

    def test_empty_file_returns_empty_mapping(self):
        self.write_config("# Settings will be added later.\n")
        self.assertEqual(load_config(self.path), {})

    def test_reject_non_mapping_documents(self):
        for content in ("[]", "[browser]", "false", "0", '""', "plain text"):
            with self.subTest(content=content):
                self.write_config(content)
                with self.assertRaisesRegex(ConfigurationError, "YAML mapping"):
                    load_config(self.path)

    def test_reject_invalid_yaml(self):
        self.write_config("browser: [\n")
        with self.assertRaisesRegex(ConfigurationError, "Invalid YAML"):
            load_config(self.path)

    def test_reject_python_object_tags(self):
        self.write_config("!!python/object:builtins.object {}\n")
        with self.assertRaises(ConfigurationError):
            load_config(self.path)

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_config(self.path)


if __name__ == "__main__":
    unittest.main()
