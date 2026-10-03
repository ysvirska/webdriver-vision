# Vision API client

`AIClient` sends screenshots to an OpenAI-compatible Chat Completions endpoint.
The endpoint must support image inputs and return a text completion. Responses API
and Anthropic Messages endpoints use different schemas and are not supported.

```python
from webdriver_vision import AIClient, Capture

screenshot = Capture("https://example.com").take()
client = AIClient.from_config("config.yaml")
report = client.analyze(screenshot)
print(report)
```

The `ai` section requires `api_url`, `api_key`, and `model`. Use the full endpoint
URL, usually ending in `/v1/chat/completions`; no suffix is added automatically.
Choose a vision-capable model supported by your provider. Keep credentials in
`AI_API_KEY`, referenced as `${AI_API_KEY}` in YAML.

Optional `ai.timeout` defaults to 30 seconds. The default prompt asks for visible
page errors; `ai.prompt` overrides it. `screenshot.format` and `screenshot.quality`
control image encoding and default to `png` and `85`.

`AIClient.from_settings(settings)` accepts already loaded settings. To construct a
client directly, pass `api_url`, `api_key`, and `model`, with optional `timeout`,
`prompt`, `image_format`, and `quality` keyword arguments.

The client sends one user message containing a text prompt and a base64 image data
URL. It returns the first choice's non-empty text, with surrounding whitespace
removed. Empty, malformed, or incomplete responses raise `AIResponseError`, a
subclass of `AIClientError`. Image errors are reported before any HTTP request.
Responses are closed after use, and redirects are not followed.

The request schema follows the
[official Chat Completions reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
Other providers must implement this schema; a configurable URL alone does not
make an arbitrary vision API compatible.
