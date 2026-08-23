"""Load application settings from YAML files."""

from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(ValueError):
    """Raised when a configuration file cannot be interpreted."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Read a UTF-8 YAML mapping; return an empty mapping for an empty file.

    File access errors are propagated as OSError subclasses. Invalid YAML and
    documents whose root is not a mapping raise ConfigurationError.
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
        return {}
    if not isinstance(settings, dict):
        raise ConfigurationError("Configuration must be a YAML mapping.")
    return settings
