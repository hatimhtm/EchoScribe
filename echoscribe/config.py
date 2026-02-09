"""Configuration management for EchoScribe.

Loads configuration from environment variables with sensible defaults.
Use a .env file for local development.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig:
    """Slack API configuration."""
    api_token: str = ""
    channel: str = "#meeting_recordings"
    
    @classmethod
    def from_env(cls) -> "SlackConfig":
        """Create config from environment variables."""
        return cls(
            api_token=os.getenv("SLACK_API_TOKEN", ""),
            channel=os.getenv("SLACK_CHANNEL", "#meeting_recordings"),
        )


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key: str = ""
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 500
    
    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500")),
        )


@dataclass
class AudioConfig:
    """Audio recording configuration."""
    sample_rate: int = 44100
    channels: int = 2
    chunk_length_ms: int = 60000
    output_format: str = "wav"
    
    @classmethod
    def from_env(cls) -> "AudioConfig":
        """Create config from environment variables."""
        return cls(
            sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "44100")),
            channels=int(os.getenv("AUDIO_CHANNELS", "2")),
            chunk_length_ms=int(os.getenv("AUDIO_CHUNK_MS", "60000")),
        )


@dataclass
class Config:
    """Main configuration container.
    
    Example usage:
        config = Config.from_env()
        print(config.slack.channel)
    """
    slack: SlackConfig = field(default_factory=SlackConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    debug: bool = False
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create complete config from environment variables.
        
        Environment variables:
            SLACK_API_TOKEN: Slack Bot token
            SLACK_CHANNEL: Channel to post summaries (default: #meeting_recordings)
            OPENAI_API_KEY: OpenAI API key
            OPENAI_MODEL: Model to use (default: gpt-3.5-turbo)
            GOOGLE_APPLICATION_CREDENTIALS: Path to Google Cloud credentials
            DEBUG: Enable debug mode (default: false)
            LOG_LEVEL: Logging level (default: INFO)
        """
        return cls(
            slack=SlackConfig.from_env(),
            openai=OpenAIConfig.from_env(),
            audio=AudioConfig.from_env(),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.slack.api_token:
            errors.append("SLACK_API_TOKEN is required")
        if not self.openai.api_key:
            errors.append("OPENAI_API_KEY is required")
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            errors.append("GOOGLE_APPLICATION_CREDENTIALS is required")
            
        return errors
    
    def setup_logging(self) -> None:
        """Configure logging based on config."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
