# webdriver-vision

A Python tool for checking web pages with Selenium screenshots and an AI vision API.
The goal is to turn a screenshot into a text report describing visible page errors,
such as broken layouts, overlapping elements, or error messages.

The tool captures a viewport, full document, or selected element in Chrome,
encodes the image as PNG or JPEG, and submits it to an OpenAI-compatible Chat
Completions endpoint. It includes a Python API, CLI, YAML configuration, and tests.

## Quick start

Use Python 3.10 or newer and install Google Chrome. From a checkout, in Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
cp config.example.yaml config.yaml
```

In your local `config.yaml`, replace the placeholder endpoint and model with your
provider's image-capable Chat Completions endpoint and model identifier. Keep the
key as `${AI_API_KEY}`, then enter it for the current shell and run:

```bash
read -r -s -p "AI API key: " AI_API_KEY
printf '\n'
export AI_API_KEY
python -m webdriver_vision --url https://example.com --config config.yaml
```

The example contains no real credentials. Local `config.yaml` and `.env` files are
ignored by Git. See [installation](docs/installation.md) for Windows instructions
and [CLI usage](docs/cli.md) for all flags and exit codes.

## Python API

```python
from webdriver_vision import AIClient, Capture

client = AIClient.from_config("config.yaml")
screenshot = Capture("https://example.com").take()
print(client.analyze(screenshot))
```

## How it works

1. Open a page in Chrome through Selenium WebDriver.
2. Capture a screenshot of the page or a selected element.
3. Encode the image as base64.
4. Send the image and an analysis prompt to a vision API.
5. Print a text report of the visible issues found in the screenshot.

```text
Selenium -> Screenshot -> Base64 -> Vision API -> Text report
```

## Use cases

- Check for visible UI problems that DOM assertions may miss.
- Look for error messages during automated browser tests.
- Review screenshots when investigating page rendering problems.

## Module layout

| Module | Responsibility |
| --- | --- |
| `webdriver_vision/capture.py` | Manage browser sessions and capture screenshots. |
| `webdriver_vision/encode.py` | Prepare images for transmission as base64. |
| `webdriver_vision/client.py` | Send analysis requests and handle API responses. |
| `webdriver_vision/config.py` | Load and validate YAML and environment settings. |
| `webdriver_vision/__main__.py` | Run the workflow from the command line. |

## Repository layout

```text
webdriver_vision/    Python implementation
tests/
  unit/             Tests for individual modules
  integration/      Tests for interactions between modules
docs/               Usage guides and examples
config.example.yaml Settings template without credentials
```

## Development and testing

Use an editable install while working on the source:

```bash
python -m pip install -e .
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
```

The default tests use generated images, mocked browser sessions, and a local fake
API. They require no real API credential. See [testing](docs/testing.md) for real
Chrome checks and the CI workflow.

## Documentation

- [Installation and first run](docs/installation.md)
- [Command-line usage](docs/cli.md)
- [Configuration](docs/configuration.md)
- [Screenshot capture](docs/capture.md)
- [Image encoding](docs/encoding.md)
- [Vision API client](docs/client.md)
- [Testing and CI](docs/testing.md)
- [Chrome setup and troubleshooting](docs/browser-setup.md)
- [Known limitations](docs/limitations.md)

## Limitations

AI analysis can miss issues or report problems that are not present. Treat its
output as a review aid and confirm findings with browser tests or manual checks.
The client supports the Chat Completions image schema, and each capture uses a
fresh Chrome session. See [known limitations](docs/limitations.md) for readiness,
authentication, image size, and API compatibility details.
