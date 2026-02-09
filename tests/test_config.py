"""Tests for configuration module."""

import os
import pytest

from echoscribe.config import Config, SlackConfig, OpenAIConfig, AudioConfig


class TestSlackConfig:
    """Tests for SlackConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SlackConfig()

        assert config.api_token == ""
        assert config.channel == "#meeting_recordings"

    def test_from_env(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("SLACK_API_TOKEN", "xoxb-test-token")
        monkeypatch.setenv("SLACK_CHANNEL", "#custom-channel")

        config = SlackConfig.from_env()

        assert config.api_token == "xoxb-test-token"
        assert config.channel == "#custom-channel"


class TestOpenAIConfig:
    """Tests for OpenAIConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = OpenAIConfig()

        assert config.api_key == ""
        assert config.model == "gpt-3.5-turbo"
        assert config.max_tokens == 500

    def test_from_env(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4")
        monkeypatch.setenv("OPENAI_MAX_TOKENS", "1000")

        config = OpenAIConfig.from_env()

        assert config.api_key == "sk-test-key"
        assert config.model == "gpt-4"
        assert config.max_tokens == 1000


class TestAudioConfig:
    """Tests for AudioConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AudioConfig()

        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.chunk_length_ms == 60000


class TestConfig:
    """Tests for main Config class."""

    def test_from_env(self, monkeypatch):
        """Test loading complete config from environment."""
        monkeypatch.setenv("SLACK_API_TOKEN", "test-slack")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        config = Config.from_env()

        assert config.slack.api_token == "test-slack"
        assert config.openai.api_key == "test-openai"
        assert config.debug is True
        assert config.log_level == "DEBUG"

    def test_validate_missing_all(self, monkeypatch):
        """Test validation with missing required config."""
        # Clear environment
        monkeypatch.delenv("SLACK_API_TOKEN", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

        config = Config.from_env()
        errors = config.validate()

        assert len(errors) == 3
        assert "SLACK_API_TOKEN" in errors[0]
        assert "OPENAI_API_KEY" in errors[1]
        assert "GOOGLE_APPLICATION_CREDENTIALS" in errors[2]

    def test_validate_all_present(self, monkeypatch):
        """Test validation with all required config present."""
        monkeypatch.setenv("SLACK_API_TOKEN", "token")
        monkeypatch.setenv("OPENAI_API_KEY", "key")
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/creds.json")

        config = Config.from_env()
        errors = config.validate()

        assert len(errors) == 0
