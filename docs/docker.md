# Docker Compose

Use Docker Engine or Docker Desktop with Compose v2. Python and Chrome do not need
to be installed on the host. Run the commands from the repository root.

Compose starts two services:

- `vision`: the Python CLI, running as a non-root user.
- `browser`: the official Selenium Chromium image, with a readiness check and
  2 GB of shared memory available to the browser.

The browser image version is pinned in `compose.yaml`. The Selenium endpoint is
available within the Compose network and is not published on the host.

## Run an analysis

Copy `config.example.yaml` to a local `config.yaml`. Set the endpoint and model,
and supply `AI_API_KEY` in your shell as described in [installation](installation.md).
Keep the credential out of the YAML file.

```bash
docker compose build vision
docker compose run --rm vision --url https://example.com
docker compose run --rm vision --url https://example.com --full-page
docker compose run --rm vision --url https://example.com --selector '#login-form'
```

The first run downloads the Python and Selenium images. Compose waits for Selenium
to become healthy before starting an analysis. Reports go to stdout, and CLI exit
codes are preserved. The browser service stays up for subsequent runs; stop it with:

```bash
docker compose down
```

The local configuration is mounted read-only at `/app/config.yaml`. Set the
`VISION_CONFIG` environment variable to use a different host file. It must exist
and be readable by the app container's user (UID 10001). Compose supplies the
remote browser URL automatically, so your normal local configuration also works.

The API key is passed only to `vision`, not to the browser service. The Docker
build context includes only Python source and package metadata; local configs,
`.env`, Git data, and key files are excluded. No credential is stored in the image.

## Network addresses

The target page is opened from the browser container. The vision API is contacted
from the app container. In each case, `localhost` refers to that container, not the
host machine. Use URLs reachable from the appropriate container, or configure
host/service networking for local targets and local API servers.

## Check the containers without a provider

In Bash, use the example config for help and browser smoke tests; no real API key
or paid API is needed:

```bash
VISION_CONFIG=./config.example.yaml docker compose run --rm --no-deps vision --help
VISION_CONFIG=./config.example.yaml docker compose run --rm --entrypoint python \
  --volume "$PWD/tests/docker/smoke.py:/tmp/docker-smoke.py:ro" \
  vision /tmp/docker-smoke.py
docker compose down
```

The checks capture a viewport, full document, and element through remote Chromium
and verify JPEG encoding. GitHub Actions builds the app image and runs these checks.

The browser service follows the
[official Selenium container guidance](https://github.com/SeleniumHQ/docker-selenium).
