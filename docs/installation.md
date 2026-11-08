# Installation and first run

## Requirements

- Python 3.10 or newer with `pip` and `venv`.
- Google Chrome for screenshot capture.
- An OpenAI-compatible Chat Completions endpoint and a vision-capable model.

See [Chrome setup](browser-setup.md) for browser and driver requirements.

Install from this repository; no PyPI release is required:

```bash
git clone https://github.com/ysvirska/webdriver-vision.git
cd webdriver-vision
```

## Create an environment

In Bash on Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
cp config.example.yaml config.yaml
```

In PowerShell on Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
Copy-Item config.example.yaml config.yaml
```

If environment activation is unavailable, invoke the environment's Python
directly: `.venv/bin/python` on Linux/macOS or `.venv\Scripts\python.exe` on Windows.
For development, use `python -m pip install -e .` instead of a regular install.
After changing source files, reinstall a regular installation to use the changes.

## Configure the provider

Edit your local `config.yaml`:

- Replace `ai.api_url` with the full image-capable Chat Completions endpoint.
- Replace `ai.model` with the provider's model identifier.
- Keep `ai.api_key: ${AI_API_KEY}` so the credential is read from the environment.

The example's `.invalid` hostname and `your-vision-model` are placeholders. A model
must accept image inputs; a text-only model will not work. Other API protocols,
including Responses and Anthropic Messages, require a different client.

Enter the credential for the current shell without placing its value in a command
or configuration file. In Bash:

```bash
read -r -s -p "AI API key: " AI_API_KEY
printf '\n'
export AI_API_KEY
```

In PowerShell:

```powershell
$apiKey = Read-Host "AI API key" -AsSecureString
$env:AI_API_KEY = [System.Net.NetworkCredential]::new("", $apiKey).Password
```

The package does not load `.env` files automatically. Local configuration and
credential files remain excluded from Git.

## Run an analysis

```bash
python -m webdriver_vision --help
python -m webdriver_vision --url https://example.com --config config.yaml
```

You can also use `webdriver-vision` after installation. A successful run prints a
text report. It may describe errors or say that no visible issues were found; exit
code 0 only means that a report was produced.

Chrome starts headless by default. Selenium Manager locates ChromeDriver and may
download it on the first run. Dependencies, driver downloads, the target page, and
the selected API need the network access appropriate to their locations.

See [CLI usage](cli.md) for capture options and exit codes, and
[testing](testing.md) for checks that do not call a paid vision API.
