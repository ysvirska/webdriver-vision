# Screenshot capture

Install the package and Google Chrome. Selenium Manager locates a compatible
driver and may download it on the first run, which requires network access.

```python
from pathlib import Path

from webdriver_vision import Capture
from webdriver_vision.encode import encode_image

screenshot = Capture("https://example.com").take()
Path("screenshot.png").write_bytes(screenshot)
encoded = encode_image(screenshot)
```

Each call to `take()` creates a fresh Chrome session, navigates to the URL, returns
PNG bytes, and closes the session. Selenium exceptions propagate to the caller.
The screenshot is taken after normal page navigation completes. This does not
guarantee that asynchronous application content or animations have settled.

The browser is closed after capture and when setup, navigation, or screenshot
operations fail. If cleanup also fails, the original capture error is preserved.
A cleanup failure after a successful capture is reported to the caller.

| Argument | Default | Meaning |
| --- | --- | --- |
| `url` | Required | A non-empty URL accepted by Chrome. |
| `headless` | `True` | Run Chrome without a visible window. |
| `window_size` | `(1920, 1080)` | Browser window width and height in CSS pixels; a tuple or list of positive integers. |
| `full_page` | `False` | Capture the document beyond the viewport using Chrome DevTools Protocol. |
| `timeout` | `30` | Finite positive timeout in seconds, applied separately to navigation and element visibility waits. |

By default, only the current viewport is captured. The viewport can be smaller
than the outer browser window. For the whole document:

```python
screenshot = Capture("https://example.com", full_page=True).take()
```

Full-page capture uses the current document size. It does not scroll through the
page to trigger lazy loading. Very large documents may exceed Chrome's screenshot
limits. Capture always returns PNG; use `encode_image` to convert it to JPEG.

## Capture an element

Pass a CSS selector to `take`:

```python
screenshot = Capture("https://example.com").take(selector="#login-form")
```

The first matching element must become visible within `timeout` seconds after
navigation. Selenium scrolls it into view when taking the element screenshot.
The result contains PNG bytes for that element. A missing or hidden element causes
Selenium's `TimeoutException`; invalid CSS selectors also propagate Selenium
errors. The browser is closed in each case.

An empty selector is rejected before Chrome starts. Element capture and
`full_page=True` cannot be combined. Visibility does not guarantee that images,
fonts, or animations inside the element have finished loading.

## Tests

The capture unit tests use mocked WebDriver sessions and run without Chrome or
ChromeDriver. They cover browser options, full-page protocol requests, element
visibility waits, input validation, and cleanup after failures.

```bash
python -m unittest discover -s tests/unit -p test_capture.py -v
```
