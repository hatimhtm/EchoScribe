"""Configuration management for EchoScribe.

Loads from environment variables (and a `.env` file if `python-dotenv` is
installed or a parent process loaded it). The whole pipeline runs on a
single OpenAI key; Slack is optional.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _load_dotenv_if_present() -> None:
    """Best-effort load of .env from CWD. Silent no-op if python-dotenv is missing."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


@dataclass
class OpenAIConfig:
    """OpenAI configuration — used for both Whisper (transcription) and GPT (intelligence)."""

    api_key: str = ""
    model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> OpenAIConfig:
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            whisper_model=os.getenv("OPENAI_WHISPER_MODEL", "whisper-1"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
        )


@dataclass
class SlackConfig:
    """Slack configuration — optional, only used when posting summaries to Slack."""

    api_token: str = ""
    channel: str = "#meetings"

    @classmethod
    def from_env(cls) -> SlackConfig:
        return cls(
            api_token=os.getenv("SLACK_API_TOKEN", ""),
            channel=os.getenv("SLACK_CHANNEL", "#meetings"),
        )


@dataclass
class Config:
    """Top-level config container.

    Example:
        config = Config.from_env()
        if not config.openai.api_key:
            raise SystemExit("OPENAI_API_KEY required")
    """

    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Config:
        _load_dotenv_if_present()
        return cls(
            openai=OpenAIConfig.from_env(),
            slack=SlackConfig.from_env(),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )

    def required_errors(self, *, need_slack: bool = False) -> list[str]:
        """Return human-readable error messages for missing required config.

        OpenAI is always required (it's the whole pipeline). Slack is only
        required when the caller asks for it (`--slack` / server with
        `post_to_slack=true`).
        """
        errors: list[str] = []
        if not self.openai.api_key:
            errors.append("OPENAI_API_KEY is required")
        if need_slack and not self.slack.api_token:
            errors.append("SLACK_API_TOKEN is required for Slack posting")
        return errors

    def setup_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, self.log_level, logging.INFO),
            format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
