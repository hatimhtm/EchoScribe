# EchoScribe

[![Tests](https://github.com/hatimhtm/EchoScribe/actions/workflows/tests.yml/badge.svg)](https://github.com/hatimhtm/EchoScribe/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🎙️ Automated meeting transcription and summarization tool

EchoScribe records meetings, transcribes audio using Google Cloud Speech-to-Text, summarizes content with OpenAI, and posts structured summaries to Slack.

<p align="center">
  <img src="docs/demo.png" alt="EchoScribe Demo" width="600" />
</p>

## ✨ Features

- **Audio Recording** - Capture meeting audio with configurable quality
- **Transcription** - Convert speech to text using Google Cloud Speech-to-Text
- **AI Summarization** - Extract summaries, action items, and key points using GPT
- **Slack Integration** - Post formatted meeting notes to any channel
- **CLI Interface** - Easy-to-use command-line tool
- **Docker Support** - Run anywhere with containerization

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/hatimhtm/EchoScribe.git
cd EchoScribe

# Install with pip
pip install -e .

# Or with Docker
docker build -t echoscribe .
```

### Configuration

Set these environment variables (or use a `.env` file):

```bash
# Required
export SLACK_API_TOKEN="xoxb-your-slack-bot-token"
export OPENAI_API_KEY="sk-your-openai-api-key"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# Optional
export SLACK_CHANNEL="#meeting_recordings"
export OPENAI_MODEL="gpt-3.5-turbo"
export LOG_LEVEL="INFO"
```

### Usage

```bash
# Check configuration
echoscribe check-config

# Transcribe an audio file
echoscribe transcribe recording.wav -o transcript.txt

# Summarize a transcription
echoscribe summarize transcript.txt --slack

# Full pipeline: transcribe + summarize + post to Slack
echoscribe process recording.wav --channel "#team-meetings"
```

## 📁 Project Structure

```
echoscribe/
├── __init__.py           # Package exports
├── config.py             # Configuration management
├── cli.py                # Typer CLI commands
├── services/
│   ├── transcription.py  # Google Cloud Speech-to-Text
│   ├── summarization.py  # OpenAI summarization
│   ├── slack.py          # Slack integration
│   └── recorder.py       # Audio recording
└── utils/
    └── __init__.py

tests/
├── test_config.py        # Configuration tests
└── test_summarization.py # Summarization tests
```

## 🔧 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=echoscribe

# Format code
black echoscribe tests
ruff check echoscribe tests
```

## 🐳 Docker

```bash
# Build image
docker build -t echoscribe .

# Run with environment variables
docker run --rm \
  -e SLACK_API_TOKEN="xoxb-..." \
  -e OPENAI_API_KEY="sk-..." \
  -e GOOGLE_APPLICATION_CREDENTIALS="/creds/key.json" \
  -v /path/to/creds:/creds:ro \
  -v /path/to/audio:/audio:ro \
  echoscribe process /audio/meeting.wav
```

## 📋 API Reference

### SummarizationService

```python
from echoscribe.services.summarization import SummarizationService

service = SummarizationService(api_key="sk-...")
summary = service.summarize("Meeting transcription text...")

print(summary.summary)        # Brief summary
print(summary.action_items)   # List of action items
print(summary.key_points)     # Key discussion points
```

### TranscriptionService

```python
from echoscribe.services.transcription import TranscriptionService

service = TranscriptionService(language_code="en-US")
result = service.transcribe("meeting.wav")

print(result.text)        # Transcribed text
print(result.confidence)  # Confidence score
```

### SlackService

```python
from echoscribe.services.slack import SlackService

slack = SlackService(token="xoxb-...")
slack.post_message("Hello, team!", channel="#general")
slack.upload_file("report.pdf", title="Meeting Report")
```

## 📄 License

[MIT](LICENSE)
