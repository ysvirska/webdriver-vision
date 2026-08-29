"""Tests for reading configuration files."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webdriver_vision.config import ConfigurationError, load_config


class LoadConfigTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {})
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop("AI_API_KEY", None)
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

    def test_environment_api_key_overrides_yaml_value(self):
        self.write_config("ai: {api_key: file-key, model: test-model}\n")
        os.environ["AI_API_KEY"] = "environment-key"
        self.assertEqual(
            load_config(self.path)["ai"],
            {"api_key": "environment-key", "model": "test-model"},
        )

    def test_preserve_yaml_api_key_without_environment_override(self):
        self.write_config("ai: {api_key: file-key}\n")
        self.assertEqual(load_config(self.path)["ai"]["api_key"], "file-key")

    def test_resolve_api_key_placeholder(self):
        self.write_config('ai:\n  api_key: "${AI_API_KEY}"\n')
        os.environ["AI_API_KEY"] = "environment-key"
        self.assertEqual(load_config(self.path)["ai"]["api_key"], "environment-key")

    def test_missing_placeholder_variable_raises_configuration_error(self):
        self.write_config('ai:\n  api_key: "${AI_API_KEY}"\n')
        with self.assertRaisesRegex(ConfigurationError, "AI_API_KEY is not set"):
            load_config(self.path)

    def test_environment_api_key_works_with_empty_file(self):
        self.write_config("")
        os.environ["AI_API_KEY"] = "environment-key"
        self.assertEqual(load_config(self.path), {"ai": {"api_key": "environment-key"}})

    def test_reject_empty_environment_api_key(self):
        self.write_config("{}")
        for value in ("", "   "):
            with self.subTest(value=value):
                os.environ["AI_API_KEY"] = value
                with self.assertRaisesRegex(ConfigurationError, "must not be empty"):
                    load_config(self.path)

    def test_reject_non_mapping_ai_section(self):
        for content in ("ai: null", "ai: []", "ai: text"):
            for api_key in (None, "environment-key"):
                with self.subTest(content=content, api_key=api_key):
                    os.environ.pop("AI_API_KEY", None)
                    if api_key is not None:
                        os.environ["AI_API_KEY"] = api_key
                    self.write_config(content)
                    with self.assertRaisesRegex(ConfigurationError, "ai section"):
                        load_config(self.path)

    def test_read_environment_on_each_load(self):
        self.write_config("{}")
        os.environ["AI_API_KEY"] = "first-key"
        first = load_config(self.path)
        os.environ["AI_API_KEY"] = "second-key"
        self.assertEqual(load_config(self.path)["ai"]["api_key"], "second-key")
        self.assertEqual(first["ai"]["api_key"], "first-key")

    def test_leave_unrelated_placeholders_unchanged(self):
        self.write_config('ai: {prompt: "${PROMPT}"}\n')
        os.environ["PROMPT"] = "Check this screenshot."
        self.assertEqual(load_config(self.path)["ai"]["prompt"], "${PROMPT}")

    def test_api_key_override_does_not_modify_aliased_sections(self):
        self.write_config("other: &options\n  model: test-model\nai: *options\n")
        os.environ["AI_API_KEY"] = "environment-key"
        settings = load_config(self.path)
        self.assertEqual(settings["other"], {"model": "test-model"})
        self.assertEqual(settings["ai"]["api_key"], "environment-key")


if __name__ == "__main__":
    unittest.main()
