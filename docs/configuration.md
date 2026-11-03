# Configuration

Start with [config.example.yaml](../config.example.yaml). Copy it to `config.yaml`,
replace `ai.api_url` with your provider's full Chat Completions endpoint, and set
`ai.model` to a vision-capable model available to your account. The `.invalid`
hostname and model in the example are placeholders and cannot be used as-is.
Set the real key through `AI_API_KEY`; keep `api_key: ${AI_API_KEY}` in the file.
The local `config.yaml` is ignored by Git; the example contains no credentials.

Load a UTF-8 YAML file with `load_config`:

```python
from webdriver_vision.config import load_config

settings = load_config("config.yaml")
```

The file must contain a mapping. An empty file produces an empty dictionary before
environment settings are applied.
For example:

```yaml
browser:
  headless: true
  window_size: [1920, 1080]
ai:
  model: your-model
  timeout: 30
```

The loader preserves nested YAML values as Python dictionaries, lists, and scalars.
It raises `ConfigurationError` for invalid YAML or a document whose root is not a
mapping. Missing files and other file access errors propagate as `OSError`
subclasses.

## Validation

`load_config` validates supplied fields after applying the API key override.
You can also call `validate_config(settings)` to check an existing dictionary.
Validation leaves the dictionary unchanged and does not insert defaults.
Sections and fields are optional; unknown fields are preserved.

| Field | Accepted values |
| --- | --- |
| `browser.headless` | A boolean. |
| `browser.window_size` | A list of two positive integers: width and height. |
| `screenshot.format` | `png` or `jpeg`, in lowercase. |
| `screenshot.full_page` | A boolean. |
| `screenshot.quality` | An integer from 1 to 95; used for JPEG encoding. |
| `ai.api_url` | An absolute HTTP or HTTPS URL with a hostname and valid port. |
| `ai.api_key`, `ai.model`, `ai.prompt` | Non-empty strings. |
| `ai.timeout` | A finite positive number of seconds. |

Wrong types and values raise `ConfigurationError` identifying the field. Values
are not coerced: for example, the string `"false"` is not accepted as a boolean.
An empty configuration is valid at this stage; required settings will be checked
by the components that use them.

## API credentials

Set the API key through the environment:

```bash
export AI_API_KEY=your-key
```

`AI_API_KEY` takes precedence over `ai.api_key` in the file. Other settings in the
`ai` section are preserved. The environment key also works when the file has no
`ai` section. If present, that section must be a mapping.

You can explicitly reference the variable in YAML:

```yaml
ai:
  api_key: ${AI_API_KEY}
  model: your-model
```

The loader raises `ConfigurationError` if this placeholder is used without setting
the variable, or if the environment variable is empty or contains only whitespace.
Without an environment override, a literal `ai.api_key` value is preserved.
Only `AI_API_KEY` is read; placeholders in other fields are left unchanged.
Environment values are read on every call to `load_config`.

Keep real API keys out of version control. `.env` files are ignored by Git but are
not loaded automatically.
