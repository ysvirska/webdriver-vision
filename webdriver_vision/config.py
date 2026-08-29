"""Load application settings from YAML files and environment variables."""

import os
from pathlib import Path
from typing import Any

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

    return settings
