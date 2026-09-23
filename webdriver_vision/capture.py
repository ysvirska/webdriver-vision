"""Capture PNG screenshots with Chrome through Selenium WebDriver."""

import base64
import math
from contextlib import suppress

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from webdriver_vision.config import validate_config


class Capture:
    """Open a fresh Chrome session for each screenshot."""

    def __init__(
        self,
        url: str,
        *,
        headless: bool = True,
        window_size: tuple[int, int] | list[int] = (1920, 1080),
        full_page: bool = False,
        timeout: float = 30,
    ):
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string.")
        if not isinstance(window_size, (tuple, list)):
            raise ValueError("window_size must contain two positive integers.")
        validate_config(
            {
                "browser": {"headless": headless, "window_size": list(window_size)},
                "screenshot": {"full_page": full_page},
            }
        )
        if (
            type(timeout) not in (int, float)
            or timeout <= 0
            or (isinstance(timeout, float) and not math.isfinite(timeout))
        ):
            raise ValueError("timeout must be a finite positive number.")

        self.url = url
        self.headless = headless
        self.window_size = tuple(window_size)
        self.full_page = full_page
        self.timeout = timeout

    def take(self) -> bytes:
        """Return a PNG screenshot after navigation completes."""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=options)
        try:
            driver.set_window_size(*self.window_size)
            driver.set_page_load_timeout(self.timeout)
            driver.get(self.url)
            screenshot = self._screenshot(driver)
        except BaseException:
            # Cleanup must not replace the original capture error or interrupt.
            with suppress(Exception):
                driver.quit()
            raise
        else:
            driver.quit()
            return screenshot

    def _screenshot(self, driver: webdriver.Chrome) -> bytes:
        if not self.full_page:
            return driver.get_screenshot_as_png()
        metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
        result = driver.execute_cdp_cmd(
            "Page.captureScreenshot",
            {
                "format": "png",
                "fromSurface": True,
                "captureBeyondViewport": True,
                "clip": {**metrics["cssContentSize"], "scale": 1},
            },
        )
        return base64.b64decode(result["data"], validate=True)
