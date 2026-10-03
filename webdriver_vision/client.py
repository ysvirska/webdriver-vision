"""Send screenshots to an OpenAI-compatible Chat Completions endpoint."""

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
from requests.auth import AuthBase

from webdriver_vision.config import ConfigurationError, load_config, validate_config
from webdriver_vision.encode import encode_image


DEFAULT_PROMPT = (
    "Check this screenshot for visible page errors and describe them briefly. "
    "If no issues are visible, say so."
)


class AIClientError(RuntimeError):
    """Raised when a vision API request cannot produce a report."""


class AIResponseError(AIClientError):
    """Raised when the API response does not contain a complete text report."""


class _BearerAuth(AuthBase):
    def __init__(self, api_key: str):
        self._api_key = api_key

    def __call__(self, request):
        request.headers["Authorization"] = f"Bearer {self._api_key}"
        return request


class AIClient:
    """Analyze image bytes using a configurable vision-capable model."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str,
        *,
        timeout: float = 30,
        prompt: str = DEFAULT_PROMPT,
        image_format: str = "png",
        quality: int = 85,
    ):
        validate_config(
            {
                "ai": {
                    "api_url": api_url, "api_key": api_key, "model": model,
                    "timeout": timeout, "prompt": prompt,
                },
                "screenshot": {"format": image_format, "quality": quality},
            }
        )
        if not api_key.isascii() or any(char.isspace() for char in api_key):
            raise ConfigurationError(
                "ai.api_key must be an ASCII token without whitespace."
            )
        if urlsplit(api_url).username is not None:
            raise ConfigurationError("ai.api_url must not contain credentials.")
        self.api_url = api_url
        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self.prompt = prompt
        self.image_format = image_format
        self.quality = quality

    @classmethod
    def from_config(cls, path: str | Path) -> "AIClient":
        """Load YAML settings and environment credentials, then create a client."""
        return cls.from_settings(load_config(path))

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> "AIClient":
        """Create a client from loaded settings without reading the file again."""
        validate_config(settings)
        ai = settings.get("ai", {})
        for field in ("api_url", "api_key", "model"):
            if field not in ai:
                raise ConfigurationError(f"ai.{field} is required.")
        screenshot = settings.get("screenshot", {})
        return cls(
            api_url=ai["api_url"], api_key=ai["api_key"], model=ai["model"],
            timeout=ai.get("timeout", 30), prompt=ai.get("prompt", DEFAULT_PROMPT),
            image_format=screenshot.get("format", "png"),
            quality=screenshot.get("quality", 85),
        )

    def analyze(self, image: bytes) -> str:
        """Encode screenshot bytes, submit one request, and return a text report."""
        encoded = encode_image(
            image, image_format=self.image_format, quality=self.quality
        )
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{self.image_format};base64,{encoded}"
                        },
                    },
                ],
            }],
        }
        with requests.post(
            self.api_url, json=payload, auth=_BearerAuth(self._api_key),
            timeout=self.timeout, allow_redirects=False,
        ) as response:
            if not 200 <= response.status_code < 300:
                raise AIClientError(f"Vision API returned HTTP {response.status_code}.")
            try:
                document = response.json()
            except ValueError:
                raise AIResponseError("Vision API returned invalid JSON.") from None
        return _extract_report(document)


def _extract_report(document: Any) -> str:
    try:
        choice = document["choices"][0]
        report = choice["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise AIResponseError("Vision API did not return a text report.") from None
    if not isinstance(report, str) or not report.strip():
        raise AIResponseError("Vision API did not return a text report.")
    if choice.get("finish_reason") not in (None, "stop"):
        raise AIResponseError("Vision API returned an incomplete report.")
    return report.strip()
