# Configuration

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
subclasses. Full field validation will be added separately.

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
