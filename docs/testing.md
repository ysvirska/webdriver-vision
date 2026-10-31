# Testing

Install the package in your development environment, then run:

```bash
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
```

Unit tests isolate individual modules. Integration tests exercise configuration,
CLI orchestration, image encoding, and real HTTP requests to a local fake vision
API. By default, Chrome is mocked. No real API key or paid service is needed.

## Real browser checks

With Chrome installed, opt in to the browser integration tests:

```bash
WEBDRIVER_VISION_BROWSER_TESTS=1 python -m unittest discover -s tests/integration -v
```

These tests serve a local page, capture a delayed element and a full document with
real Chrome, and send the images to the local fake API. Selenium Manager may need
network access to download ChromeDriver. All API requests remain on localhost and
use a fixed dummy credential. The model's ability to detect visual errors is not
tested by this suite.

## Continuous integration

[GitHub Actions](../.github/workflows/tests.yml) runs unit and local HTTP integration
tests on Python 3.10, 3.12, and 3.14. A separate Ubuntu job runs the browser tests
with Chrome against the installed package. The workflow runs on pushes to `main`
and pull requests. It does not need provider secrets or contact a paid vision API.
