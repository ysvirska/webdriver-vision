# Command-line usage

Follow [installation and first run](installation.md) to install the package, copy
`config.example.yaml` to a local `config.yaml`, choose the endpoint and model,
and set `AI_API_KEY` in your environment.

```bash
python -m webdriver_vision --url https://example.com --config config.yaml
```

Installing the package also provides the `webdriver-vision` command:

```bash
webdriver-vision --url https://example.com --config config.yaml
```

The CLI loads the file once, validates API settings, captures the page, and sends
the screenshot for analysis. The text report is written to stdout. Settings in
the YAML file control browser options, image format and quality, and API requests.

## Capture options

```bash
webdriver-vision --url https://example.com --selector '#login-form'
webdriver-vision --url https://example.com --full-page
webdriver-vision --url https://example.com --no-headless --window-size 1280 900
webdriver-vision --url https://example.com --capture-timeout 60 > report.txt
```

`--config` defaults to `config.yaml`. `--selector` captures a visible element.
`--headless` / `--no-headless`, `--full-page` / `--no-full-page`, and `--window-size`
override the corresponding YAML settings. `--capture-timeout` defaults to 30
seconds and applies separately to navigation and element visibility. API request
timeouts remain controlled by `ai.timeout`.

Use `--remote-url http://grid:4444` to connect to a remote Chrome WebDriver rather
than launch Chrome locally. It overrides the optional `browser.remote_url` setting.
The target page must be reachable from that remote browser. Docker Compose supplies
this flag automatically; see [Docker usage](docker.md).

Flags override supplied YAML values, including explicit false values. For example,
use `--no-full-page --selector '#login-form'` when the file enables full-page
capture. Page capture returns PNG; `screenshot.format: jpeg` converts the image
before sending it to the API. Use `screenshot.quality` to set JPEG quality.

The CLI starts a fresh browser session, so it does not reuse an existing Chrome
login or cookies. It sends one image and prompt to the API, prints the returned
report, and exits. A report that describes a visual error still has exit code 0;
the text is not converted into an automated pass/fail judgment.

Use `--help` to list all options. Help does not require a configuration or browser.
Exit code 0 means a report was produced, even if it describes page errors.

## Validation and errors

The page URL must be an absolute HTTP or HTTPS URL. Window dimensions must be
positive integers, and the capture timeout must be finite and positive. Empty
selectors and a selector combined with full-page capture are rejected before
Chrome starts, including when full-page capture is enabled in YAML.

Errors go to stderr, leaving stdout empty. API errors include guidance for common
authentication, quota, timeout, and endpoint problems. Provider response bodies
and browser stack traces are not printed.

| Exit code | Meaning |
| --- | --- |
| `0` | A text report was produced. |
| `1` | Browser, image processing, or API failure. |
| `2` | Invalid arguments, unreadable configuration, or invalid settings. |
| `130` | Interrupted by the user. |

## Local credentials

Use the `AI_API_KEY` environment variable for real credentials. Local `config.yaml`,
`.env` files, and private key file formats are excluded from Git. `.env` files are
not loaded automatically. Examples and tests contain placeholders only.
