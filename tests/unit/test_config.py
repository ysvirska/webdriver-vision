"""Tests for reading configuration files."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webdriver_vision.config import ConfigurationError, load_config, validate_config


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

    def test_validate_loaded_settings(self):
        self.write_config('browser: {headless: "yes"}\n')
        with self.assertRaisesRegex(ConfigurationError, "browser.headless"):
            load_config(self.path)

    def test_environment_override_is_applied_before_validation(self):
        self.write_config("ai: {api_key: null}\n")
        os.environ["AI_API_KEY"] = "environment-key"
        self.assertEqual(load_config(self.path)["ai"]["api_key"], "environment-key")


class ValidateConfigTests(unittest.TestCase):
    def test_accept_partial_configuration_without_mutation(self):
        for settings in (
            {},
            {"ai": {"timeout": 0.5}},
            {"custom": {"enabled": True}},
        ):
            with self.subTest(settings=settings):
                original = repr(settings)
                validate_config(settings)
                self.assertEqual(repr(settings), original)

    def test_accept_all_supported_fields(self):
        validate_config(
            {
                "browser": {"headless": False, "window_size": [1920, 1080]},
                "screenshot": {"format": "jpeg", "quality": 85, "full_page": True},
                "ai": {
                    "api_url": "https://api.example.com:443/v1/messages",
                    "api_key": "test-key",
                    "model": "test-model",
                    "timeout": 30,
                    "prompt": "Check the screenshot.",
                },
            }
        )

    def test_reject_invalid_root_and_section_types(self):
        for settings in (None, [], "text"):
            with self.subTest(settings=settings):
                with self.assertRaises(ConfigurationError):
                    validate_config(settings)
        for section in ("browser", "screenshot", "ai"):
            for value in (None, [], True, "text"):
                with self.subTest(section=section, value=value):
                    with self.assertRaisesRegex(ConfigurationError, section):
                        validate_config({section: value})

    def test_reject_boolean_lookalikes(self):
        for section, field in (
            ("browser", "headless"), ("screenshot", "full_page")
        ):
            for value in ("false", 0, 1, None):
                with self.subTest(section=section, value=value):
                    with self.assertRaisesRegex(ConfigurationError, field):
                        validate_config({section: {field: value}})

    def test_validate_window_dimensions(self):
        validate_config({"browser": {"window_size": [1, 1]}})
        for size in (
            [0, 10], [-1, 10], [True, 10], [1.5, 10],
            [10], [1, 2, 3], "10,10", None,
        ):
            with self.subTest(size=size):
                with self.assertRaisesRegex(ConfigurationError, "window_size"):
                    validate_config({"browser": {"window_size": size}})

    def test_validate_image_format(self):
        for format in ("png", "jpeg"):
            validate_config({"screenshot": {"format": format}})
        for format in ("gif", "jpg", "PNG", "", None, []):
            with self.subTest(format=format):
                with self.assertRaisesRegex(ConfigurationError, "screenshot.format"):
                    validate_config({"screenshot": {"format": format}})

    def test_validate_jpeg_quality_bounds(self):
        for quality in (1, 95):
            validate_config({"screenshot": {"quality": quality}})
        for quality in (0, 96, True, 85.0, "85", None):
            with self.subTest(quality=quality):
                with self.assertRaisesRegex(ConfigurationError, "screenshot.quality"):
                    validate_config({"screenshot": {"quality": quality}})

    def test_validate_ai_strings_without_exposing_values(self):
        for field in ("api_key", "model", "prompt"):
            for value in (None, "", "  ", 123, {"private": "value"}):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ConfigurationError) as caught:
                        validate_config({"ai": {field: value}})
                    self.assertEqual(
                        str(caught.exception),
                        f"ai.{field} must be a non-empty string.",
                    )

    def test_validate_api_url(self):
        for url in (
            "http://localhost:8000/analyze",
            "https://api.example.com/v1",
            "http://[::1]:8000",
        ):
            validate_config({"ai": {"api_url": url}})
        for url in (
            "/v1", "https://", "ftp://example.com", "https://bad host",
            "https://[", "https://example.com:wrong", "http://localhost:0",
            "http://localhost:65536", None,
        ):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ConfigurationError, "ai.api_url"):
                    validate_config({"ai": {"api_url": url}})

    def test_validate_timeout(self):
        for timeout in (0.1, 1, 30.5):
            validate_config({"ai": {"timeout": timeout}})
        for timeout in (
            0, -1, True, "30", None, float("nan"), float("inf"), -float("inf"),
        ):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(ConfigurationError, "ai.timeout"):
                    validate_config({"ai": {"timeout": timeout}})


if __name__ == "__main__":
    unittest.main()
