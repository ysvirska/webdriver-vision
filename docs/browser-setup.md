# Chrome setup and troubleshooting

## Browser and driver

Install [Google Chrome](https://www.google.com/chrome/) in the normal location for
your operating system. `Capture` uses Chrome only and starts it headless by default.
Use `--no-headless` only in an environment with a graphical desktop.

Selenium Manager finds a compatible ChromeDriver and may download it on the first
run. Allow the download and ensure that the account running the tool can write to
the driver's cache. See the official
[Selenium Manager documentation](https://www.selenium.dev/documentation/selenium_manager/)
for proxy, cache, and offline configuration.

If you manage ChromeDriver yourself, put a compatible executable on `PATH`.
An outdated driver there can interfere with startup. Check the browser and driver
versions, update the managed driver, or let Selenium Manager resolve it. The
[ChromeDriver setup guide](https://developer.chrome.com/docs/chromedriver/get-started)
describes installation locations and driver discovery.

## Check capture without a vision provider

The browser integration tests use a local page and a fake HTTP API:

```bash
WEBDRIVER_VISION_BROWSER_TESTS=1 python -m unittest discover -s tests/integration -v
```

In PowerShell:

```powershell
$env:WEBDRIVER_VISION_BROWSER_TESTS = "1"
python -m unittest discover -s tests/integration -v
```

These checks require Chrome and a usable driver but no provider account. If they
pass while a real analysis fails, check the target page, endpoint, model, and API
access separately.

## Common problems

| Symptom | What to check |
| --- | --- |
| Browser capture fails at startup | Chrome installation, compatible ChromeDriver, driver download access, and cache permissions. |
| A visible window cannot open | Keep the default headless mode on servers without a graphical session. |
| Page load or element visibility times out | Confirm the page is reachable and increase `--capture-timeout` if needed. For elements, use a selector whose first match becomes visible. |
| Element capture reports invalid CSS | Check `--selector`; it accepts CSS, not XPath. |
| Captured area is smaller than `--window-size` | Window dimensions include browser chrome; the viewport can be smaller. Use `--full-page` for document content. |
| Expected content is missing | Navigation completion and element visibility do not guarantee application, font, or image readiness. Full-page capture does not trigger lazy loading by scrolling. |
| HTTP 401 or 403 | Check `AI_API_KEY`, the account's model access, and the selected endpoint. |
| HTTP 400 or an invalid text report | Confirm that the endpoint supports the Chat Completions image schema and the model accepts images. |
| API timeout | Check connectivity and `ai.timeout`, which controls connection and read inactivity rather than a total deadline. |

The Python API propagates Selenium exceptions for local debugging; the CLI reports
concise errors and exit codes. See [CLI usage](cli.md) and
[known limitations](limitations.md) for the supported behavior.
