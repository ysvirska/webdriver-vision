# Command-line usage

Create a local YAML configuration as described in [configuration](configuration.md)
and [the API client](client.md), then set `AI_API_KEY` in your environment.

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
```

`--config` defaults to `config.yaml`. `--selector` captures a visible element.
`--headless` / `--no-headless`, `--full-page` / `--no-full-page`, and `--window-size`
override the corresponding YAML settings. `--capture-timeout` defaults to 30
seconds and applies separately to navigation and element visibility. API request
timeouts remain controlled by `ai.timeout`.

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
