"""Run screenshot capture and vision analysis from the command line."""

import argparse
import sys
from collections.abc import Sequence

from selenium.common.exceptions import WebDriverException

from webdriver_vision import AIClient, Capture
from webdriver_vision.client import AIClientError
from webdriver_vision.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webdriver-vision",
        description="Capture a web page and describe visible issues with a vision API.",
    )
    parser.add_argument("--url", required=True, help="Page URL to capture.")
    parser.add_argument("--config", default="config.yaml", help="YAML settings file.")
    parser.add_argument("--selector", help="CSS selector of a visible element to capture.")
    parser.add_argument(
        "--full-page", action=argparse.BooleanOptionalAction, default=None,
        help="Capture the whole document; overrides screenshot.full_page.",
    )
    parser.add_argument(
        "--headless", action=argparse.BooleanOptionalAction, default=None,
        help="Run without a visible window; overrides browser.headless.",
    )
    parser.add_argument(
        "--window-size", nargs=2, type=int, metavar=("WIDTH", "HEIGHT"),
        help="Browser window size; overrides browser.window_size.",
    )
    parser.add_argument(
        "--capture-timeout", type=float, default=30, metavar="SECONDS",
        help="Navigation and element wait timeout (default: 30).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Return a process exit code; write the report to stdout."""
    args = build_parser().parse_args(argv)
    try:
        settings = load_config(args.config)
        client = AIClient.from_settings(settings)
        browser = settings.get("browser", {})
        screenshot = settings.get("screenshot", {})
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
            full_page=(
                args.full_page if args.full_page is not None
                else screenshot.get("full_page", False)
            ),
            timeout=args.capture_timeout,
        )
        report = client.analyze(capture.take(selector=args.selector))
    except (OSError, ValueError, TypeError, AIClientError, WebDriverException):
        print("Error: Analysis failed.", file=sys.stderr)
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
