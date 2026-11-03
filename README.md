# webdriver-vision
 
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-lightgrey)
 
Python module that captures a Chrome screenshot via WebDriver, encodes it to base64, and sends it to an AI vision API. The AI analyzes the screenshot and returns a text report of any errors found on the page.
 
## Demo
 
<!-- Replace with a real GIF/screenshot of a run -->
![Demo](docs/demo.gif)
 
## Use cases
 
- UI test automation: detect visible errors that DOM checks miss
- Page monitoring: get a text alert when a page shows an error state
- Visual regression: describe what changed on screen
## Features
 
- Chrome screenshots via Selenium WebDriver (full page or element)
- Base64 encoding (PNG/JPEG, configurable quality)
- Pluggable AI client (any vision API over HTTP)
- AI error analysis: detects UI/page errors and describes them in plain text
- Configurable via YAML or environment variables
## How it works
 
```
 config.yaml  (controls every step)
      |
      v
+-----------+   screenshot   +---------+  image + prompt  +--------+  analysis  +-------------+
|  Chrome   | -------------> | Base64  | ---------------> | AI API | ---------> | Text report |
| WebDriver |                | encoder |                  | vision |            | of errors   |
+-----------+                +---------+                  +--------+            +-------------+
```
 
## Install
 
```bash
pip install -r requirements.txt
```
 
## Quick start
 
```python
from webdriver_vision import Capture, AIClient
 
shot = Capture(url="https://example.com").take()
result = AIClient.from_config("config.yaml").analyze(shot)
print(result)
# -> "Error found: login form shows 'Invalid password' message under the password field."
```
 
## CLI
 
```bash
python -m webdriver_vision --url https://example.com --config config.yaml
```
 
## Configuration
 
```yaml
browser:
  headless: true
  window_size: [1920, 1080]
screenshot:
  format: png        # png | jpeg
  full_page: false
ai:
  api_url: https://api.example.com/v1/messages
  api_key: ${AI_API_KEY}
  model: your-model
  timeout: 30
  prompt: "Check this screenshot for errors and describe them briefly in text."
```
 
Set the API key via environment variable (never commit it):
 
```bash
export AI_API_KEY=your-key
```
 
## Troubleshooting
 
- **chromedriver version mismatch**: use Selenium 4.6+ (auto-manages drivers) or match the driver to your Chrome version
- **Blank screenshot in headless mode**: set `window_size` explicitly and wait for page load
- **API timeout**: increase `ai.timeout`
## Limitations
 
AI analysis can miss or misreport errors. Treat output as a hint, not a source of truth.
 
## Roadmap
 
- [ ] Firefox support
- [ ] Batch mode (multiple URLs)
- [ ] Screenshot comparison
## Project structure
 
```
webdriver_vision/
  capture.py   # Chrome screenshot
  encode.py    # base64 encoding
  client.py    # AI API client
tests/
config.yaml
```
 
## Tests
 
```bash
pytest
```
 
## License
 
MIT
