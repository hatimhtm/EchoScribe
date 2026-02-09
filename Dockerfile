FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY echoscribe/ echoscribe/

# Create non-root user
RUN useradd --create-home appuser
USER appuser

# Default command
ENTRYPOINT ["echoscribe"]
CMD ["--help"]
