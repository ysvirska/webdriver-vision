FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY webdriver_vision/ ./webdriver_vision/
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 app

USER app
ENTRYPOINT ["webdriver-vision"]
CMD ["--help"]
