# webdriver-vision

A Python tool for checking web pages with Selenium screenshots and an AI vision API.
The goal is to turn a screenshot into a text report describing visible page errors,
such as broken layouts, overlapping elements, or error messages.

## Project status

The repository currently contains the project overview and directory structure.
The Python modules, command-line interface, and tests are planned and have not been
implemented yet.

## How it will work

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

## Planned modules

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
```

## Development plan

- [ ] Set up Python packaging and dependencies.
- [ ] Add configuration loading and validation.
- [ ] Implement image encoding and screenshot capture.
- [ ] Add the vision API client.
- [ ] Connect the modules through a command-line interface.
- [ ] Add tests, CI, and usage documentation.

## Limitations

AI analysis can miss issues or report problems that are not present. Treat its
output as a review aid and confirm findings with browser tests or manual checks.
