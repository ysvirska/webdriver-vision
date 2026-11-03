# webdriver-vision
 
Python module that captures a Chrome screenshot via WebDriver, encodes it to base64, and sends it to an AI vision API. The AI analyzes the screenshot and returns a text report of any errors found on the page.
 
## Features
 
- Chrome screenshots via Selenium WebDriver (full page or element)
- Base64 encoding (PNG/JPEG, configurable quality)
- Pluggable AI client (any vision API over HTTP)
- AI error analysis: detects UI/page errors and describes them in plain text
- Configurable via YAML or environment variables
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
