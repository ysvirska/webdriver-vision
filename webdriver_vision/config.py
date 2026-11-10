"""Load application settings from YAML files and environment variables."""

import math
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml


class ConfigurationError(ValueError):
    """Raised when a configuration file cannot be interpreted."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Read a UTF-8 YAML mapping and apply the AI_API_KEY environment override.

    File access errors are propagated as OSError subclasses. Invalid YAML and
    unsupported configuration structures raise ConfigurationError.
    """
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as stream:
        try:
            settings = yaml.safe_load(stream)
        except yaml.YAMLError:
            raise ConfigurationError(
                f"Invalid YAML in configuration file: {config_path}"
            ) from None

    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ConfigurationError("Configuration must be a YAML mapping.")

    ai_settings = settings.get("ai", {})
    if not isinstance(ai_settings, dict):
        raise ConfigurationError("The ai section must be a YAML mapping.")

    api_key = os.environ.get("AI_API_KEY")
    if api_key is not None:
        if not api_key.strip():
            raise ConfigurationError("AI_API_KEY must not be empty.")
        settings["ai"] = {**ai_settings, "api_key": api_key}
    elif ai_settings.get("api_key") == "${AI_API_KEY}":
        raise ConfigurationError("AI_API_KEY is not set.")

    validate_config(settings)
    return settings


def validate_config(settings: dict[str, Any]) -> None:
    """Validate supplied fields without inserting defaults or requiring sections."""
    if not isinstance(settings, dict):
        raise ConfigurationError("Configuration must be a YAML mapping.")
    for section in ("browser", "screenshot", "ai"):
        if section in settings and not isinstance(settings[section], dict):
            raise ConfigurationError(f"The {section} section must be a YAML mapping.")

    browser = settings.get("browser", {})
    screenshot = settings.get("screenshot", {})
    ai = settings.get("ai", {})

    if "remote_url" in browser and not _is_http_url(browser["remote_url"]):
        raise ConfigurationError("browser.remote_url must be an absolute HTTP or HTTPS URL.")

    for section_name, section, field in (
        ("browser", browser, "headless"),
        ("screenshot", screenshot, "full_page"),
    ):
        if field in section and type(section[field]) is not bool:
            raise ConfigurationError(f"{section_name}.{field} must be a boolean.")

    if "window_size" in browser:
        size = browser["window_size"]
        if (
            not isinstance(size, list)
            or len(size) != 2
            or any(type(value) is not int or value <= 0 for value in size)
        ):
            raise ConfigurationError(
                "browser.window_size must contain two positive integers."
            )

    if "format" in screenshot and screenshot["format"] not in ("png", "jpeg"):
        raise ConfigurationError("screenshot.format must be png or jpeg.")
    if "quality" in screenshot:
        quality = screenshot["quality"]
        if type(quality) is not int or not 1 <= quality <= 95:
            raise ConfigurationError(
                "screenshot.quality must be an integer from 1 to 95."
            )

    for field in ("api_key", "model", "prompt"):
        if field in ai and (not isinstance(ai[field], str) or not ai[field].strip()):
            raise ConfigurationError(f"ai.{field} must be a non-empty string.")

    if "api_url" in ai and not _is_http_url(ai["api_url"]):
        raise ConfigurationError("ai.api_url must be an absolute HTTP or HTTPS URL.")
    if "timeout" in ai:
        timeout = ai["timeout"]
        if (
            type(timeout) not in (int, float)
            or timeout <= 0
            or (isinstance(timeout, float) and not math.isfinite(timeout))
        ):
            raise ConfigurationError("ai.timeout must be a finite positive number.")


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str) or any(char.isspace() for char in value):
        return False
    try:
        parsed = urlsplit(value)
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.hostname)
            and valid_port
        )
    except ValueError:
        return False
