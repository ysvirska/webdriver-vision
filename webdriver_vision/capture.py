"""Capture PNG screenshots with Chrome through Selenium WebDriver."""

import base64
import math
from contextlib import suppress

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_vision.config import validate_config


class Capture:
    """Open a fresh local or remote Chrome session for each screenshot."""

    def __init__(
        self,
        url: str,
        *,
        headless: bool = True,
        window_size: tuple[int, int] | list[int] = (1920, 1080),
        full_page: bool = False,
        timeout: float = 30,
        remote_url: str | None = None,
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
        if remote_url is not None:
            validate_config({"browser": {"remote_url": remote_url}})
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
        self.remote_url = remote_url

    def take(self, *, selector: str | None = None) -> bytes:
        """Return PNG bytes for the page or a visible element matched by CSS."""
        if selector is not None:
            if not isinstance(selector, str) or not selector.strip():
                raise ValueError("selector must be a non-empty CSS selector.")
            if self.full_page:
                raise ValueError("selector cannot be combined with full_page.")
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        if self.remote_url is None:
            driver = webdriver.Chrome(options=options)
        else:
            driver = webdriver.Remote(command_executor=self.remote_url, options=options)
        try:
            driver.set_window_size(*self.window_size)
            driver.set_page_load_timeout(self.timeout)
            driver.get(self.url)
            if selector is None:
                screenshot = self._screenshot(driver)
            else:
                element = WebDriverWait(driver, self.timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                )
                screenshot = element.screenshot_as_png
        except BaseException:
            # Cleanup must not replace the original capture error or interrupt.
            with suppress(Exception):
                driver.quit()
            raise
        else:
            driver.quit()
            return screenshot

    def _screenshot(self, driver: webdriver.Remote) -> bytes:
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
