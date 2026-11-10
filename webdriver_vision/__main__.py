"""Run screenshot capture and vision analysis from the command line."""

import argparse
import math
import sys
from collections.abc import Sequence
from urllib.parse import urlsplit

from urllib3.exceptions import HTTPError as WebDriverConnectionError

from selenium.common.exceptions import (
    InvalidSelectorException, TimeoutException, WebDriverException,
)

from webdriver_vision import AIClient, Capture
from webdriver_vision.client import (
    AIClientError, AIHTTPError, AIResponseError, AITimeoutError,
)
from webdriver_vision.config import ConfigurationError, load_config


def _page_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
        valid = (
            parsed.scheme in ("http", "https") and bool(parsed.hostname)
            and valid_port and not any(char.isspace() or ord(char) < 32 for char in value)
        )
    except ValueError:
        valid = False
    if not valid:
        raise argparse.ArgumentTypeError("must be an absolute HTTP or HTTPS URL.")
    return value


def _positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer.") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer.")
    return number


def _positive_timeout(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a finite positive number.") from None
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number.")
    return number


def _selector(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must be a non-empty CSS selector.")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webdriver-vision",
        description="Capture a web page and describe visible issues with a vision API.",
    )
    parser.add_argument("--url", required=True, type=_page_url, help="HTTP(S) page URL.")
    parser.add_argument("--config", default="config.yaml", help="YAML settings file.")
    parser.add_argument(
        "--remote-url", type=_page_url,
        help="Remote Chrome WebDriver URL; overrides browser.remote_url.",
    )
    parser.add_argument(
        "--selector", type=_selector, help="CSS selector of a visible element to capture."
    )
    parser.add_argument(
        "--full-page", action=argparse.BooleanOptionalAction, default=None,
        help="Capture the whole document; overrides screenshot.full_page.",
    )
    parser.add_argument(
        "--headless", action=argparse.BooleanOptionalAction, default=None,
        help="Run without a visible window; overrides browser.headless.",
    )
    parser.add_argument(
        "--window-size", nargs=2, type=_positive_integer, metavar=("WIDTH", "HEIGHT"),
        help="Browser window size; overrides browser.window_size.",
    )
    parser.add_argument(
        "--capture-timeout", type=_positive_timeout, default=30, metavar="SECONDS",
        help="Navigation and element wait timeout (default: 30).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Return a process exit code; write the report to stdout."""
    args = build_parser().parse_args(argv)
    try:
        report = _analyze(args)
    except ConfigurationError as error:
        return _fail(str(error), 2)
    except AITimeoutError:
        return _fail("Vision API request timed out. Check ai.timeout.", 1)
    except AIHTTPError as error:
        status = error.status_code
        if status in (401, 403):
            hint = "Check AI_API_KEY and model access."
        elif status == 429:
            hint = "Check the provider's rate limits or quota."
        elif 300 <= status < 400:
            hint = "Check ai.api_url; redirects are not followed."
        elif status >= 500:
            hint = "The provider is unavailable; try again later."
        else:
            hint = "Check the provider's endpoint and model settings."
        return _fail(f"Vision API returned HTTP {status}. {hint}", 1)
    except AIResponseError:
        return _fail("Vision API returned an invalid or incomplete text report.", 1)
    except AIClientError:
        return _fail("Vision API request failed. Check connectivity and ai.api_url.", 1)
    except InvalidSelectorException:
        return _fail("Invalid CSS selector. Check --selector.", 1)
    except TimeoutException:
        return _fail("Page load or element visibility timed out. Check --capture-timeout.", 1)
    except (WebDriverException, WebDriverConnectionError, OSError):
        return _fail(
            "Browser capture failed. Check Chrome, ChromeDriver, or --remote-url.", 1
        )
    except (ValueError, TypeError):
        return _fail("Screenshot processing failed.", 1)
    except KeyboardInterrupt:
        return _fail("Interrupted.", 130)
    print(report)
    return 0


def _analyze(args: argparse.Namespace) -> str:
    try:
        settings = load_config(args.config)
    except FileNotFoundError:
        raise ConfigurationError("Configuration file was not found. Check --config.") from None
    except UnicodeError:
        raise ConfigurationError("Configuration file must use UTF-8 encoding.") from None
    except OSError:
        raise ConfigurationError("Could not read configuration file. Check --config.") from None

    browser = settings.get("browser", {})
    screenshot = settings.get("screenshot", {})
    full_page = (
        args.full_page if args.full_page is not None
        else screenshot.get("full_page", False)
    )
    if args.selector is not None and full_page:
        raise ConfigurationError("--selector cannot be combined with full-page capture.")
    client = AIClient.from_settings(settings)
    capture = Capture(
        args.url,
        headless=(
            args.headless if args.headless is not None
            else browser.get("headless", True)
        ),
        window_size=(
            args.window_size if args.window_size is not None
            else browser.get("window_size", (1920, 1080))
        ),
        full_page=full_page,
        timeout=args.capture_timeout,
        remote_url=(
            args.remote_url if args.remote_url is not None
            else browser.get("remote_url")
        ),
    )
    return client.analyze(capture.take(selector=args.selector))


def _fail(message: str, code: int) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
