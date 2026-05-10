# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg is required by pydub for >25 MB chunking.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY echoscribe/ echoscribe/

# Install with the [server] extra so `echoscribe serve` works out of the box.
RUN pip install ".[server]"

RUN useradd --create-home --uid 1000 echoscribe
USER echoscribe

EXPOSE 8000

ENTRYPOINT ["echoscribe"]
CMD ["--help"]

# ── Healthcheck ─────────────────────────────────────────────────────
# Only relevant when running `echoscribe serve`. Cheap to enable for all
# invocations because curl on a non-listener exits non-zero quickly.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
                   sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz', timeout=3).status == 200 else 1)" || exit 1
