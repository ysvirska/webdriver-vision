# Configuration

Load a UTF-8 YAML file with `load_config`:

```python
from webdriver_vision.config import load_config

settings = load_config("config.yaml")
```

The file must contain a mapping. An empty file produces an empty dictionary.
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
subclasses. Field validation will be added separately.
